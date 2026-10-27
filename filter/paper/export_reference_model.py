"""Export the canonical 45-feature reference model from post-extraction descriptors.

This is a post-extraction operation. It does not parse CIFs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from cifmagfilter.reference import (
    DEFAULT_MAGNETIC_CLASSES,
    DEFAULT_REFERENCE_CLASSES,
    canon_label,
    robust_transform,
    score_reference_training,
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--features", required=True, type=Path)
    ap.add_argument("--scaler", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--knn-k", type=int, default=15)
    ap.add_argument("--clip-z", type=float, default=8.0)
    args = ap.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.features, low_memory=False)
    scaler = pd.read_csv(args.scaler)
    feature_names = scaler["feature"].astype(str).tolist()
    center = pd.to_numeric(scaler["center"], errors="raise").to_numpy(float)
    scale = pd.to_numeric(scaler["scale"], errors="raise").to_numpy(float)
    if len(feature_names) != 45:
        raise AssertionError(f"Expected 45 canonical features, found {len(feature_names)}")

    valid = pd.to_numeric(df["parse_success"], errors="coerce").fillna(0).astype(int).eq(1)
    labels = df["label_order"].map(canon_label)
    ref = df[valid & labels.isin(DEFAULT_REFERENCE_CLASSES)].copy().reset_index(drop=True)
    ref["label_order"] = ref["label_order"].map(canon_label)

    X, missing = robust_transform(ref, feature_names, center, scale, args.clip_z)
    meta_cols = [c for c in ["dataset", "structure_id", "formula_reduced", "label_order"] if c in ref]
    scored = score_reference_training(
        ref[meta_cols].copy(),
        X,
        ref["label_order"],
        DEFAULT_REFERENCE_CLASSES,
        DEFAULT_MAGNETIC_CLASSES,
        args.knn_k,
    )
    scored["feature_missing_fraction"] = missing

    arrays: dict[str, np.ndarray] = {
        "feature_names": np.asarray(feature_names, dtype=str),
        "center": center,
        "scale": scale,
        "reference_self_dmag": scored["nearest_magnetic_reference_distance"].to_numpy(float),
        "reference_self_label": np.asarray(scored["label_order"].astype(str).tolist(), dtype="U16"),
    }
    for branch in DEFAULT_REFERENCE_CLASSES:
        arrays[f"ref_{branch}"] = X[ref["label_order"].eq(branch).to_numpy(bool)]

    npz_path = args.output_dir / "reference_filter.npz"
    np.savez_compressed(npz_path, **arrays)

    counts = ref["label_order"].value_counts().to_dict()
    metadata = {
        "model_name": "default",
        "paper_model": "default",
        "reference_classes": DEFAULT_REFERENCE_CLASSES,
        "magnetic_classes": DEFAULT_MAGNETIC_CLASSES,
        "n_features": len(feature_names),
        "feature_names": feature_names,
        "knn_k": args.knn_k,
        "clip_z": args.clip_z,
        "reference_self_policy": "leave_one_out",
        "reference_counts": {b: int(counts.get(b, 0)) for b in DEFAULT_REFERENCE_CLASSES},
        "reference_total": int(len(ref)),
        "features_source_sha256": sha256_file(args.features),
        "scaler_source_sha256": sha256_file(args.scaler),
        "interpretation": (
            "Nearest branch denotes affinity to an empirical reference manifold, not a predicted magnetic ground state."
        ),
    }
    json_path = args.output_dir / "reference_filter.json"
    json_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    scored.to_csv(args.output_dir / "reference_validation_scores.csv", index=False)

    artifact_manifest = {
        "reference_filter.npz": sha256_file(npz_path),
        "reference_filter.json": sha256_file(json_path),
        "reference_validation_scores.csv": sha256_file(args.output_dir / "reference_validation_scores.csv"),
    }
    (args.output_dir / "SHA256SUMS.json").write_text(json.dumps(artifact_manifest, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
