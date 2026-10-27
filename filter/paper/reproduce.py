"""Reproduce publication tables and figures from canonical post-extraction outputs.

This entry point does not parse CIFs. It expects the canonical post-extraction
reference/query score tables and optional DFT/robustness inputs described in
``configs/paper.example.json``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import figures
from .analysis import merge_dft_fm_init


def _resolve(base: Path, value):
    if value in (None, ""):
        return None
    p = Path(value)
    return p if p.is_absolute() else (base / p).resolve()


def load_reproduction_config(path: str | Path) -> dict:
    path = Path(path).resolve()
    cfg = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    path_keys = [
        "reference_scores", "query_scores", "feature_manifest",
        "ablation_reference", "ablation_generator", "afmfm_subset",
        "sha_reference_sensitivity", "sha_generator_sensitivity",
        "sha_dft_sensitivity", "dft_join", "dft_fm_init", "output_dir",
    ]
    for key in path_keys:
        if key in cfg:
            cfg[key] = _resolve(base, cfg[key])
    return cfg


def _require(path: Path | None, label: str) -> Path:
    if path is None:
        raise ValueError(f"Missing required paper config path: {label}")
    if not Path(path).exists():
        raise FileNotFoundError(f"{label}: {path}")
    return Path(path)


def _build_ablation_tables_from_analysis_root(analysis_root: Path, outdir: Path) -> tuple[Path, Path]:
    """Convert canonical run_reference_benchmark outputs to figure-ready ablation tables."""
    variants = {
        "full": "main",
        "composition_only": "ablation_composition",
        "magnetic_topology": "ablation_magnetic_graph",
    }
    ref_rows = []
    generator_rows = []

    main_summary = pd.read_csv(analysis_root / "main" / "query_summary.csv")
    main_map = main_summary.set_index("dataset")["fraction_closer_to_magnetic_reference_than_NM"].to_dict()

    for representation, folder in variants.items():
        fm = pd.read_csv(analysis_root / folder / "feature_manifest.csv")
        vs = pd.read_csv(analysis_root / folder / "reference_validation_summary.csv")
        val = vs.set_index("metric")["value"].to_dict()
        ref_rows.append({
            "main_candidate": "default",
            "representation": representation,
            "n_features": int(len(fm)),
            "balanced_accuracy": float(val["binary_balanced_accuracy"]),
        })
        if representation == "full":
            continue
        qs = pd.read_csv(analysis_root / folder / "query_summary.csv")
        for _, row in qs.iterrows():
            ds = str(row["dataset"])
            ab = float(row["fraction_closer_to_magnetic_reference_than_NM"])
            main = float(main_map[ds])
            generator_rows.append({
                "main_candidate": "default",
                "dataset": ds,
                "ablation": representation,
                "main_fmag": main,
                "ablation_fmag": ab,
                "delta_fmag": ab - main,
            })

    outdir.mkdir(parents=True, exist_ok=True)
    ref_path = outdir / "figure2_reference_ablation.csv"
    gen_path = outdir / "figure2_generator_ablation.csv"
    pd.DataFrame(ref_rows).to_csv(ref_path, index=False)
    pd.DataFrame(generator_rows).to_csv(gen_path, index=False)
    return ref_path, gen_path


def _build_dft_join(query_scores: Path, raw_dft: Path, outdir: Path) -> Path:
    query = pd.read_csv(query_scores, low_memory=False)
    merged = merge_dft_fm_init(raw_dft, query)
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / "dft_fm_init_join.csv"
    merged.to_csv(path, index=False)
    return path


def reproduce(config_path: str | Path, *, strict: bool = True, write_components: bool = False) -> dict:
    cfg = load_reproduction_config(config_path)
    figures.configure_style()

    out = Path(cfg.get("output_dir") or "paper_output")
    out.mkdir(parents=True, exist_ok=True)
    derived = out / "derived_tables"
    derived.mkdir(parents=True, exist_ok=True)

    reference_scores = _require(cfg.get("reference_scores"), "reference_scores")
    query_scores = _require(cfg.get("query_scores"), "query_scores")
    feature_manifest = _require(cfg.get("feature_manifest"), "feature_manifest")

    ab_ref = cfg.get("ablation_reference")
    ab_gen = cfg.get("ablation_generator")
    analysis_root = _resolve(Path(config_path).resolve().parent, cfg.get("analysis_root")) if cfg.get("analysis_root") else None
    if (ab_ref is None or ab_gen is None) and analysis_root is not None:
        ab_ref, ab_gen = _build_ablation_tables_from_analysis_root(Path(analysis_root), derived)

    dft_join = cfg.get("dft_join")
    if dft_join is None and cfg.get("dft_fm_init") is not None:
        dft_join = _build_dft_join(query_scores, _require(cfg.get("dft_fm_init"), "dft_fm_init"), derived)
    dft_join = _require(dft_join, "dft_join or dft_fm_init")

    bundle = figures.load_inputs(reference_scores, query_scores, dft_join, feature_manifest)
    ref = bundle["reference"]
    query = bundle["query"]
    dft = bundle["dft"]

    n_bootstrap = int(cfg.get("n_bootstrap", 1000))
    seed = int(cfg.get("seed", 42))
    dpi = int(cfg.get("dpi", 600))

    ref_summary = figures.build_reference_summary(ref)
    gen_summary = figures.build_generator_summary(query, n_bootstrap=n_bootstrap, seed=seed)
    secondary_summary = figures.build_generator_secondary_summary(query)
    dft_summary, dft_overall = figures.build_dft_summary(dft)
    afmfm = figures.load_afmfm_subset(cfg.get("afmfm_subset"))
    sha_ref, sha_gen, sha_dft = figures.load_sha_sensitivity_inputs(
        cfg.get("sha_reference_sensitivity"),
        cfg.get("sha_generator_sensitivity"),
        cfg.get("sha_dft_sensitivity"),
    )

    audit = figures.run_publication_audit(
        bundle=bundle,
        ref_summary=ref_summary,
        gen_summary=gen_summary,
        dft_summary=dft_summary,
        dft_overall=dft_overall,
        strict=strict,
    )

    reference_ablation = generator_ablation = ablation_audit = None
    if ab_ref is not None or ab_gen is not None:
        if ab_ref is None or ab_gen is None:
            raise ValueError("Both ablation_reference and ablation_generator are required")
        reference_ablation, generator_ablation = figures.load_ablation_inputs(
            Path(ab_ref), Path(ab_gen), main_candidate=str(cfg.get("ablation_main_candidate", "default"))
        )
        ablation_audit = figures.audit_ablation_inputs(reference_ablation, generator_ablation)

    tables = out / "tables"
    figures.write_tables(
        out,
        ref_summary,
        gen_summary,
        dft_summary,
        dft_overall,
        audit,
        reference_ablation=reference_ablation,
        generator_ablation=generator_ablation,
        ablation_audit=ablation_audit,
        secondary_summary=secondary_summary,
        afmfm_subset=afmfm,
        sha_ref_sens=sha_ref,
        sha_gen_sens=sha_gen,
        sha_dft_sens=sha_dft,
    )

    main1 = out / "Figure1_rows"
    main2 = out / "Figure2"
    supp = out / "Supplementary"
    figures.build_figure1_row_top(ref, ref_summary, main1, dpi=dpi)
    figures.build_figure1_row_bottom(gen_summary, dft_summary, main1, dpi=dpi)
    if reference_ablation is not None:
        figures.build_figure_ablation(reference_ablation, generator_ablation, main2, dpi=dpi)
    figures.build_figureS1_generator_secondary(secondary_summary, supp, dpi=dpi)
    figures.build_figureS2_dft_details(dft_summary, dft_overall, afmfm, supp, dpi=dpi)
    if sha_ref is not None:
        figures.build_figureS3_sha_sensitivity(sha_ref, sha_gen, sha_dft, supp, dpi=dpi)

    if write_components:
        components = out / "components"
        figures.build_figure1(ref, ref_summary, components, dpi=dpi)
        figures.build_figure2(gen_summary, dft_summary, components, dpi=dpi)

    manifest = {
        "config": str(Path(config_path).resolve()),
        "strict_publication_audit": bool(strict),
        "n_features": audit.get("n_features"),
        "n_reference": audit.get("n_reference"),
        "outputs": {
            "figure1_rows": str(main1),
            "figure2": str(main2),
            "supplementary": str(supp),
            "tables": str(tables),
        },
        "note": "No CIF extraction was run by paper.reproduce.",
    }
    (out / "reproduction_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--no-strict-audit", action="store_true")
    ap.add_argument("--write-components", action="store_true")
    args = ap.parse_args()
    result = reproduce(args.config, strict=not args.no_strict_audit, write_components=args.write_components)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
