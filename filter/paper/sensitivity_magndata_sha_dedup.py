from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from cifmagfilter.core import (
    numeric_feature_columns,
    robust_fit,
    robust_transform,
    reference_scores,
    reference_scores_training,
)

REF_CLASSES = ["MAGNDATA", "AFM", "FM", "FiM", "NM"]
MAG_CLASSES = ["MAGNDATA", "AFM", "FM", "FiM"]


def deduplicate_magndata_by_sha(reference_df: pd.DataFrame) -> pd.DataFrame:
    """Retain one deterministic MAGNDATA row per exact SHA256; leave all other branches unchanged."""
    if "sha256" not in reference_df.columns:
        raise ValueError("reference_df requires a sha256 column")
    mag = reference_df[reference_df["label_order"].eq("MAGNDATA")].copy()
    other = reference_df[~reference_df["label_order"].eq("MAGNDATA")].copy()
    mag = mag.sort_values(["sha256", "structure_id"]).drop_duplicates("sha256", keep="first")
    return pd.concat([mag, other], ignore_index=True).sort_values(
        ["label_order", "dataset", "structure_id"]
    ).reset_index(drop=True)


def fit_and_score(ref: pd.DataFrame, query: pd.DataFrame, k: int, clip_z: float,
                  min_coverage: float, near_constant_tol: float):
    features = numeric_feature_columns(
        ref, min_coverage=min_coverage, feature_set="main", near_constant_tol=near_constant_tol
    )
    mask = np.ones(len(ref), dtype=bool)
    Zr, center, scale, miss_r = robust_fit(ref, features, mask, clip_z=clip_z)
    meta_cols = ["dataset", "structure_id", "source_path", "formula_reduced", "label_order", "role", "sha256"]
    rmeta = ref[[c for c in meta_cols if c in ref.columns]].copy()
    rscore = reference_scores_training(rmeta, Zr, ref["label_order"], REF_CLASSES, MAG_CLASSES, k)
    rscore["feature_missing_fraction"] = miss_r

    Zq, miss_q = robust_transform(query, features, center, scale, clip_z=clip_z)
    pools = {lab: Zr[ref["label_order"].eq(lab).to_numpy(bool)] for lab in REF_CLASSES}
    qmeta = query[[c for c in meta_cols if c in query.columns]].copy()
    qscore = reference_scores(qmeta, Zq, pools, MAG_CLASSES, k)
    qscore["feature_missing_fraction"] = miss_q
    return pd.DataFrame({"feature": features, "center": center, "scale": scale}), rscore, qscore


def validation_metrics(scores: pd.DataFrame) -> dict[str, float]:
    y = scores["label_order"].astype(str)
    p = scores["nearest_reference_branch"].astype(str)
    magnetic = y.ne("NM")
    pred_magnetic = p.ne("NM")
    return {
        "five_branch_agreement": float(y.eq(p).mean()),
        "magnetic_sensitivity": float(pred_magnetic[magnetic].mean()),
        "nm_specificity": float((~pred_magnetic[~magnetic]).mean()),
        "binary_balanced_accuracy": float((pred_magnetic[magnetic].mean() + (~pred_magnetic[~magnetic]).mean()) / 2),
        **{f"same_branch_{lab}": float(p[y.eq(lab)].eq(lab).mean()) for lab in REF_CLASSES},
    }


def nm_thresholds(scores: pd.DataFrame) -> dict[str, float]:
    x = scores.loc[scores["label_order"].eq("NM"), "magnetic_reference_vs_NM_contrast"].dropna()
    return {f"NM{int(100*q)}": float(x.quantile(q)) for q in (0.95, 0.98, 0.99)}


def generator_summary(scores: pd.DataFrame, thresholds: dict[str, float]) -> pd.DataFrame:
    rows = []
    for ds, g in scores.groupby("dataset", sort=True):
        c = g["magnetic_reference_vs_NM_contrast"]
        row = {
            "dataset": ds,
            "n": len(g),
            "fmag": float(c.gt(0).mean()),
            "median_contrast": float(c.median()),
            "median_dmag": float(g["nearest_magnetic_reference_distance"].median()),
        }
        row.update({f"yield_{name}": float(c.gt(v).mean()) for name, v in thresholds.items()})
        rows.append(row)
    return pd.DataFrame(rows)


def plot_sensitivity(manifest: pd.DataFrame, validation: pd.DataFrame, gen: pd.DataFrame,
                     paired: pd.DataFrame, out: Path):
    counts = manifest.loc[manifest["dataset"].eq("magndata")].groupby("sha256").size().value_counts().sort_index()
    fig, axs = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)

    ax = axs[0, 0]
    x = np.arange(len(counts))
    ax.bar(x, counts.values)
    ax.set_xticks(x, [f"{int(v)}×" for v in counts.index])
    ax.set_xlabel("Exact-CIF multiplicity in MAGNDATA")
    ax.set_ylabel("Number of unique SHA256 groups")
    ax.set_title("A  Exact-SHA duplicate audit", loc="left", fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)

    ax = axs[0, 1]
    metrics = ["five_branch_agreement", "magnetic_sensitivity", "nm_specificity", "binary_balanced_accuracy"]
    labels = ["Five-branch\nagreement", "Magnetic\nsensitivity", "NM\nspecificity", "Balanced\naccuracy"]
    v = validation.set_index("metric")
    a = v.loc[metrics, "default"].to_numpy(); b = v.loc[metrics, "sha_deduplicated"].to_numpy()
    xx = np.arange(len(metrics)); w = 0.34
    ax.bar(xx-w/2, a, w, label="Default"); ax.bar(xx+w/2, b, w, label="MAGNDATA SHA-dedup")
    ax.set_xticks(xx, labels); ax.set_ylim(0.70, 1.00); ax.set_ylabel("Fraction")
    ax.set_title("B  Reference validation", loc="left", fontweight="bold"); ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)

    ax = axs[1, 0]
    order = ["mattergen_base", "mattergen_finetuned", "concdvae_base", "concdvae_finetuned",
             "crysjepa_base", "crysjepa_refined", "crystalformer", "crystalllm"]
    g = gen.set_index("dataset").reindex(order).dropna(subset=["delta_fmag"])
    y = np.arange(len(g)); d = g["delta_fmag"].to_numpy()
    ax.barh(y, d); ax.axvline(0, lw=0.8)
    ax.set_yticks(y, g.index.str.replace("_", " ")); ax.invert_yaxis()
    ax.set_xlabel("Δ magnetic-like fraction (dedup − main)")
    ax.set_title("C  Generator enrichment sensitivity", loc="left", fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)

    ax = axs[1, 1]
    xm = paired["magnetic_reference_vs_NM_contrast_main"].to_numpy(float)
    yd = paired["magnetic_reference_vs_NM_contrast_dedup"].to_numpy(float)
    ax.scatter(xm, yd, s=4, alpha=0.12, rasterized=True)
    lo = min(np.nanmin(xm), np.nanmin(yd)); hi = max(np.nanmax(xm), np.nanmax(yd))
    ax.plot([lo, hi], [lo, hi], "--", lw=1)
    ax.set_xlabel("Default contrast"); ax.set_ylabel("SHA-dedup contrast")
    ax.set_title("D  Paired generator contrast", loc="left", fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle("MAGNDATA exact-SHA deduplication sensitivity — canonical reference filter", fontweight="bold")
    fig.savefig(out / "FigureS_MAGNDATA_SHA_dedup_sensitivity.png", dpi=600, bbox_inches="tight")
    fig.savefig(out / "FigureS_MAGNDATA_SHA_dedup_sensitivity.pdf", bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="Exact-SHA MAGNDATA deduplication sensitivity; no CIF extraction.")
    ap.add_argument("--features", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--knn-k", type=int, default=15)
    ap.add_argument("--clip-z", type=float, default=8.0)
    ap.add_argument("--min-feature-coverage", type=float, default=0.20)
    ap.add_argument("--near-constant-tol", type=float, default=1e-8)
    args = ap.parse_args()

    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    features = pd.read_csv(args.features, low_memory=False)
    manifest = pd.read_csv(args.manifest, low_memory=False)
    for d in (features, manifest):
        d["dataset"] = d["dataset"].astype(str).str.lower()
        d["structure_id"] = d["structure_id"].astype(str)
    prov = manifest[["dataset", "structure_id", "sha256"]].drop_duplicates()
    data = features.merge(prov, on=["dataset", "structure_id"], how="left", validate="one_to_one")
    data = data[pd.to_numeric(data["parse_success"], errors="coerce").eq(1)].copy()
    ref = data[data["role"].astype(str).eq("reference")].copy()
    query = data[data["role"].astype(str).eq("query")].copy()
    dedup = deduplicate_magndata_by_sha(ref)

    fm_main, rs_main, qs_main = fit_and_score(ref, query, args.knn_k, args.clip_z, args.min_feature_coverage, args.near_constant_tol)
    fm_dedup, rs_dedup, qs_dedup = fit_and_score(dedup, query, args.knn_k, args.clip_z, args.min_feature_coverage, args.near_constant_tol)
    if fm_main["feature"].tolist() != fm_dedup["feature"].tolist():
        raise RuntimeError("Deduplication changed the selected feature list; inspect before interpreting sensitivity.")

    fm_main.to_csv(out/"default_feature_manifest.csv", index=False)
    fm_dedup.to_csv(out/"sha_deduplicated_feature_manifest.csv", index=False)
    rs_dedup.to_csv(out/"sha_deduplicated_reference_scores.csv", index=False)
    qs_dedup.to_csv(out/"sha_deduplicated_query_scores.csv", index=False)

    vm = validation_metrics(rs_main); vd = validation_metrics(rs_dedup)
    val = pd.DataFrame([{"metric": k, "default": vm[k], "sha_deduplicated": vd[k], "delta": vd[k]-vm[k]} for k in vm])
    val.to_csv(out/"reference_validation_sensitivity.csv", index=False)

    tm, td = nm_thresholds(rs_main), nm_thresholds(rs_dedup)
    pd.DataFrame([{"threshold": k, "default": tm[k], "sha_deduplicated": td[k], "delta": td[k]-tm[k]} for k in tm]).to_csv(out/"nm_threshold_sensitivity.csv", index=False)

    gm, gd = generator_summary(qs_main, tm), generator_summary(qs_dedup, td)
    gen = gm.merge(gd, on="dataset", suffixes=("_main", "_dedup"), validate="one_to_one")
    for c in ["fmag", "median_contrast", "median_dmag", "yield_NM95", "yield_NM98", "yield_NM99"]:
        gen[f"delta_{c}"] = gen[f"{c}_dedup"] - gen[f"{c}_main"]
    gen.to_csv(out/"generator_benchmark_sensitivity.csv", index=False)

    paired = qs_main[["dataset", "structure_id", "magnetic_reference_vs_NM_contrast", "is_closer_to_magnetic_reference_than_NM"]].merge(
        qs_dedup[["dataset", "structure_id", "magnetic_reference_vs_NM_contrast", "is_closer_to_magnetic_reference_than_NM"]],
        on=["dataset", "structure_id"], suffixes=("_main", "_dedup"), validate="one_to_one")
    paired["binary_same"] = paired["is_closer_to_magnetic_reference_than_NM_main"].eq(paired["is_closer_to_magnetic_reference_than_NM_dedup"])
    paired.to_csv(out/"paired_query_score_sensitivity.csv", index=False)

    mm = manifest[manifest["dataset"].eq("magndata")]
    counts = mm.groupby("sha256").size()
    audit = pd.DataFrame([{
        "magndata_manifest_rows": len(mm),
        "unique_sha256": mm["sha256"].nunique(),
        "duplicate_sha_groups": int(counts.gt(1).sum()),
        "extra_duplicate_rows": int(len(mm)-mm["sha256"].nunique()),
        "cross_dataset_sha_overlaps": int(manifest.groupby("sha256")["dataset"].nunique().reindex(mm["sha256"].unique()).fillna(1).gt(1).sum()),
        "binary_agreement_all_queries": float(paired["binary_same"].mean()),
        "spearman_contrast_all_queries": float(paired[["magnetic_reference_vs_NM_contrast_main", "magnetic_reference_vs_NM_contrast_dedup"]].corr(method="spearman").iloc[0,1]),
    }])
    audit.to_csv(out/"magndata_sha_dedup_summary.csv", index=False)
    plot_sensitivity(manifest, val.rename(columns={"delta":"delta_dedup_minus_main"}), gen, paired, out)
    print(audit.to_string(index=False))


if __name__ == "__main__":
    main()
