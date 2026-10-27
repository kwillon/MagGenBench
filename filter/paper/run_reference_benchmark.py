from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd

try:
    from cifmagfilter.core import FEATURE_SETS, REGISTERED_DESCRIPTORS, CANONICAL_MAIN_EXCLUSIONS
    from cifmagfilter.reference import (
        feature_selection_audit as canonical_feature_selection_audit,
        robust_fit as canonical_robust_fit,
        robust_transform as canonical_robust_transform,
        knn_distance as canonical_knn_distance,
        knn_distance_training as canonical_knn_distance_training,
        finish_scores as canonical_finish_scores,
        score_reference_training as canonical_score_reference_training,
        score_against_references as canonical_score_query,
        add_reference_support_percentile,
        summarize_queries,
    )
except Exception as exc:
    raise SystemExit(
        "Could not import cifmagfilter.core. Install the repository first with `pip install -e .`.\n"
        f"Original error: {type(exc).__name__}: {exc}"
    )

REFS = ["MAGNDATA", "AFM", "FM", "FiM", "NM"]
MAG = ["MAGNDATA", "AFM", "FM", "FiM"]


def descriptor_policy_table() -> pd.DataFrame:
    rows=[]
    for feature in REGISTERED_DESCRIPTORS:
        reason=CANONICAL_MAIN_EXCLUSIONS.get(feature, "eligible_for_canonical_main")
        rows.append({
            "feature": feature,
            "registered": 1,
            "eligible_for_canonical_main": int(feature not in CANONICAL_MAIN_EXCLUSIONS),
            "canonical_policy": reason,
        })
    return pd.DataFrame(rows)


def canon_label(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    s = str(x).strip()
    if s.lower() == "fim":
        return "FiM"
    u = s.upper()
    return u if u in {"MAGNDATA", "AFM", "FM", "NM"} else s


def sha256_file(path: Path, block_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(block_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def feature_selection_audit(
    ref: pd.DataFrame,
    feature_set: str,
    min_coverage: float,
    near_constant_tol: float,
) -> tuple[list[str], pd.DataFrame]:
    if feature_set not in FEATURE_SETS:
        raise ValueError(f"Unknown feature_set={feature_set}; choose from {sorted(FEATURE_SETS)}")
    return canonical_feature_selection_audit(
        ref,
        FEATURE_SETS[feature_set],
        min_coverage=min_coverage,
        near_constant_tol=near_constant_tol,
    )

def robust_fit(df: pd.DataFrame, feature_cols: list[str], clip_z: float):
    return canonical_robust_fit(
        df, feature_cols, fit_mask=np.ones(len(df), dtype=bool), clip_z=clip_z
    )


def robust_transform(
    df: pd.DataFrame,
    feature_cols: list[str],
    center: np.ndarray,
    scale: np.ndarray,
    clip_z: float,
):
    return canonical_robust_transform(df, feature_cols, center, scale, clip_z)


def knn_distance(X: np.ndarray, ref: np.ndarray, k: int) -> np.ndarray:
    return canonical_knn_distance(X, ref, k)


def knn_distance_training(X: np.ndarray, ref_idx: np.ndarray, k: int) -> np.ndarray:
    return canonical_knn_distance_training(X, ref_idx, k)


def finish_scores(out: pd.DataFrame, refs: list[str], magnetic_classes: list[str]) -> pd.DataFrame:
    return canonical_finish_scores(out, refs, magnetic_classes)


def score_reference_training(
    ref_meta: pd.DataFrame,
    X: np.ndarray,
    labels: pd.Series,
    k: int,
) -> pd.DataFrame:
    return canonical_score_reference_training(ref_meta, X, labels, REFS, MAG, k)


def score_query(
    meta: pd.DataFrame,
    X: np.ndarray,
    ref_arrays: dict[str, np.ndarray],
    k: int,
) -> pd.DataFrame:
    return canonical_score_query(meta, X, ref_arrays, MAG, k)

def validation_summary(scored: pd.DataFrame) -> pd.DataFrame:
    true = scored["label_order"].astype(str)
    pred = scored["nearest_reference_branch"].astype(str)
    exact = float((true == pred).mean())

    true_mag = true.isin(MAG)
    pred_mag = pred.ne("NM")
    sensitivity = float(pred_mag[true_mag].mean()) if true_mag.any() else np.nan
    specificity = float((~pred_mag[~true_mag]).mean()) if (~true_mag).any() else np.nan
    balanced = float(np.nanmean([sensitivity, specificity]))

    rows = [{
        "metric": "exact_five_branch_agreement",
        "value": exact,
    }, {
        "metric": "magnetic_reference_sensitivity",
        "value": sensitivity,
    }, {
        "metric": "NM_specificity",
        "value": specificity,
    }, {
        "metric": "binary_balanced_accuracy",
        "value": balanced,
    }]
    for cls in REFS:
        m = true.eq(cls)
        rows.append({
            "metric": f"same_branch_agreement_{cls}",
            "value": float(pred[m].eq(cls).mean()) if m.any() else np.nan,
        })
    return pd.DataFrame(rows)


def reference_support_summary(scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groups = [("MAGNETIC_POOLED", scored[scored["label_order"].isin(MAG)])]
    groups += [(c, scored[scored["label_order"].eq(c)]) for c in REFS]
    for name, g in groups:
        x = pd.to_numeric(g["nearest_magnetic_reference_distance"], errors="coerce").dropna().to_numpy(float)
        if not len(x):
            continue
        rows.append({
            "reference_group": name,
            "n": len(x),
            "p50_dmag": float(np.quantile(x, 0.50)),
            "p75_dmag": float(np.quantile(x, 0.75)),
            "p90_dmag": float(np.quantile(x, 0.90)),
            "p95_dmag": float(np.quantile(x, 0.95)),
            "p99_dmag": float(np.quantile(x, 0.99)),
            "max_dmag": float(np.max(x)),
            "median_contrast": float(pd.to_numeric(g["magnetic_reference_vs_NM_contrast"], errors="coerce").median()),
        })
    return pd.DataFrame(rows)


def run_variant(
    df: pd.DataFrame,
    out_dir: Path,
    feature_set: str,
    k: int,
    clip_z: float,
    min_coverage: float,
    near_constant_tol: float,
    magndata_dedup: bool = False,
    manifest: pd.DataFrame | None = None,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    valid = df["parse_success"].fillna(0).astype(int).eq(1)
    labels = df["label_order"].map(canon_label)
    ref = df[valid & labels.isin(REFS)].copy()
    ref["label_order"] = ref["label_order"].map(canon_label)

    dedup_report = None
    if magndata_dedup:
        if manifest is None or "sha256" not in manifest.columns:
            raise ValueError("MAGNDATA dedup requested but manifest with sha256 is unavailable")
        mcols = [c for c in ["dataset", "structure_id", "sha256"] if c in manifest.columns]
        ref = ref.merge(manifest[mcols].drop_duplicates(["dataset", "structure_id"]), on=["dataset", "structure_id"], how="left")
        mag_mask = ref["label_order"].eq("MAGNDATA")
        before = int(mag_mask.sum())
        mag = ref[mag_mask].copy()
        other = ref[~mag_mask].copy()
        if mag["sha256"].notna().any():
            # Missing hashes are made structure-specific so they are never accidentally collapsed.
            key = mag["sha256"].where(mag["sha256"].notna(), "NOHASH__" + mag["structure_id"].astype(str))
            mag = mag.loc[~key.duplicated(keep="first")].copy()
        ref = pd.concat([other, mag], ignore_index=True, sort=False)
        after = int(ref["label_order"].eq("MAGNDATA").sum())
        dedup_report = {"magndata_before": before, "magndata_after": after, "removed": before - after}

    counts = ref["label_order"].value_counts().to_dict()
    missing_classes = [c for c in REFS if counts.get(c, 0) < 2]
    if missing_classes:
        raise ValueError(f"Reference classes need at least 2 valid structures: {missing_classes}")

    features, audit = feature_selection_audit(ref, feature_set, min_coverage, near_constant_tol)
    if not features:
        raise ValueError(f"No usable features for feature_set={feature_set}")
    audit.to_csv(out_dir / "feature_selection_audit.csv", index=False)

    Xref, center, scale, ref_missing = robust_fit(ref, features, clip_z)
    ref_meta_cols = [c for c in ["dataset", "structure_id", "source_path", "formula_reduced", "label_order"] if c in ref.columns]
    ref_scores = score_reference_training(ref[ref_meta_cols].copy(), Xref, ref["label_order"], k)
    ref_scores["feature_missing_fraction"] = ref_missing
    ref_scores.to_csv(out_dir / "reference_validation_scores.csv", index=False)

    confusion = pd.crosstab(ref_scores["label_order"], ref_scores["nearest_reference_branch"], normalize="index")
    confusion = confusion.reindex(index=REFS, columns=REFS, fill_value=0.0)
    confusion.to_csv(out_dir / "reference_branch_confusion.csv")
    validation_summary(ref_scores).to_csv(out_dir / "reference_validation_summary.csv", index=False)
    reference_support_summary(ref_scores).to_csv(out_dir / "reference_support_summary.csv", index=False)

    pd.DataFrame({"feature": features, "center": center, "scale": scale}).to_csv(out_dir / "feature_manifest.csv", index=False)

    ref_arrays = {c: Xref[ref["label_order"].eq(c).to_numpy(bool)] for c in REFS}

    # Score queries only; preserve parse failures in the output.
    role = df.get("role", pd.Series("query", index=df.index)).astype(str)
    query_mask = ~role.eq("reference")
    query_df = df[query_mask].copy()
    q_ok = query_df["parse_success"].fillna(0).astype(int).eq(1)
    scored_parts = []

    if q_ok.any():
        good = query_df[q_ok].copy()
        Xq, q_missing = robust_transform(good, features, center, scale, clip_z)
        qmeta_cols = [c for c in ["dataset", "structure_id", "source_path", "formula_reduced", "label_order", "role"] if c in good.columns]
        qs = score_query(good[qmeta_cols].copy(), Xq, ref_arrays, k)
        qs["feature_missing_fraction"] = q_missing
        qs["score_status"] = "ok"
        scored_parts.append(qs)

    if (~q_ok).any():
        bad = query_df[~q_ok].copy()
        cols = [c for c in ["dataset", "structure_id", "source_path", "formula_reduced", "label_order", "role", "parse_error"] if c in bad.columns]
        qb = bad[cols].copy()
        qb["score_status"] = "parse_failed"
        scored_parts.append(qb)

    query_scores = pd.concat(scored_parts, ignore_index=True, sort=False) if scored_parts else pd.DataFrame()
    if len(query_scores):
        okmask = query_scores["score_status"].eq("ok")
        qok = add_reference_support_percentile(query_scores[okmask], ref_scores)
        qbad = query_scores[~okmask]
        query_scores = pd.concat([qok, qbad], ignore_index=True, sort=False)

    query_scores.to_csv(out_dir / "query_scores.csv", index=False)
    query_summary = summarize_queries(query_scores)
    query_summary.to_csv(out_dir / "query_summary.csv", index=False)

    model_meta = {
        "feature_set": feature_set,
        "registered_descriptor_count": len(REGISTERED_DESCRIPTORS),
        "candidate_feature_count": len(FEATURE_SETS[feature_set]),
        "n_features": len(features),
        "features": features,
        "knn_k": int(k),
        "clip_z": float(clip_z),
        "min_feature_coverage": float(min_coverage),
        "near_constant_tol": float(near_constant_tol),
        "magndata_sha_dedup": bool(magndata_dedup),
        "reference_counts": {c: int(counts.get(c, 0)) for c in REFS},
        "dedup_report": dedup_report,
    }
    (out_dir / "model_metadata.json").write_text(json.dumps(model_meta, indent=2), encoding="utf-8")

    return {
        "name": out_dir.name,
        "feature_set": feature_set,
        "n_features": len(features),
        "query_scores": query_scores,
        "query_summary": query_summary,
        "reference_scores": ref_scores,
        "validation_summary": validation_summary(ref_scores),
        "dedup_report": dedup_report,
    }


def cluster_bootstrap_ci(good: pd.DataFrame, n_boot: int, rng: np.random.Generator) -> dict:
    if len(good) == 0:
        return {}

    if "formula_reduced" in good.columns:
        cluster = good["formula_reduced"].astype("string")
        cluster = cluster.fillna("__SID__" + good["structure_id"].astype(str))
    else:
        cluster = good["structure_id"].astype(str)

    groups = {}
    for key, idx in cluster.groupby(cluster, dropna=False).groups.items():
        groups[str(key)] = np.asarray(list(idx), dtype=int)
    keys = list(groups)
    if not keys:
        return {}

    pos = {idx: i for i, idx in enumerate(good.index)}
    group_pos = [np.asarray([pos[int(i)] for i in groups[k]], dtype=int) for k in keys]

    magnetic = pd.to_numeric(good["is_closer_to_magnetic_reference_than_NM"], errors="coerce").to_numpy(float)
    contrast = pd.to_numeric(good["magnetic_reference_vs_NM_contrast"], errors="coerce").to_numpy(float)
    dmag = pd.to_numeric(good["nearest_magnetic_reference_distance"], errors="coerce").to_numpy(float)

    vals = np.empty((n_boot, 3), dtype=float)
    n_clusters = len(group_pos)
    for b in range(n_boot):
        sampled = rng.integers(0, n_clusters, size=n_clusters)
        idx = np.concatenate([group_pos[int(i)] for i in sampled])
        vals[b, 0] = np.nanmean(magnetic[idx])
        vals[b, 1] = np.nanmedian(contrast[idx])
        vals[b, 2] = np.nanmedian(dmag[idx])

    def ci(col):
        return tuple(np.nanquantile(vals[:, col], [0.025, 0.975]))

    m_lo, m_hi = ci(0)
    c_lo, c_hi = ci(1)
    d_lo, d_hi = ci(2)
    return {
        "magnetic_fraction_ci_low": float(m_lo),
        "magnetic_fraction_ci_high": float(m_hi),
        "median_contrast_ci_low": float(c_lo),
        "median_contrast_ci_high": float(c_hi),
        "median_dmag_ci_low": float(d_lo),
        "median_dmag_ci_high": float(d_hi),
        "bootstrap_clusters": int(n_clusters),
    }


def generator_benchmark_with_ci(query_scores: pd.DataFrame, n_boot: int, seed: int) -> pd.DataFrame:
    base = summarize_queries(query_scores)
    extra = []
    rng_master = np.random.default_rng(seed)
    for ds, g in query_scores.groupby("dataset", dropna=False):
        good = g[g["score_status"].eq("ok")].copy()
        sub_seed = int(rng_master.integers(0, 2**32 - 1))
        ci = cluster_bootstrap_ci(good, n_boot, np.random.default_rng(sub_seed)) if n_boot > 0 else {}
        ci["dataset"] = ds
        extra.append(ci)
    ex = pd.DataFrame(extra)
    return base.merge(ex, on="dataset", how="left") if len(ex) else base


def spearman_rank_corr(x: pd.Series, y: pd.Series) -> float:
    z = pd.DataFrame({"x": pd.to_numeric(x, errors="coerce"), "y": pd.to_numeric(y, errors="coerce")}).dropna()
    if len(z) < 3 or z["x"].nunique() < 2 or z["y"].nunique() < 2:
        return np.nan
    return float(z["x"].rank(method="average").corr(z["y"].rank(method="average"), method="pearson"))


def missingness_sensitivity(query_scores: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ds, g in query_scores.groupby("dataset", dropna=False):
        good = g[g["score_status"].eq("ok")].copy()
        if not len(good):
            continue
        rows.append({
            "dataset": ds,
            "n_scored": len(good),
            "median_feature_missing_fraction": float(good["feature_missing_fraction"].median()),
            "fraction_missing_gt_0p20": float((good["feature_missing_fraction"] > 0.20).mean()),
            "spearman_missing_vs_contrast": spearman_rank_corr(good["feature_missing_fraction"], good["magnetic_reference_vs_NM_contrast"]),
            "spearman_missing_vs_dmag": spearman_rank_corr(good["feature_missing_fraction"], good["nearest_magnetic_reference_distance"]),
        })
    return pd.DataFrame(rows)


def group_metrics(g: pd.DataFrame) -> dict:
    good = g[g["score_status"].eq("ok")].copy()
    n = len(g)
    n_good = len(good)
    unique_formula = good["formula_reduced"].dropna().astype(str).nunique() if "formula_reduced" in good else n_good
    return {
        "n_structures": int(n),
        "n_scored": int(n_good),
        "validity_fraction": n_good / max(n, 1),
        "n_unique_formulas": int(unique_formula),
        "formula_diversity_fraction": unique_formula / max(n_good, 1),
        "fraction_closer_to_magnetic_reference_than_NM": float(good["is_closer_to_magnetic_reference_than_NM"].mean()) if n_good else np.nan,
        "median_contrast": float(good["magnetic_reference_vs_NM_contrast"].median()) if n_good else np.nan,
        "median_dmag": float(good["nearest_magnetic_reference_distance"].median()) if n_good else np.nan,
        "median_support_percentile": float(good["magnetic_reference_support_percentile"].median()) if n_good and "magnetic_reference_support_percentile" in good else np.nan,
    }


def grouped_table(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    rows = []
    for keys, g in df.groupby(by, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = {c: v for c, v in zip(by, keys)}
        row.update(group_metrics(g))
        rows.append(row)
    return pd.DataFrame(rows)


def make_condition_tables(query_scores: pd.DataFrame, manifest: pd.DataFrame, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    keep = [
        "dataset", "structure_id", "generator_family", "variant", "benchmark_group",
        "condition_path", "condition_leaf", "target_formula", "seed", "n_requested",
        "mattergen_mgd", "mattergen_guidance", "concdvae_condition", "crystalformer_series",
        "sha256",
    ]
    keep = [c for c in keep if c in manifest.columns]
    m = manifest[keep].drop_duplicates(["dataset", "structure_id"])
    q = query_scores.merge(m, on=["dataset", "structure_id"], how="left", validate="many_to_one")
    q.to_csv(out_dir / "query_scores_with_provenance.csv", index=False)

    if "mattergen_mgd" in q.columns:
        z = q[q["generator_family"].astype(str).eq("mattergen") & q["mattergen_mgd"].notna()].copy()
        z["mattergen_mgd"] = pd.to_numeric(z["mattergen_mgd"], errors="coerce")
        if len(z):
            grouped_table(z, ["dataset", "variant", "mattergen_mgd"]).to_csv(out_dir / "mattergen_by_mgd.csv", index=False)
            if "seed" in z.columns:
                grouped_table(z, ["dataset", "variant", "seed"]).to_csv(out_dir / "mattergen_by_seed.csv", index=False)

    if "concdvae_condition" in q.columns:
        z = q[q["generator_family"].astype(str).eq("concdvae") & q["concdvae_condition"].notna()].copy()
        if len(z):
            grouped_table(z, ["dataset", "variant", "concdvae_condition"]).to_csv(out_dir / "concdvae_by_condition.csv", index=False)

    if "crystalformer_series" in q.columns:
        z = q[q["generator_family"].astype(str).eq("crystalformer") & q["crystalformer_series"].notna()].copy()
        if len(z):
            grouped_table(z, ["dataset", "crystalformer_series", "seed"]).to_csv(out_dir / "crystalformer_by_series_seed.csv", index=False)

    if "target_formula" in q.columns:
        z = q[q["generator_family"].astype(str).eq("crystalllm") & q["target_formula"].notna()].copy()
        if len(z):
            grouped_table(z, ["dataset", "target_formula"]).to_csv(out_dir / "crystalllm_by_target_formula.csv", index=False)

    # Base -> tuned/refined comparison at dataset level.
    summary = summarize_queries(query_scores)
    if {"dataset", "generator_family", "variant"}.issubset(m.columns):
        dsmeta = m[["dataset", "generator_family", "variant"]].drop_duplicates("dataset")
        s = summary.merge(dsmeta, on="dataset", how="left")
        rows = []
        for fam, g in s.groupby("generator_family", dropna=False):
            base = g[g["variant"].astype(str).str.lower().eq("base")]
            alt = g[~g["variant"].astype(str).str.lower().eq("base")]
            if len(base) != 1 or len(alt) != 1:
                continue
            b = base.iloc[0]
            a = alt.iloc[0]
            rows.append({
                "generator_family": fam,
                "base_dataset": b["dataset"],
                "comparison_dataset": a["dataset"],
                "comparison_variant": a["variant"],
                "delta_validity_fraction": a["parse_success_fraction"] - b["parse_success_fraction"],
                "delta_formula_diversity": a["formula_diversity_fraction"] - b["formula_diversity_fraction"],
                "delta_magnetic_fraction": a["fraction_closer_to_magnetic_reference_than_NM"] - b["fraction_closer_to_magnetic_reference_than_NM"],
                "delta_median_contrast": a["median_magnetic_reference_vs_NM_contrast"] - b["median_magnetic_reference_vs_NM_contrast"],
                "delta_median_dmag": a["median_nearest_magnetic_reference_distance"] - b["median_nearest_magnetic_reference_distance"],
            })
        pd.DataFrame(rows).to_csv(out_dir / "base_vs_tuned_shifts.csv", index=False)


def compare_variants(variant_results: list[dict], out_dir: Path):
    rows = []
    for vr in variant_results:
        vname = vr["name"]
        vsum = vr["validation_summary"].set_index("metric")["value"].to_dict()
        for _, r in vr["query_summary"].iterrows():
            rows.append({
                "variant": vname,
                "feature_set": vr["feature_set"],
                "n_features": vr["n_features"],
                "dataset": r["dataset"],
                "fraction_closer_to_magnetic_reference_than_NM": r["fraction_closer_to_magnetic_reference_than_NM"],
                "median_contrast": r["median_magnetic_reference_vs_NM_contrast"],
                "median_dmag": r["median_nearest_magnetic_reference_distance"],
                "median_support_percentile": r.get("median_magnetic_reference_support_percentile", np.nan),
                "reference_magnetic_sensitivity": vsum.get("magnetic_reference_sensitivity", np.nan),
                "reference_NM_specificity": vsum.get("NM_specificity", np.nan),
                "reference_balanced_accuracy": vsum.get("binary_balanced_accuracy", np.nan),
            })
    pd.DataFrame(rows).to_csv(out_dir / "variant_comparison.csv", index=False)


def main():
    ap = argparse.ArgumentParser(
        description=(
            "Re-fit/re-score CIF magnetic-reference models from an already extracted "
            "structure_features.csv. No CIFs are parsed and no CrystalNN/pair extraction is run."
        )
    )
    ap.add_argument("--features", required=True, type=Path, help="Full structure_features.csv from the completed extraction")
    ap.add_argument("--manifest", required=True, type=Path, help="cif_manifest.csv from dataset preparation")
    ap.add_argument("--output", type=Path, default=Path("analysis_v1"))
    ap.add_argument("--knn-k", type=int, default=15)
    ap.add_argument("--clip-z", type=float, default=8.0)
    ap.add_argument("--min-feature-coverage", type=float, default=0.20)
    ap.add_argument("--near-constant-tol", type=float, default=1e-8)
    ap.add_argument("--bootstrap", type=int, default=500, help="Formula-cluster bootstrap replicates for main model; 0 disables")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    if not args.features.exists():
        raise FileNotFoundError(args.features)
    if not args.manifest.exists():
        raise FileNotFoundError(args.manifest)

    args.output.mkdir(parents=True, exist_ok=True)
    descriptor_policy_table().to_csv(args.output / "descriptor_policy.csv", index=False)
    print(f"Reading extracted descriptors: {args.features}", flush=True)
    df = pd.read_csv(args.features, low_memory=False)
    manifest = pd.read_csv(args.manifest, low_memory=False)

    required = {"dataset", "structure_id", "parse_success", "label_order", "role"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"structure_features.csv is missing required columns: {missing}")

    # Normalize join keys once.
    df["dataset"] = df["dataset"].astype(str).str.lower()
    manifest["dataset"] = manifest["dataset"].astype(str).str.lower()
    df["structure_id"] = df["structure_id"].astype(str)
    manifest["structure_id"] = manifest["structure_id"].astype(str)
    df["label_order"] = df["label_order"].map(canon_label)

    variants = []
    specs = [
        ("main", "main", False),
        ("ablation_composition", "composition", False),
        ("ablation_magnetic_graph", "magnetic_graph", False),
        ("sensitivity_magndata_dedup", "main", True),
    ]

    for out_name, feature_set, dedup in specs:
        print(f"\n=== {out_name}: feature_set={feature_set}, MAGNDATA_dedup={dedup} ===", flush=True)
        vr = run_variant(
            df=df,
            out_dir=args.output / out_name,
            feature_set=feature_set,
            k=args.knn_k,
            clip_z=args.clip_z,
            min_coverage=args.min_feature_coverage,
            near_constant_tol=args.near_constant_tol,
            magndata_dedup=dedup,
            manifest=manifest,
        )
        variants.append(vr)
        val = vr["validation_summary"].set_index("metric")["value"].to_dict()
        print(
            f"features={vr['n_features']}; "
            f"mag-sensitivity={val.get('magnetic_reference_sensitivity', np.nan):.4f}; "
            f"NM-specificity={val.get('NM_specificity', np.nan):.4f}; "
            f"balanced={val.get('binary_balanced_accuracy', np.nan):.4f}",
            flush=True,
        )
        if vr["dedup_report"]:
            print(f"MAGNDATA dedup: {vr['dedup_report']}", flush=True)

    tables = args.output / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    compare_variants(variants, tables)

    main_result = variants[0]
    print(f"\nBootstrap ({args.bootstrap} replicates, formula-clustered)...", flush=True)
    benchmark = generator_benchmark_with_ci(main_result["query_scores"], args.bootstrap, args.seed)
    benchmark.to_csv(tables / "generator_benchmark_with_ci.csv", index=False)
    missingness_sensitivity(main_result["query_scores"]).to_csv(tables / "missingness_sensitivity.csv", index=False)
    make_condition_tables(main_result["query_scores"], manifest, tables)

    run_meta = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "features_path": str(args.features.resolve()),
        "features_sha256": sha256_file(args.features),
        "manifest_path": str(args.manifest.resolve()),
        "manifest_sha256": sha256_file(args.manifest),
        "knn_k": args.knn_k,
        "clip_z": args.clip_z,
        "min_feature_coverage": args.min_feature_coverage,
        "near_constant_tol": args.near_constant_tol,
        "bootstrap": args.bootstrap,
        "seed": args.seed,
        "variants": [
            {
                "name": v["name"],
                "feature_set": v["feature_set"],
                "n_features": v["n_features"],
                "dedup_report": v["dedup_report"],
            }
            for v in variants
        ],
    }
    (args.output / "analysis_manifest.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")

    print("\nDone. No CIF extraction was performed.", flush=True)
    print(f"Main outputs: {args.output / 'main'}", flush=True)
    print(f"Comparison tables: {tables}", flush=True)


if __name__ == "__main__":
    main()
