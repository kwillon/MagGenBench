"""Cheap post-extraction scientific controls required for the paper release.

No CIF parsing, CrystalNN evaluation, or pair reconstruction is performed.
The script operates only on the canonical ``structure_features.csv`` and the
canonical ordered 45-feature paper manifest.

Controls
--------
1. ``default``: exact canonical 45-feature coordinate list, re-fitted on the
   supplied reference cohort.
2. ``no_computability``: removes algorithm-success / oxidation-state
   computability coordinates from the 45-feature space.
3. ``no_computability_smact``: additionally removes the two SMACT validity
   coordinates.
4. ``no_center_support_summaries``: removes heuristic composite center-support
   summary coordinates while retaining chemistry, family fractions and
   already-extracted pair geometry.
5. Missingness-by-dataset table for every canonical feature.

The center-support control is intentionally a coordinate ablation only. Pair
weights and pair-retention decisions were produced during the canonical
extraction and are not rebuilt here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from cifmagfilter.reference import (
    DEFAULT_MAGNETIC_CLASSES,
    DEFAULT_REFERENCE_CLASSES,
    canon_label,
    robust_fit,
    robust_transform,
    score_reference_training,
    score_against_references,
)

REFS = DEFAULT_REFERENCE_CLASSES
MAG = DEFAULT_MAGNETIC_CLASSES

COMPUTABILITY_FEATURES = [
    "chemistry__bv_success",
    "chemistry__oxi_guess_success",
    "chemistry__oxi_guess_count",
    "chemistry__oxidation_state_coverage",
]

SMACT_FEATURES = [
    "chemistry__smact_valid",
    "chemistry__smact_valid_mixed_valence",
]

CENTER_SUPPORT_SUMMARIES = [
    "magnetic_center__mean_center_confidence",
    "magnetic_center__max_center_confidence",
    "magnetic_center__mean_ionic_score",
    "magnetic_center__mean_metallic_score",
    "magnetic_center__mean_rare_earth_score",
    "magnetic_center__mean_closed_shell_suppression",
]


def binary_reference_metrics(scores: pd.DataFrame) -> dict[str, float]:
    truth_mag = scores["label_order"].isin(MAG).to_numpy(bool)
    pred_mag = ~scores["nearest_reference_branch"].eq("NM").to_numpy(bool)
    tp = int((truth_mag & pred_mag).sum())
    fn = int((truth_mag & ~pred_mag).sum())
    tn = int((~truth_mag & ~pred_mag).sum())
    fp = int((~truth_mag & pred_mag).sum())
    sensitivity = tp / (tp + fn) if tp + fn else np.nan
    specificity = tn / (tn + fp) if tn + fp else np.nan
    balanced = np.nanmean([sensitivity, specificity])
    five = float(scores["label_order"].eq(scores["nearest_reference_branch"]).mean())
    return {
        "five_branch_agreement": five,
        "magnetic_sensitivity": float(sensitivity),
        "nm_specificity": float(specificity),
        "binary_balanced_accuracy": float(balanced),
    }


def fit_and_score_variant(
    df: pd.DataFrame,
    feature_names: list[str],
    *,
    k: int = 15,
    clip_z: float = 8.0,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    valid = pd.to_numeric(df["parse_success"], errors="coerce").fillna(0).astype(int).eq(1)
    labels = df["label_order"].map(canon_label)
    ref = df[valid & labels.isin(REFS)].copy().reset_index(drop=True)
    ref["label_order"] = ref["label_order"].map(canon_label)

    missing = [f for f in feature_names if f not in ref.columns]
    if missing:
        raise ValueError(f"Canonical feature columns missing from structure_features.csv: {missing}")

    Xref, center, scale, miss_ref = robust_fit(
        ref, feature_names, fit_mask=np.ones(len(ref), dtype=bool), clip_z=clip_z
    )
    meta_cols = [c for c in ["dataset", "structure_id", "formula_reduced", "label_order"] if c in ref]
    ref_scores = score_reference_training(
        ref[meta_cols].copy(), Xref, ref["label_order"], REFS, MAG, k
    )
    ref_scores["feature_missing_fraction"] = miss_ref

    ref_arrays = {
        branch: Xref[ref["label_order"].eq(branch).to_numpy(bool)]
        for branch in REFS
    }

    role = df.get("role", pd.Series("query", index=df.index)).astype(str)
    q = df[valid & ~role.eq("reference")].copy().reset_index(drop=True)
    Xq, miss_q = robust_transform(q, feature_names, center, scale, clip_z)
    qmeta = [c for c in ["dataset", "structure_id", "formula_reduced"] if c in q]
    query_scores = score_against_references(q[qmeta].copy(), Xq, ref_arrays, MAG, k)
    query_scores["feature_missing_fraction"] = miss_q

    return ref_scores, query_scores, binary_reference_metrics(ref_scores)


def generator_summary(scores: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for dataset, g in scores.groupby("dataset", sort=True):
        rows.append({
            "dataset": dataset,
            "n": int(len(g)),
            "fmag": float(g["is_closer_to_magnetic_reference_than_NM"].mean()),
            "median_contrast": float(pd.to_numeric(g["magnetic_reference_vs_NM_contrast"], errors="coerce").median()),
            "median_dmag": float(pd.to_numeric(g["nearest_magnetic_reference_distance"], errors="coerce").median()),
        })
    return pd.DataFrame(rows)


def missingness_by_dataset(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    valid = pd.to_numeric(df["parse_success"], errors="coerce").fillna(0).astype(int).eq(1)
    use = df[valid].copy()
    rows = []
    for dataset, g in use.groupby("dataset", sort=True):
        for feature in features:
            x = pd.to_numeric(g[feature], errors="coerce").replace([np.inf, -np.inf], np.nan)
            rows.append({
                "dataset": dataset,
                "feature": feature,
                "n_structures": int(len(g)),
                "coverage": float(x.notna().mean()),
                "missing_fraction": float(x.isna().mean()),
            })
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--features", required=True, type=Path)
    ap.add_argument("--feature-list", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--knn-k", type=int, default=15)
    ap.add_argument("--clip-z", type=float, default=8.0)
    args = ap.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.features, low_memory=False)
    features = pd.read_csv(args.feature_list)["feature"].astype(str).tolist()
    variants = {
        "default": features,
        "no_computability": [f for f in features if f not in COMPUTABILITY_FEATURES],
        "no_computability_smact": [f for f in features if f not in set(COMPUTABILITY_FEATURES + SMACT_FEATURES)],
        "no_center_support_summaries": [f for f in features if f not in CENTER_SUPPORT_SUMMARIES],
    }

    reference_rows = []
    generator_tables = {}
    for name, feats in variants.items():
        ref_scores, query_scores, metrics = fit_and_score_variant(
            df, feats, k=args.knn_k, clip_z=args.clip_z
        )
        reference_rows.append({"variant": name, "n_features": len(feats), **metrics})
        generator_tables[name] = generator_summary(query_scores)

    ref_table = pd.DataFrame(reference_rows)
    ref_table.to_csv(args.output / "reference_control_reference_metrics.csv", index=False)

    main_gen = generator_tables["default"].set_index("dataset")
    rows = []
    for name, table in generator_tables.items():
        d = table.set_index("dataset")
        for dataset in d.index:
            rows.append({
                "variant": name,
                "dataset": dataset,
                "n_features": len(variants[name]),
                "fmag": float(d.loc[dataset, "fmag"]),
                "median_contrast": float(d.loc[dataset, "median_contrast"]),
                "median_dmag": float(d.loc[dataset, "median_dmag"]),
                "delta_fmag_vs_default": float(d.loc[dataset, "fmag"] - main_gen.loc[dataset, "fmag"]),
                "delta_median_contrast_vs_default": float(d.loc[dataset, "median_contrast"] - main_gen.loc[dataset, "median_contrast"]),
                "delta_median_dmag_vs_default": float(d.loc[dataset, "median_dmag"] - main_gen.loc[dataset, "median_dmag"]),
            })
    pd.DataFrame(rows).to_csv(args.output / "reference_control_generator_metrics.csv", index=False)

    miss = missingness_by_dataset(df, features)
    miss.to_csv(args.output / "missingness_by_dataset.csv", index=False)
    miss_summary = (
        miss.groupby("dataset", as_index=False)
        .agg(
            mean_missing_fraction=("missing_fraction", "mean"),
            max_missing_fraction=("missing_fraction", "max"),
            n_features_with_any_missing=("missing_fraction", lambda x: int((x > 0).sum())),
        )
    )
    miss_summary.to_csv(args.output / "missingness_summary_by_dataset.csv", index=False)

    metadata = {
        "knn_k": args.knn_k,
        "clip_z": args.clip_z,
        "feature_count": len(features),
        "controls": {
            name: {
                "n_features": len(feats),
                "removed_features": [f for f in features if f not in feats],
            }
            for name, feats in variants.items()
        },
        "note": (
            "All controls are post-extraction coordinate ablations. The center-support control "
            "does not rebuild pair weights or pair retention."
        ),
    }
    (args.output / "reference_controls_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    print(ref_table.to_string(index=False))
    print(f"Wrote reference controls to {args.output}")


if __name__ == "__main__":
    main()
