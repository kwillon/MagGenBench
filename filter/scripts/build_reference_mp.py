#!/usr/bin/env python3
"""Fit an MP-only (AFM/FM/FiM/NM) CIFMagFilter reference model.

Input: extracted structure_features.csv (the same descriptor schema used by
the published filter). This never re-runs CrystalNN or bond-valence analysis.

The descriptor registry and numerical kernels come from installed cifmagfilter.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from cifmagfilter.core import FEATURE_SETS
from cifmagfilter.reference import (
    feature_selection_audit,
    robust_fit,
    score_reference_training,
)

CLASSES = ["AFM", "FM", "FiM", "NM"]
MAGNETIC = ["AFM", "FM", "FiM"]


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(features_csv: Path, model_dir: Path):
    source = pd.read_csv(features_csv, low_memory=False)
    if "label_order" not in source or "parse_success" not in source:
        raise ValueError("Missing label_order / parse_success columns")

    labels = source["label_order"].fillna("").astype(str).str.strip().map(
        lambda s: "FiM" if s.upper() == "FIM" else s.upper()
    )

    valid = pd.to_numeric(source["parse_success"], errors="coerce").eq(1)
    ref = source.loc[valid & labels.isin(CLASSES)].copy().reset_index(drop=True)
    ref["label_order"] = labels[valid & labels.isin(CLASSES)].to_numpy()

    counts = ref["label_order"].value_counts().to_dict()
    if any(counts.get(c, 0) < 16 for c in CLASSES):
        raise ValueError(f"Reference branches are too small: {counts}")

    features, feature_audit = feature_selection_audit(
        ref, FEATURE_SETS["main"],
        min_coverage=0.20, near_constant_tol=1e-8,
    )

    # Fit scaling only to MP, not to MAGNDATA or generated crystals.
    X, center, scale, missing = robust_fit(
        ref, features, np.ones(len(ref), dtype=bool), clip_z=8.0
    )
    ref_meta_cols = [
        col for col in
        ["dataset", "structure_id", "source_path", "formula_reduced", "label_order"]
        if col in ref.columns
    ]
    scored = score_reference_training(
        ref[ref_meta_cols].copy(),
        X, ref["label_order"], CLASSES, MAGNETIC, k=15
    )
    scored["feature_missing_fraction"] = missing

    out = Path(model_dir)
    out.mkdir(parents=True, exist_ok=True)
    arrays = {
        "feature_names": np.asarray(features, dtype=str),
        "center": center,
        "scale": scale,
        "reference_self_dmag": scored["nearest_magnetic_reference_distance"].to_numpy(float),
        "reference_self_label": ref["label_order"].to_numpy(dtype=str),
    }
    for label in CLASSES:
        arrays[f"ref_{label}"] = X[ref["label_order"].eq(label).to_numpy()]
    np.savez_compressed(out / "reference_filter.npz", **arrays)

    meta = {
        "model_name": "mp_only",
        "reference_classes": CLASSES,
        "magnetic_classes": MAGNETIC,
        "feature_set": "main",
        "feature_names": features,
        "n_features": len(features),
        "knn_k": 15,
        "clip_z": 8.0,
        "min_feature_coverage": 0.20,
        "near_constant_tol": 1e-8,
        "reference_self_policy": "leave_one_out",
        "reference_counts": {c: int(counts[c]) for c in CLASSES},
        "reference_total": len(ref),
        "source_file_sha256": sha256(features_csv),
        "interpretation": "Reference affinity, not prediction of magnetic ground state",
    }
    (out / "reference_filter.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    true = scored["label_order"].astype(str)
    predicted = scored["nearest_reference_branch"].astype(str)
    pos = true.isin(MAGNETIC)
    binary_pred = predicted.ne("NM")

    validation = {
        "n_reference": len(scored),
        "four_branch_agreement": float((true == predicted).mean()),
        "magnetic_reference_sensitivity": float(binary_pred[pos].mean()),
        "NM_specificity": float((~binary_pred[~pos]).mean()),
        "binary_balanced_accuracy": float(
            0.5 * (binary_pred[pos].mean() + (~binary_pred[~pos]).mean())
        ),
        "leave_one_out_reference_scoring": True,
        "scaler_fit_on_all_reference_rows": True,
        "note": "Internal reference consistency, not an independent test cohort",
    }
    (out / "validation_metrics.json").write_text(
        json.dumps(validation, indent=2), encoding="utf-8"
    )
    feature_audit.to_csv(out / "feature_selection_audit.csv", index=False)
    pd.DataFrame({
        "feature": features, "center": center, "scale": scale
    }).to_csv(out / "scaler.csv", index=False)
    scored.to_csv(out / "reference_validation_scores.csv", index=False)

    print(json.dumps({"reference": meta["reference_counts"],
                      "n_features": len(features), "validation": validation},
                     indent=2))
    print(f"Model written to: {out.resolve()}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--features", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    build(a.features.expanduser().resolve(), a.output.expanduser().resolve())


if __name__ == "__main__":
    main()
