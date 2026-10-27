from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

REFERENCE_CLASSES = ["MAGNDATA", "AFM", "FM", "FiM", "NM"]
MAGNETIC_CLASSES = ["MAGNDATA", "AFM", "FM", "FiM"]

DFT_MODEL_DATASET_ALIASES = {
    "mattergen": "mattergen_base",
    "concdvae": "concdvae_base",
    "crystalformer": "crystalformer",
    "crystalllm": "crystalllm",
}



def canon_label(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    if s.lower() == "fim":
        return "FiM"
    u = s.upper()
    if u in {"MAGNDATA", "AFM", "FM", "NM"}:
        return u
    return s


def load_config(path: str | Path) -> dict:
    path = Path(path).resolve()
    cfg = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    for key in ["pipeline_root", "analysis_root", "manifest", "output_dir", "figure1_concept"]:
        if cfg.get(key):
            p = Path(cfg[key])
            cfg[key] = str((base / p).resolve()) if not p.is_absolute() else str(p.resolve())
    dft = cfg.get("dft", {})
    for key in ["fm_init", "afm_fm"]:
        if dft.get(key):
            p = Path(dft[key])
            dft[key] = str((base / p).resolve()) if not p.is_absolute() else str(p.resolve())
    cfg["dft"] = dft
    return cfg


def first_existing(*paths: Path) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None


def load_pipeline_outputs(root: str | Path, analysis_root: str | Path | None = None) -> dict[str, object]:
    """Load canonical extraction plus the final post-extraction reference model when available.

    `root` is the expensive CIF-extraction output. `analysis_root`, when provided,
    should be analysis_v0_6 (or equivalent) containing main/query_scores.csv,
    main/reference_validation_scores.csv and main/feature_manifest.csv. This lets
    article figures use the final 45-feature metric without re-running CIF extraction.
    """
    root = Path(root)
    analysis_root = Path(analysis_root) if analysis_root else None
    main_root = analysis_root / "main" if analysis_root else None

    features_path = first_existing(
        root / "features" / "structure_features.csv",
        root / "structure_features.csv",
    )
    if features_path is None:
        raise FileNotFoundError("Could not find features/structure_features.csv")

    query_path = first_existing(
        *( [main_root / "query_scores.csv"] if main_root else [] ),
        root / "scores" / "query_scores.csv",
        root / "query_scores.csv",
    )
    ref_validation_path = first_existing(
        *( [main_root / "reference_validation_scores.csv"] if main_root else [] ),
        root / "model" / "reference_validation_scores.csv",
        root / "reference_validation_scores.csv",
    )
    scores_path = first_existing(
        root / "scores" / "all_scores.csv",
        root / "all_scores.csv",
        root / "article_reference_distances_per_structure_v5.csv",
    )

    model_npz = first_existing(root / "model" / "reference_filter.npz", root / "reference_filter.npz")
    model_json = first_existing(root / "model" / "reference_filter.json", root / "reference_filter.json")
    scaling_manifest = first_existing(
        *( [main_root / "feature_manifest.csv"] if main_root else [] ),
        root / "model" / "feature_manifest.csv",
        root / "feature_manifest.csv",
    )

    features = pd.read_csv(features_path, low_memory=False)
    for c in ["dataset", "structure_id"]:
        if c in features:
            features[c] = features[c].astype(str)
    if "dataset" in features:
        features["dataset"] = features["dataset"].str.lower()
    if "label_order" in features:
        features["label_order"] = features["label_order"].map(canon_label)

    query = pd.read_csv(query_path, low_memory=False) if query_path is not None else pd.DataFrame()
    ref_validation = pd.read_csv(ref_validation_path, low_memory=False) if ref_validation_path is not None else pd.DataFrame()
    for df in [query, ref_validation]:
        if "dataset" in df:
            df["dataset"] = df["dataset"].astype(str).str.lower()
        if "structure_id" in df:
            df["structure_id"] = df["structure_id"].astype(str)
        if "label_order" in df:
            df["label_order"] = df["label_order"].map(canon_label)

    if scores_path is not None:
        scores = pd.read_csv(scores_path, low_memory=False)
        if "dataset" in scores:
            scores["dataset"] = scores["dataset"].astype(str).str.lower()
        if "structure_id" in scores:
            scores["structure_id"] = scores["structure_id"].astype(str)
        if "label_order" in scores:
            scores["label_order"] = scores["label_order"].map(canon_label)
    else:
        parts = []
        if len(ref_validation):
            x = ref_validation.copy()
            if "role" not in x:
                x["role"] = "reference"
            parts.append(x)
        if len(query):
            x = query.copy()
            if "role" not in x:
                x["role"] = "query"
            parts.append(x)
        scores = pd.concat(parts, ignore_index=True, sort=False) if parts else pd.DataFrame()

    if query.empty and len(scores):
        if "role" in scores:
            query = scores[~scores["role"].astype(str).eq("reference")].copy()
        else:
            query = scores[~scores.get("label_order", pd.Series(np.nan, index=scores.index)).isin(REFERENCE_CLASSES)].copy()
    if ref_validation.empty and len(scores):
        if "role" in scores:
            ref_validation = scores[scores["role"].astype(str).eq("reference")].copy()
        else:
            ref_validation = scores[scores.get("label_order", pd.Series(np.nan, index=scores.index)).isin(REFERENCE_CLASSES)].copy()

    return {
        "root": root,
        "analysis_root": analysis_root,
        "main_root": main_root,
        "features": features,
        "scores": scores,
        "query": query,
        "reference_validation": ref_validation,
        "model_npz": model_npz,
        "model_json": model_json,
        "scaling_manifest": scaling_manifest,
        "analysis_tables_dir": analysis_root / "tables" if analysis_root else None,
    }


def transformed_feature_space(bundle: dict[str, object], clip_z: float | None = None) -> tuple[pd.DataFrame, np.ndarray, list[str]]:
    """Return the canonical final metric space used for article embeddings.

    Prefer analysis_v0_6/main/feature_manifest.csv (feature, center, scale), which
    reflects near-constant filtering. Fall back to the legacy NPZ model.
    """
    features = bundle["features"].copy()
    manifest_path = bundle.get("scaling_manifest")
    model_npz = bundle.get("model_npz")
    model_json = bundle.get("model_json")

    if manifest_path is not None and Path(manifest_path).exists():
        fm = pd.read_csv(manifest_path)
        required = {"feature", "center", "scale"}
        if not required.issubset(fm.columns):
            raise ValueError(f"{manifest_path} must contain {sorted(required)}")
        feature_names = fm["feature"].astype(str).tolist()
        center = pd.to_numeric(fm["center"], errors="coerce").to_numpy(float)
        scale = pd.to_numeric(fm["scale"], errors="coerce").to_numpy(float)
    elif model_npz is not None:
        z = np.load(model_npz, allow_pickle=False)
        feature_names = z["feature_names"].astype(str).tolist()
        center = z["center"].astype(float)
        scale = z["scale"].astype(float)
    else:
        raise FileNotFoundError("Need final feature_manifest.csv or reference_filter.npz to rebuild the metric space")

    if clip_z is None:
        clip_z = 8.0
        if model_json is not None:
            try:
                meta = json.loads(Path(model_json).read_text(encoding="utf-8"))
                clip_z = float(meta.get("clip_z", clip_z))
            except Exception:
                pass

    missing = [c for c in feature_names if c not in features.columns]
    if missing:
        raise ValueError(f"Feature table is missing {len(missing)} model features; first: {missing[:5]}")

    valid = pd.Series(True, index=features.index)
    if "parse_success" in features:
        valid &= pd.to_numeric(features["parse_success"], errors="coerce").fillna(0).astype(int).eq(1)
    f = features.loc[valid].copy().reset_index(drop=True)
    X = f[feature_names].apply(pd.to_numeric, errors="coerce").astype(float).replace([np.inf, -np.inf], np.nan)
    X = X.fillna(pd.Series(center, index=feature_names)).fillna(0.0)
    safe_scale = np.where(np.isfinite(scale) & (np.abs(scale) > 0), scale, 1.0)
    Z = (X.to_numpy(float) - center) / safe_scale
    if clip_z and clip_z > 0:
        Z = np.clip(Z, -clip_z, clip_z)
    return f, Z, feature_names


def compute_embeddings(bundle: dict[str, object], cfg: dict) -> dict[str, pd.DataFrame]:
    ecfg = cfg.get("embedding", {})
    f, Z, feature_names = transformed_feature_space(bundle, ecfg.get("clip_z"))
    meta_cols = [c for c in ["dataset", "structure_id", "formula_reduced", "label_order", "role"] if c in f.columns]
    base = f[meta_cols].copy()
    if "role" not in base:
        base["role"] = np.where(base.get("label_order", pd.Series(np.nan, index=base.index)).isin(REFERENCE_CLASSES), "reference", "query")

    out: dict[str, pd.DataFrame] = {}
    pca = PCA(n_components=2, random_state=int(ecfg.get("random_state", 42)))
    P = pca.fit_transform(Z)
    p = base.copy()
    p["x"] = P[:, 0]
    p["y"] = P[:, 1]
    p["explained_variance_x"] = float(pca.explained_variance_ratio_[0])
    p["explained_variance_y"] = float(pca.explained_variance_ratio_[1])
    out["pca"] = p

    if bool(ecfg.get("umap", True)):
        try:
            import umap
            reducer = umap.UMAP(
                n_components=2,
                n_neighbors=int(ecfg.get("umap_n_neighbors", 30)),
                min_dist=float(ecfg.get("umap_min_dist", 0.15)),
                metric="euclidean",
                random_state=int(ecfg.get("random_state", 42)),
            )
            U = reducer.fit_transform(Z)
            u = base.copy()
            u["x"], u["y"] = U[:, 0], U[:, 1]
            out["umap"] = u
        except Exception as exc:
            out["umap_error"] = pd.DataFrame({"error": [str(exc)]})

    if bool(ecfg.get("tsne", True)):
        max_points = int(ecfg.get("tsne_max_points", 12000))
        rng = np.random.default_rng(int(ecfg.get("random_state", 42)))
        if len(f) > max_points:
            idx = stratified_sample_indices(base, max_points, rng)
            Zt = Z[idx]
            bt = base.iloc[idx].reset_index(drop=True)
        else:
            Zt = Z
            bt = base.reset_index(drop=True)
        perplexity = min(float(ecfg.get("tsne_perplexity", 35)), max(5.0, (len(Zt) - 1) / 3.0))
        T = TSNE(
            n_components=2,
            perplexity=perplexity,
            init="pca",
            learning_rate="auto",
            max_iter=int(ecfg.get("tsne_iterations", 1000)),
            random_state=int(ecfg.get("random_state", 42)),
        ).fit_transform(Zt)
        t = bt.copy()
        t["x"], t["y"] = T[:, 0], T[:, 1]
        out["tsne"] = t

    out["feature_manifest"] = pd.DataFrame({"feature": feature_names})
    return out


def stratified_sample_indices(meta: pd.DataFrame, n: int, rng: np.random.Generator) -> np.ndarray:
    key = meta.get("dataset", pd.Series("all", index=meta.index)).astype(str)
    groups = {k: g.index.to_numpy() for k, g in meta.groupby(key)}
    total = len(meta)
    chosen = []
    for _, idx in groups.items():
        take = max(1, int(round(n * len(idx) / total)))
        take = min(take, len(idx))
        chosen.extend(rng.choice(idx, size=take, replace=False).tolist())
    if len(chosen) > n:
        chosen = rng.choice(np.asarray(chosen), size=n, replace=False).tolist()
    elif len(chosen) < n:
        rest = np.setdiff1d(np.arange(total), np.asarray(chosen, dtype=int))
        if len(rest):
            add = rng.choice(rest, size=min(n - len(chosen), len(rest)), replace=False)
            chosen.extend(add.tolist())
    return np.asarray(sorted(chosen), dtype=int)


def known_label_validation(ref: pd.DataFrame) -> dict[str, pd.DataFrame]:
    d = ref.copy()
    d["label_order"] = d["label_order"].map(canon_label)
    d = d[d["label_order"].isin(REFERENCE_CLASSES)].copy()
    if "nearest_reference_branch" not in d:
        raise ValueError("reference_validation_scores.csv lacks nearest_reference_branch")
    d["nearest_reference_branch"] = d["nearest_reference_branch"].map(canon_label)
    confusion_counts = pd.crosstab(d["label_order"], d["nearest_reference_branch"]).reindex(index=REFERENCE_CLASSES, columns=REFERENCE_CLASSES, fill_value=0)
    confusion_fraction = confusion_counts.div(confusion_counts.sum(axis=1).replace(0, np.nan), axis=0)

    rows = []
    for lab in REFERENCE_CLASSES:
        g = d[d["label_order"].eq(lab)]
        rows.append({
            "label": lab,
            "n": len(g),
            "nearest_reference_agreement": float(g["nearest_reference_branch"].eq(lab).mean()) if len(g) else np.nan,
            "fraction_assigned_NM": float(g["nearest_reference_branch"].eq("NM").mean()) if len(g) else np.nan,
        })
    classwise = pd.DataFrame(rows)

    magnetic = d[d["label_order"].isin(MAGNETIC_CLASSES)].copy()
    if "nearest_magnetic_reference_branch" in magnetic:
        magnetic["nearest_magnetic_reference_branch"] = magnetic["nearest_magnetic_reference_branch"].map(canon_label)
        mag_counts = pd.crosstab(magnetic["label_order"], magnetic["nearest_magnetic_reference_branch"]).reindex(index=MAGNETIC_CLASSES, columns=MAGNETIC_CLASSES, fill_value=0)
        mag_fraction = mag_counts.div(mag_counts.sum(axis=1).replace(0, np.nan), axis=0)
    else:
        mag_counts = pd.DataFrame()
        mag_fraction = pd.DataFrame()

    true_mag = d["label_order"].isin(MAGNETIC_CLASSES)
    pred_mag_nearest = ~d["nearest_reference_branch"].eq("NM")
    binary = binary_metrics(true_mag, pred_mag_nearest, name="nearest_reference_nonNM")
    binary_df = pd.DataFrame([binary])


    exact = float(d["nearest_reference_branch"].eq(d["label_order"]).mean()) if len(d) else np.nan
    summary = pd.DataFrame([
        {"metric":"exact_five_branch_agreement", "value": exact},
        {"metric":"magnetic_reference_sensitivity", "value": float(binary.get("recall", np.nan))},
        {"metric":"NM_specificity", "value": float(binary.get("specificity", np.nan))},
        {"metric":"binary_balanced_accuracy", "value": float(binary.get("balanced_accuracy", np.nan))},
    ])

    return {
        "confusion_counts": confusion_counts,
        "confusion_fraction": confusion_fraction,
        "classwise": classwise,
        "magnetic_confusion_counts": mag_counts,
        "magnetic_confusion_fraction": mag_fraction,
        "binary_metrics": binary_df,
        "summary": summary,
    }


def binary_metrics(y_true, y_pred, name: str = "criterion") -> dict[str, float | int | str]:
    yt = np.asarray(y_true, dtype=bool)
    yp = np.asarray(y_pred, dtype=bool)
    tp = int(np.sum(yt & yp)); fp = int(np.sum(~yt & yp)); tn = int(np.sum(~yt & ~yp)); fn = int(np.sum(yt & ~yp))
    precision = tp / (tp + fp) if tp + fp else np.nan
    recall = tp / (tp + fn) if tp + fn else np.nan
    specificity = tn / (tn + fp) if tn + fp else np.nan
    npv = tn / (tn + fn) if tn + fn else np.nan
    accuracy = (tp + tn) / len(yt) if len(yt) else np.nan
    f1 = 2 * precision * recall / (precision + recall) if np.isfinite(precision) and np.isfinite(recall) and precision + recall else np.nan
    return {
        "criterion": name, "n": len(yt), "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "accuracy": accuracy, "precision": precision, "recall": recall,
        "specificity": specificity, "NPV": npv, "F1": f1,
        "balanced_accuracy": np.nanmean([recall, specificity]),
    }


def generator_metrics(query: pd.DataFrame) -> pd.DataFrame:
    """Dataset-level metrics using all generated rows for validity and scored rows for proximity."""
    q = query.copy()
    rows = []
    for ds, g_all in q.groupby("dataset", dropna=False):
        if "score_status" in g_all:
            good = g_all[g_all["score_status"].astype(str).eq("ok")].copy()
        else:
            good = g_all.copy()
        n_all = len(g_all); n = len(good)
        if "formula_reduced" in good:
            formula = good["formula_reduced"].fillna(good.get("structure_id", pd.Series(index=good.index, dtype=str)).astype(str)).astype(str)
            n_formula = formula.nunique()
        else:
            n_formula = n
        row = {
            "dataset": ds,
            "n_structures": n_all,
            "n_scored": n,
            "parse_success_fraction": n / n_all if n_all else np.nan,
            "n_unique_formulas": n_formula,
            "formula_diversity_fraction": n_formula / n if n else np.nan,
            "fraction_closer_to_magnetic_reference_than_NM": float(pd.to_numeric(good.get("is_closer_to_magnetic_reference_than_NM"), errors="coerce").mean()) if n else np.nan,
            "median_magnetic_reference_vs_NM_contrast": float(pd.to_numeric(good.get("magnetic_reference_vs_NM_contrast"), errors="coerce").median()) if n else np.nan,
            "median_nearest_magnetic_reference_distance": float(pd.to_numeric(good.get("nearest_magnetic_reference_distance"), errors="coerce").median()) if n else np.nan,
            "median_magnetic_reference_support_percentile": float(pd.to_numeric(good.get("magnetic_reference_support_percentile"), errors="coerce").median()) if n and "magnetic_reference_support_percentile" in good else np.nan,
            "median_feature_missing_fraction": float(pd.to_numeric(good.get("feature_missing_fraction"), errors="coerce").median()) if n and "feature_missing_fraction" in good else np.nan,
        }
        if "nearest_magnetic_reference_branch" in good:
            for b in MAGNETIC_CLASSES:
                row[f"fraction_nearest_magnetic_reference_branch_{b}"] = float(good["nearest_magnetic_reference_branch"].map(canon_label).eq(b).mean()) if n else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def bootstrap_generator_metrics(query: pd.DataFrame, n_bootstrap: int = 1000, seed: int = 42) -> pd.DataFrame:
    q = query.copy()
    rng = np.random.default_rng(seed)
    rows = []
    metrics_to_report = [
        "fraction_closer_to_magnetic_reference_than_NM",
        "median_magnetic_reference_vs_NM_contrast",
        "median_nearest_magnetic_reference_distance",
        "median_magnetic_reference_support_percentile",
    ]
    for ds, g_all in q.groupby("dataset", dropna=False):
        g = g_all[g_all["score_status"].astype(str).eq("ok")].copy() if "score_status" in g_all else g_all.copy()
        if not len(g):
            continue
        if "formula_reduced" in g:
            formula = g["formula_reduced"].fillna("__SID__" + g["structure_id"].astype(str)).astype(str)
        else:
            formula = g["structure_id"].astype(str)
        groups = [sub for _, sub in g.groupby(formula, sort=False)]
        point = generator_metrics(g).iloc[0].to_dict()
        boot = {m: [] for m in metrics_to_report}
        for _ in range(n_bootstrap):
            picks = rng.integers(0, len(groups), size=len(groups))
            sample = pd.concat([groups[i] for i in picks], ignore_index=True)
            vals = generator_metrics(sample).iloc[0].to_dict()
            for m in metrics_to_report:
                boot[m].append(vals.get(m, np.nan))
        for m in metrics_to_report:
            arr = np.asarray(boot[m], dtype=float); arr = arr[np.isfinite(arr)]
            rows.append({
                "dataset": ds, "metric": m, "point_estimate": point.get(m, np.nan),
                "bootstrap_mean": float(arr.mean()) if len(arr) else np.nan,
                "ci95_low": float(np.quantile(arr, 0.025)) if len(arr) else np.nan,
                "ci95_high": float(np.quantile(arr, 0.975)) if len(arr) else np.nan,
                "bootstrap_mode": "formula_cluster", "n_bootstrap": n_bootstrap,
            })
    return pd.DataFrame(rows)


def extract_structure_id(model: str, folder: str) -> str | None:
    """Recover the prepared structure_id from historical DFT folder names."""
    model = str(model).lower().strip()
    name = Path(str(folder)).name
    m = re.search(rf"{re.escape(model)}__(.+)$", name, flags=re.I)
    return m.group(1) if m else None


def _dft_dataset_name(model: str) -> str:
    model = str(model).lower().strip()
    return DFT_MODEL_DATASET_ALIASES.get(model, model)


def merge_dft_fm_init(path: str | Path, query_scores: pd.DataFrame) -> pd.DataFrame:
    dft = pd.read_csv(path, low_memory=False)
    dft["dataset"] = dft["model"].map(_dft_dataset_name)
    dft["structure_id"] = [extract_structure_id(m, f) for m, f in zip(dft["model"], dft["folder"])]
    q = query_scores.copy()
    q["dataset"] = q["dataset"].astype(str).str.lower()
    q["structure_id"] = q["structure_id"].astype(str)
    cols = [c for c in ["dataset", "structure_id", "formula_reduced", "nearest_reference_branch", "nearest_magnetic_reference_branch", "magnetic_reference_vs_NM_contrast", "is_closer_to_magnetic_reference_than_NM"] if c in q.columns]
    cols = list(dict.fromkeys(cols))
    merged = dft.merge(q[cols], on=["dataset", "structure_id"], how="left", validate="many_to_one")
    merged["dft_is_magnetic"] = merged["is_magnetic"].astype(str).str.lower().eq("yes")
    merged["dft_join_status"] = np.where(merged["nearest_reference_branch"].notna(), "matched", "unmatched")
    return merged


def wilson_interval(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return np.nan, np.nan
    p = k / n
    den = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * np.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / den
    return max(0.0, center - half), min(1.0, center + half)


def dft_confirmation_by_generator(merged: pd.DataFrame) -> pd.DataFrame:
    """DFT confirmation rate among pipeline-selected magnetic-like candidates."""
    d = merged.copy()
    if "dft_join_status" in d:
        d = d[d["dft_join_status"].eq("matched")].copy()
    if "is_closer_to_magnetic_reference_than_NM" in d:
        pos = pd.to_numeric(d["is_closer_to_magnetic_reference_than_NM"], errors="coerce").fillna(0).astype(int).eq(1)
    else:
        pos = pd.to_numeric(d["magnetic_reference_vs_NM_contrast"], errors="coerce").gt(0)
    d = d[pos].copy()
    rows = []
    for ds, g in d.groupby("dataset", sort=False):
        n = int(len(g)); k = int(g["dft_is_magnetic"].sum())
        lo, hi = wilson_interval(k, n)
        rows.append({
            "dataset": ds,
            "n_dft_pipeline_positive": n,
            "n_dft_confirmed_magnetic": k,
            "dft_confirmation_fraction": k / n if n else np.nan,
            "ci95_low": lo,
            "ci95_high": hi,
        })
    return pd.DataFrame(rows)


def dft_pipeline_class_confirmation(merged: pd.DataFrame) -> pd.DataFrame:
    """Overall DFT magnetic fraction for pipeline magnetic-like and NM-like classes."""
    d = merged.copy()
    if "dft_join_status" in d:
        d = d[d["dft_join_status"].eq("matched")].copy()
    if "is_closer_to_magnetic_reference_than_NM" in d:
        pos = pd.to_numeric(d["is_closer_to_magnetic_reference_than_NM"], errors="coerce").fillna(0).astype(int).eq(1)
    else:
        pos = pd.to_numeric(d["magnetic_reference_vs_NM_contrast"], errors="coerce").gt(0)
    d["pipeline_class"] = np.where(pos, "Pipeline magnetic-like", "Pipeline NM-like")
    rows=[]
    for lab, g in d.groupby("pipeline_class", sort=False):
        n=int(len(g)); k=int(g["dft_is_magnetic"].sum()); lo,hi=wilson_interval(k,n)
        rows.append({"pipeline_class":lab,"n":n,"n_dft_magnetic":k,"dft_magnetic_fraction":k/n if n else np.nan,"ci95_low":lo,"ci95_high":hi})
    return pd.DataFrame(rows)


def dft_binary_validation(merged: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    d = merged[merged["nearest_reference_branch"].notna()].copy()
    criteria: dict[str, pd.Series] = {
        "nearest_reference_nonNM": ~d["nearest_reference_branch"].map(canon_label).eq("NM"),
    }
    if "is_closer_to_magnetic_reference_than_NM" in d:
        criteria["contrast_positive"] = pd.to_numeric(d["is_closer_to_magnetic_reference_than_NM"], errors="coerce").fillna(0).astype(int).eq(1)

    rows = []
    by_gen = []
    for name, pred in criteria.items():
        rows.append(binary_metrics(d["dft_is_magnetic"], pred, name=name))
        for ds, g in d.assign(_pred=pred).groupby("dataset"):
            x = binary_metrics(g["dft_is_magnetic"], g["_pred"], name=name)
            x["dataset"] = ds
            by_gen.append(x)
    overall = pd.DataFrame(rows)
    by_generator = pd.DataFrame(by_gen)

    # Direct pipeline-class composition relative to DFT for the primary magnetic/NM call.
    primary = ~d["nearest_reference_branch"].map(canon_label).eq("NM")
    comp = pd.crosstab(
        np.where(primary, "Pipeline magnetic-like", "Pipeline NM-like"),
        np.where(d["dft_is_magnetic"], "DFT magnetic", "DFT non-magnetic"),
    )
    comp_fraction = comp.div(comp.sum(axis=1).replace(0, np.nan), axis=0)
    comp_fraction.attrs["counts"] = comp
    return overall, by_generator, comp_fraction


def merge_dft_afm(path: str | Path, query_scores: pd.DataFrame, fm_merged: pd.DataFrame | None = None) -> pd.DataFrame:
    dft = pd.read_csv(path, low_memory=False)
    dft["dataset"] = dft["model"].map(_dft_dataset_name)
    dft["structure_id"] = [extract_structure_id(m, f) for m, f in zip(dft["model"], dft["folder"])]
    q = query_scores.copy()
    q["dataset"] = q["dataset"].astype(str).str.lower()
    q["structure_id"] = q["structure_id"].astype(str)
    cols = [c for c in ["dataset", "structure_id", "formula_reduced", "nearest_reference_branch", "nearest_magnetic_reference_branch", "magnetic_reference_vs_NM_contrast"] if c in q.columns]
    merged = dft.merge(q[list(dict.fromkeys(cols))], on=["dataset", "structure_id"], how="left", validate="many_to_one")
    if fm_merged is not None:
        extra = [c for c in ["dataset", "structure_id", "pred_ordering", "mag_type_FM_init", "is_magnetic"] if c in fm_merged.columns]
        merged = merged.merge(fm_merged[extra].drop_duplicates(["dataset", "structure_id"]), on=["dataset", "structure_id"], how="left")
    return merged


def afm_groundstate_summary(merged: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ds, g in merged.groupby("dataset"):
        n = len(g)
        rows.append({
            "dataset": ds,
            "n": n,
            "AFM_count": int(g["ground_state"].astype(str).eq("AFM").sum()),
            "FM_count": int(g["ground_state"].astype(str).eq("FM").sum()),
            "degenerate_count": int(g["ground_state"].astype(str).str.lower().eq("degenerate").sum()),
            "AFM_fraction": float(g["ground_state"].astype(str).eq("AFM").mean()) if n else np.nan,
            "median_dE_AFM_minus_FM_meV_atom": float(pd.to_numeric(g["dE_per_atom_meV"], errors="coerce").median()) if n else np.nan,
        })
    return pd.DataFrame(rows)

def load_precomputed_analysis_tables(bundle: dict[str, object]) -> dict[str, pd.DataFrame]:
    """Load robustness/conditioning tables produced by the post-extraction analysis layer."""
    td = bundle.get("analysis_tables_dir")
    if td is None:
        return {}
    td = Path(td)
    names = [
        "variant_comparison", "generator_benchmark_with_ci", "missingness_sensitivity",
        "mattergen_by_mgd", "mattergen_by_seed", "concdvae_by_condition",
        "crystalformer_by_series_seed", "crystalllm_by_target_formula",
        "base_vs_tuned_shifts", "query_scores_with_provenance",
    ]
    out = {}
    for name in names:
        p = td / f"{name}.csv"
        if p.exists():
            out[name] = pd.read_csv(p, low_memory=False)
    return out


def normalize_formula(x) -> str:
    if pd.isna(x):
        return ""
    s = str(x).strip()
    if not s:
        return ""
    try:
        from pymatgen.core import Composition
        return Composition(s).reduced_formula
    except Exception:
        return "".join(s.split())


def _shannon_entropy(values) -> float:
    s = pd.Series(values, dtype="object").dropna()
    if not len(s):
        return np.nan
    p = s.value_counts(normalize=True).to_numpy(float)
    return float(-(p * np.log(p)).sum())


def _median_pairwise_distance(X: np.ndarray) -> tuple[float, float, float]:
    if len(X) < 2:
        return np.nan, np.nan, np.nan
    vals = []
    for i in range(len(X) - 1):
        vals.extend(np.sqrt(np.sum((X[i+1:] - X[i])**2, axis=1)).tolist())
    a = np.asarray(vals, dtype=float)
    return float(np.median(a)), float(np.quantile(a, .25)), float(np.quantile(a, .75))


def crystalllm_target_metrics(bundle: dict[str, object], manifest_path: str | Path, clip_z: float = 8.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Target-aware CrystALLM metrics.

    Replaces cross-model formula diversity with target fidelity and within-target
    diversity in the canonical final descriptor space. No CIFs are re-read.
    """
    manifest = pd.read_csv(manifest_path, low_memory=False)
    manifest["dataset"] = manifest["dataset"].astype(str).str.lower()
    manifest["structure_id"] = manifest["structure_id"].astype(str)
    qscore = bundle["query"].copy()
    qscore["dataset"] = qscore["dataset"].astype(str).str.lower()
    qscore["structure_id"] = qscore["structure_id"].astype(str)
    feat_meta, Z, feature_names = transformed_feature_space(bundle, clip_z)
    feat_meta["dataset"] = feat_meta["dataset"].astype(str).str.lower()
    feat_meta["structure_id"] = feat_meta["structure_id"].astype(str)
    # Row lookup into transformed feature matrix.
    lookup = {(d, s): i for i, (d, s) in enumerate(zip(feat_meta["dataset"], feat_meta["structure_id"]))}

    keep = [c for c in ["dataset","structure_id","target_formula","sha256"] if c in manifest.columns]
    m = manifest.loc[manifest["dataset"].eq("crystalllm"), keep].drop_duplicates(["dataset","structure_id"])
    cols = [c for c in ["dataset","structure_id","formula_reduced","score_status"] if c in qscore.columns]
    q = m.merge(qscore[cols], on=["dataset","structure_id"], how="left", validate="one_to_one")
    q["target_formula_norm"] = q["target_formula"].map(normalize_formula)
    q["generated_formula_norm"] = q["formula_reduced"].map(normalize_formula)
    q["scored"] = q["score_status"].astype(str).eq("ok") if "score_status" in q else q["formula_reduced"].notna()
    q["target_adherent"] = q["scored"] & q["target_formula_norm"].ne("") & q["generated_formula_norm"].eq(q["target_formula_norm"])
    q["_zrow"] = [lookup.get((d,s), -1) for d,s in zip(q["dataset"],q["structure_id"])]

    rows=[]
    for target, g in q.groupby("target_formula", dropna=False, sort=True):
        gs=g[g["scored"]]; ga=g[g["target_adherent"] & g["_zrow"].ge(0)]
        idx=ga["_zrow"].to_numpy(int)
        med,q25,q75=_median_pairwise_distance(Z[idx]) if len(idx)>=2 else (np.nan,np.nan,np.nan)
        off=gs.loc[~gs["target_adherent"],"generated_formula_norm"]
        rows.append({
            "dataset":"crystalllm", "target_formula":target,
            "n_structures":len(g), "n_scored":len(gs),
            "validity_fraction":len(gs)/len(g) if len(g) else np.nan,
            "n_target_adherent":int(g["target_adherent"].sum()),
            "target_adherence_among_scored":float(g.loc[g["scored"],"target_adherent"].mean()) if len(gs) else np.nan,
            "target_adherence_all_generated":float(g["target_adherent"].mean()) if len(g) else np.nan,
            "n_off_target_scored":int((gs["target_adherent"]==False).sum()),
            "n_unique_off_target_formulas":int(off.nunique()) if len(off) else 0,
            "off_target_formula_entropy":_shannon_entropy(off),
            "within_target_descriptor_pairwise_distance_median":med,
            "within_target_descriptor_pairwise_distance_q25":q25,
            "within_target_descriptor_pairwise_distance_q75":q75,
            "n_unique_cif_sha256_scored":int(gs["sha256"].nunique()) if "sha256" in gs else np.nan,
        })
    detail=pd.DataFrame(rows)
    global_df=pd.DataFrame([{
        "n_structures":int(len(q)), "n_scored":int(q["scored"].sum()),
        "validity_fraction":float(q["scored"].mean()),
        "target_adherence_among_scored":float(q.loc[q["scored"],"target_adherent"].mean()) if q["scored"].any() else np.nan,
        "target_adherence_all_generated":float(q["target_adherent"].mean()),
        "median_within_target_descriptor_pairwise_distance":float(detail["within_target_descriptor_pairwise_distance_median"].median()),
        "n_targets":int(detail["target_formula"].nunique()),
    }])
    return detail, global_df
