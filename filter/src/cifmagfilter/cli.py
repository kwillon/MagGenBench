from __future__ import annotations

import argparse
import json
import platform
import hashlib
import sys
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import core as _core
from .core import FEATURE_SETS, load_site_priors, numeric_feature_columns, structure_features
from .model import CIFMagFilter
from .reference import (
    ReferenceModel,
    robust_fit,
    robust_transform,
    score_against_references as reference_scores,
    score_reference_training as reference_scores_training,
    summarize_queries,
)

REFS = ["AFM", "FM", "FiM", "NM"]
MAG = ["AFM", "FM", "FiM"]
SUFFIXES = {".cif", ".mcif", ".json"}


def canon_label(x):
    if x is None:
        return None
    s = str(x).strip()
    if s.lower() == "fim":
        return "FiM"
    u = s.upper()
    return u if u in {"MAGNDATA", "AFM", "FM", "NM"} else s


def load_config(path: Path):
    cfg = json.loads(path.read_text(encoding="utf-8"))
    base = path.resolve().parent
    for ds in cfg.get("datasets", []):
        p = Path(ds["path"])
        ds["path"] = str((base / p).resolve()) if not p.is_absolute() else str(p.resolve())
        if ds.get("label") is not None:
            ds["label"] = canon_label(ds["label"])
    if cfg.get("site_priors"):
        p = Path(cfg["site_priors"])
        cfg["site_priors"] = str((base / p).resolve()) if not p.is_absolute() else str(p.resolve())
    out = Path(cfg.get("output_dir", "results"))
    cfg["output_dir"] = str((base / out).resolve()) if not out.is_absolute() else str(out.resolve())
    return cfg


def validate_cif_only_config(cfg: dict, *, allow_external_site_priors: bool = False) -> None:
    """Enforce the paper/public canonical CIF-only boundary.

    External site priors can override oxidation states/electron counts/support scores
    and are therefore not CIF-only. They are available only behind an explicit
    advanced opt-in flag.
    """
    if cfg.get("site_priors") and not allow_external_site_priors:
        raise ValueError(
            "Canonical CIF-only mode forbids external site_priors. "
            "Remove site_priors from the config or pass --allow-external-site-priors "
            "for a non-paper advanced run."
        )


def validate_canonical_extraction_dependencies() -> None:
    missing = []
    if _core.Structure is None:
        missing.append("pymatgen")
    if _core.smact_validity is None:
        missing.append("SMACT")
    if missing:
        raise RuntimeError(
            "Canonical extraction requires the full chemistry stack: "
            + ", ".join(missing)
            + ". Install the publication environment or `pip install -e .`."
        )


def iter_structure_files(root: Path):
    if root.is_file() and root.suffix.lower() in SUFFIXES:
        yield root
        return
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in SUFFIXES:
            yield p


def _stable_dataset_seed(base_seed: int, dataset_name: str) -> int:
    """Derive a reproducible dataset-specific RNG seed."""
    digest = hashlib.sha256(dataset_name.encode("utf-8")).digest()
    offset = int.from_bytes(digest[:4], byteorder="little", signed=False)
    return (int(base_seed) + offset) % (2**32 - 1)


def _condition_group(dataset_name: str, path: Path) -> str | None:
    """Infer a preparation/conditioning group from the flattened CIF filename.

    The prepared datasets encode provenance in the filename using ``__``.
    This function is used only for smoke-test subsampling; it has no effect
    on full runs without ``--limit``.
    """
    name = dataset_name.lower()
    parts = path.stem.split("__")

    if name == "crystalllm" and len(parts) >= 2:
        # e.g. Co2FeAl__sample_17 -> target composition
        return parts[0]
    if name == "concdvae_base" and len(parts) >= 2:
        # e.g. eval_gen_FM0__eval_gen_FM0_0001 -> generation batch
        return parts[0]
    if name == "crystalformer" and len(parts) >= 2:
        # e.g. s01_seed101_n100__cf_repr... -> seed/condition block
        return parts[0]
    if name == "mattergen_base" and len(parts) >= 3:
        # e.g. benchmark_mgd_2000__mgd_0p20_g_1p2_seed_401__cand_0001
        # retain both benchmark family and the complete generation condition
        return "__".join(parts[:2])

    # Generic fallback for future prepared query datasets that use one
    # condition prefix before ``__``.  Avoid applying this to references.
    if len(parts) >= 2:
        return parts[0]
    return None


def _random_sample(files: list[Path], limit: int, rng: np.random.Generator) -> list[Path]:
    if len(files) <= limit:
        return list(files)
    idx = rng.choice(len(files), size=limit, replace=False)
    return sorted((files[int(i)] for i in idx), key=lambda p: str(p).lower())


def _stratified_sample(
    files: list[Path],
    groups: dict[str, list[Path]],
    limit: int,
    rng: np.random.Generator,
) -> list[Path]:
    """Deterministic approximately balanced sampling across condition groups.

    If the number of groups is >= limit, one structure is drawn from ``limit``
    randomly chosen groups.  Otherwise every group contributes at least one
    structure and remaining slots are filled round-robin from groups that still
    contain unused structures.
    """
    if len(files) <= limit:
        return list(files)

    # Shuffle members reproducibly inside each group.
    pools: dict[str, list[Path]] = {}
    for key, vals in groups.items():
        vals = list(vals)
        order = rng.permutation(len(vals))
        pools[key] = [vals[int(i)] for i in order]

    keys = list(pools)
    key_order = [keys[int(i)] for i in rng.permutation(len(keys))]
    selected: list[Path] = []

    if limit <= len(key_order):
        for key in key_order[:limit]:
            selected.append(pools[key].pop())
        return sorted(selected, key=lambda p: str(p).lower())

    # Give every condition group one representative first.
    for key in key_order:
        if pools[key] and len(selected) < limit:
            selected.append(pools[key].pop())

    # Fill remaining slots fairly across groups.
    while len(selected) < limit:
        available = [k for k in key_order if pools[k]]
        if not available:
            break
        round_order = [available[int(i)] for i in rng.permutation(len(available))]
        for key in round_order:
            if len(selected) >= limit:
                break
            selected.append(pools[key].pop())

    return sorted(selected, key=lambda p: str(p).lower())


def select_files_for_limit(
    files: list[Path],
    dataset: dict,
    limit: int | None,
    sampling: str = "auto",
    sample_seed: int = 42,
) -> tuple[list[Path], str, int]:
    """Choose files for smoke tests while keeping full runs unchanged.

    ``auto`` uses condition-stratified sampling for prepared query datasets
    when condition groups can be inferred, and reproducible random sampling
    for reference datasets or datasets without condition groups.
    """
    if limit is None or len(files) <= limit:
        return files, "all", 0

    name = str(dataset["name"]).lower()
    rng = np.random.default_rng(_stable_dataset_seed(sample_seed, name))

    if sampling == "first":
        return files[:limit], "first", 0
    if sampling == "random":
        return _random_sample(files, limit, rng), "random", 0

    role = str(dataset.get("role", "")).lower()
    label = canon_label(dataset.get("label"))
    is_reference = role == "reference" or label in REFS
    if is_reference:
        return _random_sample(files, limit, rng), "random-reference", 0

    groups: dict[str, list[Path]] = {}
    ungrouped: list[Path] = []
    for path in files:
        key = _condition_group(name, path)
        if key is None:
            ungrouped.append(path)
        else:
            groups.setdefault(key, []).append(path)

    # Stratify only when there is genuinely more than one inferred condition.
    if len(groups) >= 2 and not ungrouped:
        return _stratified_sample(files, groups, limit, rng), "stratified", len(groups)

    return _random_sample(files, limit, rng), "random-query", len(groups)


def extract(cfg, limit=None, write_details=False, sampling="auto", sample_seed=42):
    validate_canonical_extraction_dependencies()
    out = Path(cfg["output_dir"]) / "features"
    out.mkdir(parents=True, exist_ok=True)
    params = {
        "neighbor_cutoff": 3.2,
        "max_mm_distance": 8.0,
        "contact_norm_cutoff": 1.20,
        "bond_scale": 1.30,
        "min_center_score": 0.05,
        "min_pair_weight": 0.05,
        "max_sites": 500,
        "symprec": 0.10,
        "min_oxidation_coverage": 1.0,
        "reject_disordered": True,
        **cfg.get("extraction", {}),
    }
    priors = load_site_priors(cfg.get("site_priors"))
    rows, sites_all, pairs_all = [], [], []
    for ds in cfg.get("datasets", []):
        name = str(ds["name"]).lower()
        root = Path(ds["path"])
        if not root.exists():
            raise FileNotFoundError(root)
        files_all = list(iter_structure_files(root))
        files, sampling_used, n_groups = select_files_for_limit(
            files_all, ds, limit, sampling=sampling, sample_seed=sample_seed
        )
        if limit is not None:
            extra = f", groups={n_groups}" if n_groups else ""
            print(
                f"[{name}] {len(files)} structures "
                f"(from {len(files_all)}, sampling={sampling_used}{extra}, seed={sample_seed})",
                flush=True,
            )
        else:
            print(f"[{name}] {len(files)} structures", flush=True)
        for i, path in enumerate(files, 1):
            if limit is not None and limit <= 20:
                print(f"[{name}] {i}/{len(files)} {path.name}", flush=True)
            try:
                sites, pairs, row = structure_features(path, name, priors, **params)
            except Exception as exc:
                sites, pairs = None, None
                row = {
                    "dataset": name, "structure_id": path.stem, "source_path": str(path),
                    "parse_success": 0, "parse_error": f"descriptor_error: {type(exc).__name__}: {exc}"
                }
            row["label_order"] = ds.get("label")
            row["role"] = ds.get("role", "reference" if ds.get("label") in REFS else "query")
            rows.append(row)
            if write_details and sites is not None:
                sites_all.append(sites)
            if write_details and pairs is not None and not pairs.empty:
                pairs_all.append(pairs)
            if i % 100 == 0:
                print(f"[{name}] {i}/{len(files)}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(out / "structure_features.csv", index=False)
    df[df["parse_success"].fillna(0).astype(int).eq(0)].to_csv(out / "parse_failures.csv", index=False)
    if write_details:
        if sites_all:
            pd.concat(sites_all, ignore_index=True).to_csv(out / "magnetic_sites.csv", index=False)
        if pairs_all:
            pd.concat(pairs_all, ignore_index=True).to_csv(out / "magnetic_pairs.csv", index=False)
    return df


def fit_reference(df: pd.DataFrame, cfg):
    out = Path(cfg["output_dir"]) / "model"
    out.mkdir(parents=True, exist_ok=True)
    rcfg = {"feature_set": "main", "knn_k": 15, "clip_z": 8.0,
            "min_feature_coverage": 0.20, "near_constant_tol": 1e-8, **cfg.get("reference", {})}
    feature_set = rcfg["feature_set"]
    if feature_set not in FEATURE_SETS:
        raise ValueError(f"Unknown feature_set={feature_set}; choose from {sorted(FEATURE_SETS)}")
    valid = df["parse_success"].fillna(0).astype(int).eq(1)
    ref = df[valid & df["label_order"].map(canon_label).isin(REFS)].copy().reset_index(drop=True)
    ref["label_order"] = ref["label_order"].map(canon_label)
    counts = ref["label_order"].value_counts().to_dict()
    missing = [c for c in REFS if counts.get(c, 0) < 2]
    if missing:
        raise ValueError(f"Reference classes need at least 2 structures: {missing}")
    feat = numeric_feature_columns(ref, float(rcfg["min_feature_coverage"]), feature_set=feature_set, near_constant_tol=float(rcfg["near_constant_tol"]))
    if not feat:
        raise ValueError("No usable features after explicit feature registry / coverage filtering")
    mask = np.ones(len(ref), dtype=bool)
    X, center, scale, miss = robust_fit(ref, feat, mask, float(rcfg["clip_z"]))
    meta_cols = [c for c in ["dataset", "structure_id", "source_path", "formula_reduced", "label_order"] if c in ref.columns]
    scored = reference_scores_training(ref[meta_cols].copy(), X, ref["label_order"], REFS, MAG, int(rcfg["knn_k"]))
    scored["feature_missing_fraction"] = miss

    arrays = {"feature_names": np.asarray(feat, dtype=str), "center": center, "scale": scale}
    for c in REFS:
        arrays[f"ref_{c}"] = X[ref["label_order"].eq(c).to_numpy(bool)]
    np.savez_compressed(out / "reference_filter.npz", **arrays)
    model = {
        "model_name": "default",
        "reference_classes": REFS,
        "magnetic_classes": MAG,
        "feature_set": feature_set,
        "n_features": len(feat),
        "feature_names": feat,
        "knn_k": int(rcfg["knn_k"]),
        "clip_z": float(rcfg["clip_z"]),
        "min_feature_coverage": float(rcfg["min_feature_coverage"]),
        "near_constant_tol": float(rcfg["near_constant_tol"]),
        "reference_self_policy": "leave_one_out",
        "reference_counts": {c: int(counts.get(c, 0)) for c in REFS},
    }
    (out / "reference_filter.json").write_text(json.dumps(model, indent=2), encoding="utf-8")
    pd.DataFrame({"feature": feat, "center": center, "scale": scale}).to_csv(out / "feature_manifest.csv", index=False)
    scored.to_csv(out / "reference_validation_scores.csv", index=False)
    confusion = pd.crosstab(scored["label_order"], scored["nearest_reference_branch"], normalize="index")
    confusion.to_csv(out / "reference_branch_confusion.csv")
    return model


def load_model(model_dir: Path):
    meta = json.loads((model_dir / "reference_filter.json").read_text(encoding="utf-8"))
    z = np.load(model_dir / "reference_filter.npz", allow_pickle=False)
    refs = {c: z[f"ref_{c}"].astype(float) for c in meta["reference_classes"]}
    return meta, z["feature_names"].astype(str).tolist(), z["center"].astype(float), z["scale"].astype(float), refs


def score(df: pd.DataFrame, cfg):
    out = Path(cfg["output_dir"]) / "scores"
    out.mkdir(parents=True, exist_ok=True)
    meta, feat, center, scale, refs = load_model(Path(cfg["output_dir"]) / "model")
    scored_parts = []
    ok = df["parse_success"].fillna(0).astype(int).eq(1)
    good = df[ok].copy()
    if len(good):
        X, miss = robust_transform(good, feat, center, scale, float(meta["clip_z"]))
        cols = [c for c in ["dataset", "structure_id", "source_path", "formula_reduced", "label_order", "role"] if c in good.columns]
        sg = reference_scores(good[cols].copy(), X, refs, meta["magnetic_classes"], int(meta["knn_k"]))
        sg["feature_missing_fraction"] = miss
        sg["score_status"] = "ok"
        scored_parts.append(sg)
    bad = df[~ok].copy()
    if len(bad):
        cols = [c for c in ["dataset", "structure_id", "source_path", "formula_reduced", "label_order", "role", "parse_error"] if c in bad.columns]
        sb = bad[cols].copy()
        sb["score_status"] = "parse_failed"
        scored_parts.append(sb)
    scored = pd.concat(scored_parts, ignore_index=True, sort=False) if scored_parts else pd.DataFrame()
    scored.to_csv(out / "all_scores.csv", index=False)
    query = scored[~scored.get("role", pd.Series("query", index=scored.index)).astype(str).eq("reference")].copy()
    query.to_csv(out / "query_scores.csv", index=False)
    summarize_queries(query).to_csv(out / "query_summary.csv", index=False)
    return scored


def score_feature_table(features_path: Path, model_dir: Path, output_path: Path) -> pd.DataFrame:
    """Score an already extracted feature table against a canonical reference model."""
    df = pd.read_csv(features_path, low_memory=False)
    model = ReferenceModel.load(model_dir)
    ok = pd.to_numeric(df.get("parse_success", 1), errors="coerce").fillna(0).astype(int).eq(1)
    parts = []
    good = df[ok].copy()
    if len(good):
        X, missing = model.transform(good)
        meta_cols = [
            c for c in ["dataset", "structure_id", "source_path", "formula_reduced", "label_order", "role"]
            if c in good.columns
        ]
        scored = model.score(good[meta_cols].copy(), X, add_support_percentile=True)
        scored["feature_missing_fraction"] = missing
        scored["score_status"] = "ok"
        parts.append(scored)
    bad = df[~ok].copy()
    if len(bad):
        cols = [
            c for c in ["dataset", "structure_id", "source_path", "formula_reduced", "label_order", "role", "parse_error"]
            if c in bad.columns
        ]
        failed = bad[cols].copy()
        failed["score_status"] = "parse_failed"
        parts.append(failed)
    out = pd.concat(parts, ignore_index=True, sort=False) if parts else pd.DataFrame()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    return out


def write_manifest(cfg, runtime=None):
    out = Path(cfg["output_dir"])
    try:
        import importlib.metadata as md
        import numpy, pandas, sklearn
        versions = {
            "python": platform.python_version(),
            "numpy": numpy.__version__,
            "pandas": pandas.__version__,
            "scikit_learn": sklearn.__version__,
        }
        for distribution, key in [
            ("pymatgen", "pymatgen"),
            ("SMACT", "smact"),
            ("scipy", "scipy"),
            ("matplotlib", "matplotlib"),
            ("spglib", "spglib"),
        ]:
            try:
                versions[key] = md.version(distribution)
            except Exception:
                versions[key] = "not_installed"
    except Exception:
        versions = {"python": platform.python_version()}
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "config": cfg,
        "runtime": runtime or {},
        "versions": versions,
    }
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def run_all(
    config_path: Path,
    limit=None,
    write_details=False,
    sampling="auto",
    sample_seed=42,
    allow_external_site_priors: bool = False,
):
    cfg = load_config(config_path)
    validate_cif_only_config(cfg, allow_external_site_priors=allow_external_site_priors)
    Path(cfg["output_dir"]).mkdir(parents=True, exist_ok=True)
    df = extract(
        cfg,
        limit=limit,
        write_details=write_details,
        sampling=sampling,
        sample_seed=sample_seed,
    )
    fit_reference(df, cfg)
    score(df, cfg)
    write_manifest(
        cfg,
        runtime={
            "limit": limit,
            "limit_sampling": sampling,
            "sample_seed": int(sample_seed),
            "write_details": bool(write_details),
            "canonical_cif_only": not bool(allow_external_site_priors),
            "external_site_priors_allowed": bool(allow_external_site_priors),
        },
    )
    print(f"Done: {cfg['output_dir']}")


def self_test():
    rng = np.random.default_rng(7)
    rows = []
    centers = {"AFM": 1.5, "FM": 1.0, "FiM": 0.5, "NM": -1.5}
    for label, mu in centers.items():
        for i in range(20):
            rows.append({"dataset": label.lower(), "structure_id": f"{label}_{i}", "label_order": label,
                         "parse_success": 1, "structure__n_sites": 10 + rng.normal(),
                         "magnetic_center__fraction_magnetic_centers": mu + rng.normal(scale=.2),
                         "magnetic_pair__n_weighted_pairs": 4 + mu + rng.normal(scale=.2)})
    df = pd.DataFrame(rows)
    feat = numeric_feature_columns(df, 0.1, "main")
    X, _, _, _ = robust_fit(df, feat, np.ones(len(df), bool), 8.0)
    scored = reference_scores_training(df[["dataset", "structure_id", "label_order"]], X, df["label_order"], REFS, MAG, 5)
    acc = float(scored["label_order"].eq(scored["nearest_reference_branch"]).mean())
    print(f"self-test features={feat}; nearest-branch agreement={acc:.3f}")
    if acc < 0.70:
        raise SystemExit("self-test failed")


def _add_limit_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--limit-sampling", choices=["auto", "random", "first"], default="auto",
        help="Sampling used only with --limit; auto is deterministic and condition-aware.",
    )
    parser.add_argument("--sample-seed", type=int, default=42)
    parser.add_argument("--write-details", action="store_true")
    parser.add_argument(
        "--allow-external-site-priors", action="store_true",
        help="Advanced non-paper mode. Canonical CIF-only extraction rejects external site priors.",
    )


def main():
    ap = argparse.ArgumentParser(description="CIF-only magnetic-reference filter")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_score = sub.add_parser("score", help="Score a CIF with the bundled reference model")
    p_score.add_argument("cif", type=Path)
    p_score.add_argument("--output", type=Path, default=None)
    p_score.add_argument("--model-dir", type=Path, default=None, help="Optional custom reference model directory")

    p_table = sub.add_parser("score-features", help="Score an extracted feature table")
    p_table.add_argument("--features", required=True, type=Path)
    p_table.add_argument("--output", required=True, type=Path)
    p_table.add_argument("--model-dir", type=Path, default=None)

    p_all = sub.add_parser("workflow", help="Extract descriptors, fit references, and score datasets from a config")
    p_all.add_argument("--config", required=True)
    _add_limit_args(p_all)

    p_extract = sub.add_parser("extract", help="Extract descriptors from datasets in a config")
    p_extract.add_argument("--config", required=True)
    _add_limit_args(p_extract)

    p_fit = sub.add_parser("fit-reference", help="Fit a custom reference model from an extracted feature table")
    p_fit.add_argument("--config", required=True)

    sub.add_parser("self-test")
    args = ap.parse_args()

    if args.cmd == "score":
        filt = CIFMagFilter.from_pretrained(args.model_dir)
        scored = filt.score_cif(args.cif)
        if args.output is None:
            print(scored.to_csv(index=False).strip())
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            scored.to_csv(args.output, index=False)
            print(f"Wrote: {args.output}")
    elif args.cmd == "score-features":
        filt = CIFMagFilter.from_pretrained(args.model_dir)
        features = pd.read_csv(args.features, low_memory=False)
        scored = filt.score_features(features)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        scored.to_csv(args.output, index=False)
        print(f"Wrote: {args.output}")
    elif args.cmd == "workflow":
        run_all(
            Path(args.config),
            limit=args.limit,
            write_details=args.write_details,
            sampling=args.limit_sampling,
            sample_seed=args.sample_seed,
            allow_external_site_priors=args.allow_external_site_priors,
        )
    elif args.cmd == "extract":
        cfg = load_config(Path(args.config))
        validate_cif_only_config(cfg, allow_external_site_priors=args.allow_external_site_priors)
        Path(cfg["output_dir"]).mkdir(parents=True, exist_ok=True)
        extract(
            cfg, limit=args.limit, write_details=args.write_details,
            sampling=args.limit_sampling, sample_seed=args.sample_seed,
        )
        write_manifest(cfg, runtime={
            "mode": "extract_only",
            "limit": args.limit,
            "limit_sampling": args.limit_sampling,
            "sample_seed": int(args.sample_seed),
            "canonical_cif_only": not bool(args.allow_external_site_priors),
        })
    elif args.cmd == "fit-reference":
        cfg = load_config(Path(args.config))
        features_path = Path(cfg["output_dir"]) / "features" / "structure_features.csv"
        if not features_path.exists():
            raise FileNotFoundError(features_path)
        fit_reference(pd.read_csv(features_path, low_memory=False), cfg)
    else:
        self_test()


if __name__ == "__main__":
    main()
