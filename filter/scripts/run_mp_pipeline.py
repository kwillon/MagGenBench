#!/usr/bin/env python3
"""Run the four-branch Materials Project reference filter on prepared generators.

Assumes:
  PROJECT/data/generators/<generator>/cifs/*.cif
  PROJECT/filter/ installed as a Python package
  Bundled default model: filter/src/cifmagfilter/data/model/reference_filter.{npz,json}

Does NOT fit a model on generated structures. Explicitly rejects any reference
model that includes MAGNDATA. Saves a complete extraction and scoring audit.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
from cifmagfilter.model import CIFMagFilter


def run(*args):
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", type=Path, default=Path("."))
    p.add_argument("--model-dir", type=Path, default=None)
    p.add_argument("--limit", type=int, default=None,
                   help="Smoke-test cap per generator. Omit for the full run.")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--skip-extract", action="store_true",
                   help="Reuse previously extracted structure_features.csv.")
    args = p.parse_args()

    project = args.project.expanduser().resolve()
    model_dir = args.model_dir.expanduser().resolve() if args.model_dir else None
    generators = project / "data" / "generators"
    out = project / "results" / ("mp_only_smoke" if args.limit else "mp_only")
    out.mkdir(parents=True, exist_ok=True)

    if not generators.is_dir():
        p.error(f"Missing prepared generator directory: {generators}")

    model = CIFMagFilter.from_pretrained(model_dir)
    branches = model.reference_model.metadata["reference_classes"]
    if branches != ["AFM", "FM", "FiM", "NM"]:
        p.error(f"Expected MP-only reference model, got: {branches}")

    datasets = []
    for folder in sorted(generators.iterdir()):
        if not folder.is_dir():
            continue
        cifdir = folder / "cifs"
        if not cifdir.is_dir():
            continue
        n = sum(1 for file in cifdir.iterdir()
                if file.is_file() and file.suffix.lower() == ".cif")
        if n:
            datasets.append({
                "name": folder.name,
                "path": str(cifdir),
                "role": "query",
            })
            print(f"{folder.name}: {n} input CIFs", flush=True)

    if not datasets:
        p.error("No generator/cifs directories with CIFs found.")

    config = {
        "output_dir": str(out),
        "datasets": datasets,
        "extraction": {"reject_disordered": True},
    }
    cfg_path = out / "run_config.json"
    cfg_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    feature_csv = out / "features" / "structure_features.csv"
    if not args.skip_extract:
        cmd = [
            sys.executable, "-m", "cifmagfilter.cli",
            "extract", "--config", str(cfg_path),
            "--sample-seed", str(args.seed),
        ]
        if args.limit is not None:
            cmd += ["--limit", str(args.limit), "--limit-sampling", "auto"]
        run(*cmd)

    if not feature_csv.exists():
        p.error(f"Feature file missing: {feature_csv}")

    raw = pd.read_csv(feature_csv, low_memory=False)
    parsed = pd.to_numeric(
        raw["parse_success"], errors="coerce"
    ).fillna(0).eq(1)
    eligible = raw.loc[parsed].copy()
    failures = raw.loc[~parsed].copy()

    # Disordered CIFs should already fail extraction. This is an extra check.
    if "structure__has_disorder" in eligible:
        disordered = pd.to_numeric(
            eligible["structure__has_disorder"], errors="coerce"
        ).fillna(0).ne(0)
        if disordered.any():
            failures = pd.concat([failures, eligible.loc[disordered]])
            eligible = eligible.loc[~disordered]

    failures.to_csv(out / "rejected_structures.csv", index=False)
    if eligible.empty:
        raise RuntimeError("All CIFs failed canonical extraction.")

    print(f"Scoring {len(eligible)} valid rows with MP-only reference model...", flush=True)
    scores = model.score_features(eligible)
    scores["score_status"] = "ok"

    # Preserve generation provenance from reorganizer manifests.
    provenance = []
    for folder in generators.iterdir():
        manifest = folder / "manifest.csv"
        if not manifest.is_file():
            continue
        m = pd.read_csv(manifest, dtype=str)
        if "cif_id" not in m:
            continue
        m["dataset"] = folder.name
        m["structure_id"] = m["cif_id"]
        keep = [
            c for c in [
                "dataset", "structure_id", "original_file", "raw_file",
                "generation_group", "generation_run", "seed", "mgd",
                "guidance", "target_formula", "sha256"
            ] if c in m
        ]
        provenance.append(m[keep])
    if provenance:
        prov = pd.concat(provenance, ignore_index=True)
        prov = prov.drop_duplicates(["dataset", "structure_id"])
        scores = scores.merge(prov, on=["dataset", "structure_id"],
                              how="left", validate="many_to_one")

    scores.to_csv(out / "generator_scores.csv", index=False)
    print("Scored results:", out / "generator_scores.csv", flush=True)

    summaries = []
    for dataset, all_rows in raw.groupby("dataset", sort=True):
        good = scores[scores["dataset"].eq(dataset)]
        contrast = pd.to_numeric(
            good.get("magnetic_reference_vs_NM_contrast", pd.Series(dtype=float)),
            errors="coerce"
        )
        n_pos = int((contrast > 0).sum())
        n_neg = int((contrast <= 0).sum())
        summary = {
            "dataset": dataset,
            "n_input": len(all_rows),
            "n_scored": len(good),
            "n_rejected": len(all_rows) - len(good),
            "magnetic_like": n_pos,
            "NM_like": n_neg,
            "fraction_magnetic_like": n_pos / len(good) if len(good) else float("nan"),
            "median_contrast": float(contrast.median()) if len(good) else float("nan"),
            "median_distance_to_magnetic_references": (
                float(good["nearest_magnetic_reference_distance"].median())
                if len(good) else float("nan")
            ),
            "n_unique_reduced_formulas": (
                int(good["formula_reduced"].dropna().nunique())
                if "formula_reduced" in good else 0
            ),
        }
        summaries.append(summary)
    pd.DataFrame(summaries).to_csv(out / "generator_summary.csv", index=False)

    print("\nReference classes:", branches)
    print(pd.DataFrame(summaries).to_string(index=False))
    print("\nOutput directory:", out)


if __name__ == "__main__":
    main()
