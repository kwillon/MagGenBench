"""Canonical reference-space mathematics for CIFMagFilter.

This module is the *single implementation* used by both the public filter and
paper reproduction code for:

- coverage/constant/near-constant feature selection audits;
- reference-median imputation and robust median/IQR scaling;
- Euclidean k-nearest-neighbour reference distances;
- leave-one-out reference self-scoring;
- nearest-reference branch and magnetic-vs-NM contrast calculation.

The functions in this module operate on already extracted numeric descriptor
matrices.  They do not parse CIFs and do not use magnetic labels other than to
partition the reference cohort for distance calculation.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import json
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

DEFAULT_REFERENCE_CLASSES = ["MAGNDATA", "AFM", "FM", "FiM", "NM"]
DEFAULT_MAGNETIC_CLASSES = ["MAGNDATA", "AFM", "FM", "FiM"]


def canon_label(value):
    """Canonicalize known reference labels without inventing new classes."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    s = str(value).strip()
    if s.lower() == "fim":
        return "FiM"
    u = s.upper()
    return u if u in {"MAGNDATA", "AFM", "FM", "NM"} else s


def feature_selection_audit(
    df: pd.DataFrame,
    candidate_features: Sequence[str],
    *,
    min_coverage: float = 0.20,
    near_constant_tol: float = 1e-8,
) -> tuple[list[str], pd.DataFrame]:
    """Select usable features and return a complete audit table.

    A feature is retained when it exists, has sufficient finite coverage,
    contains more than one unique finite value, and its observed span exceeds
    ``near_constant_tol * max(1, abs(median))``.
    """
    selected: list[str] = []
    rows: list[dict[str, object]] = []

    for feature in candidate_features:
        if feature not in df.columns:
            rows.append({
                "feature": feature,
                "selected": 0,
                "reason": "missing_column",
                "coverage": 0.0,
                "n_unique": 0,
                "min": np.nan,
                "max": np.nan,
                "span": np.nan,
                "std": np.nan,
                "median": np.nan,
                "near_constant_threshold": np.nan,
            })
            continue

        x = pd.to_numeric(df[feature], errors="coerce").replace([np.inf, -np.inf], np.nan)
        valid = x.dropna()
        coverage = float(x.notna().mean())
        n_unique = int(valid.nunique(dropna=True))

        if len(valid):
            xmin = float(valid.min())
            xmax = float(valid.max())
            span = float(xmax - xmin)
            std = float(valid.std(ddof=0))
            median = float(valid.median())
            threshold = float(near_constant_tol * max(1.0, abs(median)))
        else:
            xmin = xmax = span = std = median = threshold = np.nan

        keep = True
        reason = "selected"
        if coverage < float(min_coverage):
            keep = False
            reason = "low_coverage"
        elif n_unique <= 1:
            keep = False
            reason = "constant"
        elif not np.isfinite(span) or span <= threshold:
            keep = False
            reason = "near_constant"

        if keep:
            selected.append(feature)

        rows.append({
            "feature": feature,
            "selected": int(keep),
            "reason": reason,
            "coverage": coverage,
            "n_unique": n_unique,
            "min": xmin,
            "max": xmax,
            "span": span,
            "std": std,
            "median": median,
            "near_constant_threshold": threshold,
        })

    return selected, pd.DataFrame(rows)


def select_numeric_features(
    df: pd.DataFrame,
    candidate_features: Sequence[str],
    *,
    min_coverage: float = 0.20,
    near_constant_tol: float = 1e-8,
) -> list[str]:
    selected, _ = feature_selection_audit(
        df,
        candidate_features,
        min_coverage=min_coverage,
        near_constant_tol=near_constant_tol,
    )
    return selected


def robust_fit(
    df: pd.DataFrame,
    feature_cols: Sequence[str],
    fit_mask: np.ndarray | pd.Series | None = None,
    clip_z: float = 8.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Fit the canonical reference transform and transform all supplied rows.

    Missing values are imputed by the fitting cohort median.  Centering uses
    the median.  Scale is ``IQR / 1.349`` with population-standard-deviation
    fallback for degenerate IQR.  Standardized coordinates are clipped to
    ``[-clip_z, clip_z]`` when ``clip_z > 0``.
    """
    feature_cols = list(feature_cols)
    X = (
        df[feature_cols]
        .apply(pd.to_numeric, errors="coerce")
        .astype(float)
        .replace([np.inf, -np.inf], np.nan)
    )

    if fit_mask is None:
        fit_mask_arr = np.ones(len(X), dtype=bool)
    else:
        fit_mask_arr = np.asarray(fit_mask, dtype=bool)
        if len(fit_mask_arr) != len(X):
            raise ValueError("fit_mask length must match dataframe length")

    # Historical public implementation used all rows only as a fallback when
    # fewer than five fitting rows were supplied. Preserve this behavior.
    fit = X.loc[fit_mask_arr] if int(fit_mask_arr.sum()) >= 5 else X
    fill = fit.median(axis=0).fillna(0.0)
    Xf = X.fillna(fill)
    fit_f = Xf.loc[fit_mask_arr] if int(fit_mask_arr.sum()) >= 5 else Xf

    center = fit_f.median(axis=0)
    scale = (fit_f.quantile(0.75) - fit_f.quantile(0.25)) / 1.349
    fallback = fit_f.std(axis=0, ddof=1).replace(0, np.nan).fillna(1.0)
    scale = scale.where(np.isfinite(scale) & (scale > 1e-12), fallback).fillna(1.0)

    Z = (Xf - center) / scale
    if clip_z and clip_z > 0:
        Z = Z.clip(-float(clip_z), float(clip_z))

    missing = X.isna().mean(axis=1).to_numpy(float)
    return (
        Z.to_numpy(float),
        center.to_numpy(float),
        scale.to_numpy(float),
        missing,
    )


def robust_transform(
    df: pd.DataFrame,
    feature_cols: Sequence[str],
    center: np.ndarray,
    scale: np.ndarray,
    clip_z: float = 8.0,
) -> tuple[np.ndarray, np.ndarray]:
    feature_cols = list(feature_cols)
    center = np.asarray(center, dtype=float)
    scale = np.asarray(scale, dtype=float)
    if len(center) != len(feature_cols) or len(scale) != len(feature_cols):
        raise ValueError("center/scale lengths must match feature_cols")

    cols = {
        c: pd.to_numeric(df[c], errors="coerce")
        if c in df.columns
        else pd.Series(np.nan, index=df.index)
        for c in feature_cols
    }
    X = pd.DataFrame(cols, index=df.index).astype(float).replace([np.inf, -np.inf], np.nan)
    Xf = X.fillna(pd.Series(center, index=feature_cols))
    safe_scale = np.where(np.isfinite(scale) & (np.abs(scale) > 1e-12), scale, 1.0)
    Z = (Xf.to_numpy(float) - center) / safe_scale
    if clip_z and clip_z > 0:
        Z = np.clip(Z, -float(clip_z), float(clip_z))
    missing = X.isna().mean(axis=1).to_numpy(float)
    return Z, missing


def knn_distance(X: np.ndarray, reference: np.ndarray, k: int) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    reference = np.asarray(reference, dtype=float)
    if len(reference) == 0:
        return np.full(len(X), np.nan)
    kk = max(1, min(int(k), len(reference)))
    nn = NearestNeighbors(n_neighbors=kk, metric="euclidean").fit(reference)
    return nn.kneighbors(X, return_distance=True)[0].mean(axis=1)


def knn_distance_training(X: np.ndarray, reference_indices: np.ndarray, k: int) -> np.ndarray:
    """Leave the query itself out when it belongs to the scored branch."""
    X = np.asarray(X, dtype=float)
    reference_indices = np.asarray(reference_indices, dtype=int)
    reference = X[reference_indices]
    if len(reference) == 0:
        return np.full(len(X), np.nan)

    n_neighbors = min(max(1, int(k) + 1), len(reference))
    nn = NearestNeighbors(n_neighbors=n_neighbors, metric="euclidean").fit(reference)
    dist, ind = nn.kneighbors(X, return_distance=True)
    local = {int(global_idx): local_idx for local_idx, global_idx in enumerate(reference_indices)}

    out = np.empty(len(X), dtype=float)
    for query_idx in range(len(X)):
        pairs = list(zip(dist[query_idx], ind[query_idx]))
        if query_idx in local:
            target_local_idx = local[query_idx]
            removed = False
            kept: list[float] = []
            for d, j in pairs:
                if not removed and int(j) == target_local_idx:
                    removed = True
                    continue
                kept.append(float(d))
            vals = kept[: max(1, min(int(k), len(kept)))]
        else:
            vals = [float(d) for d, _ in pairs[: max(1, min(int(k), len(pairs)))]]
        out[query_idx] = float(np.mean(vals)) if vals else np.nan
    return out


def finish_scores(
    out: pd.DataFrame,
    reference_classes: Sequence[str] = DEFAULT_REFERENCE_CLASSES,
    magnetic_classes: Sequence[str] = DEFAULT_MAGNETIC_CLASSES,
) -> pd.DataFrame:
    """Add nearest-branch and magnetic-vs-NM contrast columns."""
    reference_classes = list(reference_classes)
    magnetic_classes = [c for c in magnetic_classes if c in reference_classes]
    if "NM" not in reference_classes:
        raise ValueError("NM reference is required for magnetic-vs-NM contrast")
    if not magnetic_classes:
        raise ValueError("At least one magnetic reference class is required")

    D = out[[f"distance_to_{c}" for c in reference_classes]].to_numpy(float)
    safe_D = np.where(np.isfinite(D), D, np.inf)
    idx = np.argmin(safe_D, axis=1)
    all_missing = ~np.isfinite(D).any(axis=1)
    out["nearest_reference_branch"] = [reference_classes[i] for i in idx]
    out.loc[all_missing, "nearest_reference_branch"] = np.nan
    out["nearest_reference_distance"] = D[np.arange(len(out)), idx]
    out.loc[all_missing, "nearest_reference_distance"] = np.nan

    Dm = out[[f"distance_to_{c}" for c in magnetic_classes]].to_numpy(float)
    safe_Dm = np.where(np.isfinite(Dm), Dm, np.inf)
    mi = np.argmin(safe_Dm, axis=1)
    mag_missing = ~np.isfinite(Dm).any(axis=1)
    out["nearest_magnetic_reference_branch"] = [magnetic_classes[i] for i in mi]
    out.loc[mag_missing, "nearest_magnetic_reference_branch"] = np.nan
    out["nearest_magnetic_reference_distance"] = Dm[np.arange(len(out)), mi]
    out.loc[mag_missing, "nearest_magnetic_reference_distance"] = np.nan

    out["distance_to_NM_reference"] = pd.to_numeric(out["distance_to_NM"], errors="coerce")
    out["magnetic_reference_vs_NM_contrast"] = (
        out["distance_to_NM_reference"] - out["nearest_magnetic_reference_distance"]
    )
    denominator = (
        out["distance_to_NM_reference"]
        + out["nearest_magnetic_reference_distance"]
        + 1e-12
    )
    out["relative_magnetic_reference_preference"] = (
        out["magnetic_reference_vs_NM_contrast"] / denominator
    )
    out["is_closer_to_magnetic_reference_than_NM"] = (
        out["magnetic_reference_vs_NM_contrast"].gt(0).astype(int)
    )
    return out


def score_against_references(
    meta: pd.DataFrame,
    X: np.ndarray,
    reference_arrays: Mapping[str, np.ndarray],
    magnetic_classes: Sequence[str] = DEFAULT_MAGNETIC_CLASSES,
    k: int = 15,
) -> pd.DataFrame:
    out = meta.copy()
    reference_classes = list(reference_arrays)
    for cls in reference_classes:
        out[f"distance_to_{cls}"] = knn_distance(X, reference_arrays[cls], k)
    return finish_scores(out, reference_classes, magnetic_classes)


def score_reference_training(
    meta: pd.DataFrame,
    X: np.ndarray,
    labels: pd.Series,
    reference_classes: Sequence[str] = DEFAULT_REFERENCE_CLASSES,
    magnetic_classes: Sequence[str] = DEFAULT_MAGNETIC_CLASSES,
    k: int = 15,
) -> pd.DataFrame:
    out = meta.copy()
    labels = labels.astype(str)
    reference_classes = list(reference_classes)
    for cls in reference_classes:
        ref_idx = np.where(labels.eq(cls).to_numpy(bool))[0]
        out[f"distance_to_{cls}"] = knn_distance_training(X, ref_idx, k)
    return finish_scores(out, reference_classes, magnetic_classes)


def add_reference_support_percentile(
    query_scores: pd.DataFrame,
    reference_scores: pd.DataFrame,
    magnetic_classes: Sequence[str] = DEFAULT_MAGNETIC_CLASSES,
) -> pd.DataFrame:
    out = query_scores.copy()
    magnetic_ref = reference_scores[
        reference_scores["label_order"].isin(list(magnetic_classes))
    ]["nearest_magnetic_reference_distance"].dropna().to_numpy(float)
    magnetic_ref.sort()
    if len(magnetic_ref) == 0:
        out["magnetic_reference_support_percentile"] = np.nan
        return out
    vals = pd.to_numeric(out["nearest_magnetic_reference_distance"], errors="coerce").to_numpy(float)
    p = np.full(len(vals), np.nan)
    ok = np.isfinite(vals)
    p[ok] = 100.0 * np.searchsorted(magnetic_ref, vals[ok], side="right") / len(magnetic_ref)
    out["magnetic_reference_support_percentile"] = p
    return out


def summarize_queries(scored: pd.DataFrame, magnetic_classes: Sequence[str] = DEFAULT_MAGNETIC_CLASSES) -> pd.DataFrame:
    rows = []
    for dataset, group in scored.groupby("dataset", dropna=False):
        good = group[group["score_status"].eq("ok")].copy() if "score_status" in group else group.copy()
        n = len(group)
        unique_formula = (
            good["formula_reduced"].dropna().astype(str).nunique()
            if "formula_reduced" in good
            else len(good)
        )
        row = {
            "dataset": dataset,
            "n_structures": int(n),
            "n_scored": int(len(good)),
            "parse_success_fraction": len(good) / max(n, 1),
            "n_unique_formulas": int(unique_formula),
            "formula_diversity_fraction": unique_formula / max(len(good), 1),
            "fraction_closer_to_magnetic_reference_than_NM": (
                float(good["is_closer_to_magnetic_reference_than_NM"].mean()) if len(good) else np.nan
            ),
            "median_magnetic_reference_vs_NM_contrast": (
                float(good["magnetic_reference_vs_NM_contrast"].median()) if len(good) else np.nan
            ),
            "median_nearest_magnetic_reference_distance": (
                float(good["nearest_magnetic_reference_distance"].median()) if len(good) else np.nan
            ),
        }
        for branch in magnetic_classes:
            row[f"fraction_nearest_magnetic_reference_branch_{branch}"] = (
                float(good["nearest_magnetic_reference_branch"].eq(branch).mean()) if len(good) else np.nan
            )
        rows.append(row)
    return pd.DataFrame(rows)


@dataclass(frozen=True)
class ReferenceModel:
    """Serializable reference-space model loaded from public model artifacts."""

    metadata: dict
    feature_names: list[str]
    center: np.ndarray
    scale: np.ndarray
    reference_arrays: dict[str, np.ndarray]
    reference_self_dmag: np.ndarray | None = None
    reference_self_label: np.ndarray | None = None

    @classmethod
    def load(cls, model_dir: str | Path) -> "ReferenceModel":
        model_dir = Path(model_dir)
        metadata = json.loads((model_dir / "reference_filter.json").read_text(encoding="utf-8"))
        z = np.load(model_dir / "reference_filter.npz", allow_pickle=False)
        feature_names = z["feature_names"].astype(str).tolist()
        reference_arrays = {
            ref: z[f"ref_{ref}"].astype(float)
            for ref in metadata["reference_classes"]
        }
        return cls(
            metadata=metadata,
            feature_names=feature_names,
            center=z["center"].astype(float),
            scale=z["scale"].astype(float),
            reference_arrays=reference_arrays,
            reference_self_dmag=(z["reference_self_dmag"].astype(float) if "reference_self_dmag" in z.files else None),
            reference_self_label=(z["reference_self_label"].astype(str) if "reference_self_label" in z.files else None),
        )

    def transform(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        return robust_transform(
            df,
            self.feature_names,
            self.center,
            self.scale,
            float(self.metadata.get("clip_z", 8.0)),
        )

    def score(self, meta: pd.DataFrame, X: np.ndarray, *, add_support_percentile: bool = True) -> pd.DataFrame:
        scored = score_against_references(
            meta,
            X,
            self.reference_arrays,
            self.metadata.get("magnetic_classes", DEFAULT_MAGNETIC_CLASSES),
            int(self.metadata.get("knn_k", 15)),
        )
        if add_support_percentile and self.reference_self_dmag is not None:
            labels = self.reference_self_label
            ref_dist = self.reference_self_dmag
            if labels is not None and len(labels) == len(ref_dist):
                magnetic = set(self.metadata.get("magnetic_classes", DEFAULT_MAGNETIC_CLASSES))
                ref_dist = ref_dist[np.array([str(x) in magnetic for x in labels], dtype=bool)]
            ref_dist = ref_dist[np.isfinite(ref_dist)]
            ref_dist.sort()
            vals = pd.to_numeric(scored["nearest_magnetic_reference_distance"], errors="coerce").to_numpy(float)
            pct = np.full(len(vals), np.nan)
            ok = np.isfinite(vals)
            if len(ref_dist):
                pct[ok] = 100.0 * np.searchsorted(ref_dist, vals[ok], side="right") / len(ref_dist)
            scored["magnetic_reference_support_percentile"] = pct
        return scored
