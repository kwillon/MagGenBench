#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

import numpy as np # type: ignore
import pandas as pd # type: ignore
import matplotlib.pyplot as plt # type: ignore


PROJECT_ROOT = Path(
    "/mnt/tank/scratch/kkapranova/MagGenBench/"
    "MagGenBench"
)

MODEL_CSVS = {
    "Con-CDVAE": PROJECT_ROOT / "outputs/concdvae/all_structures.csv",
    "CrystalFormer": PROJECT_ROOT / "outputs/crystalformer/all_structures.csv",
    "CrystaLLM": PROJECT_ROOT / "outputs/crystallm/all_structures.csv",
    "MatterGen": PROJECT_ROOT / "outputs/mattergen/all_structures.csv",
}

OUTDIR = PROJECT_ROOT / "reproduced" / "exploratory" / "model_stats"
OUTDIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "font.size": 11,
    "axes.titlesize": 16,
    "axes.labelsize": 12,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "legend.fontsize": 10,
    "axes.linewidth": 0.8,
})

COLORS = {
    "validated": "#4C78A8",
    "rejected": "#B9BDC5",
    "validity": "#4C78A8",
    "magnetic": "#F58518",
    "novelty": "#54A24B",
    "duplicate": "#E45756",
    "density": "#72B7B2",
    "volume": "#B279A2",
}

REASON_COLORS = {
    "charge_imbalance": "#4C78A8",
    "duplicate": "#E45756",
    "physically_impossible_distance": "#F2CF5B",
    "overlap": "#F2CF5B",
    "cif_parse_error": "#B279A2",
    "unrealistic_density": "#72B7B2",
    "density_out_of_range": "#72B7B2",
    "volume_out_of_range": "#B279A2",
    "too_many_atoms": "#BAB0AC",
}


def to_bool_series(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.fillna(False)
    return s.astype(str).str.strip().str.lower().isin(["true", "1", "yes", "y", "t"])


def ensure_column(df: pd.DataFrame, col: str, default=None) -> pd.Series:
    if col in df.columns:
        return df[col]
    return pd.Series([default] * len(df), index=df.index)


def compute_metrics_from_all_structures(model: str, csv_path: Path) -> Dict[str, Any]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing all_structures.csv for {model}: {csv_path}")

    df = pd.read_csv(csv_path)

    if "status" not in df.columns:
        raise ValueError(f"{csv_path} has no required column: status")

    status = df["status"].astype(str).str.strip().str.lower()
    is_validated = status.eq("validated")
    is_rejected = status.eq("rejected")

    n_total = len(df)
    n_validated = int(is_validated.sum())
    n_rejected = int(is_rejected.sum())

    valid_df = df.loc[is_validated].copy()

    is_magnetic = to_bool_series(ensure_column(valid_df, "is_magnetic", False))
    is_novel = to_bool_series(ensure_column(valid_df, "is_novel", False))

    magnetic_ratio = float(is_magnetic.mean()) if n_validated else 0.0
    novelty_ratio = float(is_novel.mean()) if n_validated else 0.0

    if "rejection_reason" in df.columns:
        rejection_reason = df["rejection_reason"].fillna("").astype(str).str.strip()
        duplicate_count = int(rejection_reason.eq("duplicate").sum())
        rejection_reasons = {
            str(k): int(v)
            for k, v in rejection_reason[rejection_reason.ne("")].value_counts().sort_index().items()
        }
    else:
        is_duplicate_all = to_bool_series(ensure_column(df, "is_duplicate", False))
        duplicate_count = int(is_duplicate_all.sum())
        rejection_reasons = {}

    duplicate_ratio = duplicate_count / n_total if n_total else 0.0

    density = pd.to_numeric(ensure_column(valid_df, "density", np.nan), errors="coerce")
    volume_per_atom = pd.to_numeric(ensure_column(valid_df, "volume_per_atom", np.nan), errors="coerce")

    avg_density = float(density.mean()) if len(density.dropna()) else np.nan
    avg_volume_per_atom = float(volume_per_atom.mean()) if len(volume_per_atom.dropna()) else np.nan

    return {
        "model": model,
        "model_name": model,
        "source_csv": str(csv_path),
        "n_total": int(n_total),
        "n_validated": n_validated,
        "n_rejected": n_rejected,
        "validity_ratio": n_validated / n_total if n_total else 0.0,
        "magnetic_ratio": magnetic_ratio,
        "novelty_ratio": novelty_ratio,
        "duplicate_ratio": duplicate_ratio,
        "avg_density": avg_density,
        "avg_volume_per_atom": avg_volume_per_atom,
        "rejection_reasons": rejection_reasons,
    }


def apply_paper_style(ax):
    ax.set_facecolor("white")
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def save_close(fig, filename, legend_outside=False):
    if legend_outside:
        fig.tight_layout(rect=[0, 0, 0.82, 1])
    else:
        fig.tight_layout()
    fig.savefig(OUTDIR / filename, bbox_inches="tight")
    plt.close(fig)


def add_value_labels(ax, bars, decimals=1, y_offset=1.0, fontsize=9):
    for bar in bars:
        h = bar.get_height()
        if pd.isna(h):
            continue
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            h + y_offset,
            f"{h:.{decimals}f}",
            ha="center",
            va="bottom",
            fontsize=fontsize,
        )


def minmax_good_high(s: pd.Series) -> pd.Series:
    mn, mx = s.min(skipna=True), s.max(skipna=True)
    if pd.isna(mn) or pd.isna(mx) or abs(mx - mn) < 1e-12:
        return pd.Series([1.0] * len(s), index=s.index)
    return (s - mn) / (mx - mn)


def minmax_good_low(s: pd.Series) -> pd.Series:
    mn, mx = s.min(skipna=True), s.max(skipna=True)
    if pd.isna(mn) or pd.isna(mx) or abs(mx - mn) < 1e-12:
        return pd.Series([1.0] * len(s), index=s.index)
    return 1.0 - (s - mn) / (mx - mn)


data = [compute_metrics_from_all_structures(model, path) for model, path in MODEL_CSVS.items()]
summary_df = pd.DataFrame(data)

summary_df["validity_percent"] = summary_df["validity_ratio"] * 100
summary_df["magnetic_percent"] = summary_df["magnetic_ratio"] * 100
summary_df["novelty_percent"] = summary_df["novelty_ratio"] * 100
summary_df["duplicate_percent"] = summary_df["duplicate_ratio"] * 100

summary_df = summary_df[
    [
        "model",
        "source_csv",
        "n_total",
        "n_validated",
        "n_rejected",
        "validity_percent",
        "magnetic_percent",
        "novelty_percent",
        "duplicate_percent",
        "avg_density",
        "avg_volume_per_atom",
        "rejection_reasons",
    ]
].copy()

summary_df.to_csv(OUTDIR / "summary_metrics_from_all_structures.csv", index=False)

with open(OUTDIR / "summary_metrics_from_all_structures.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("[INFO] Summary metrics:")
print(summary_df[[
    "model",
    "n_total",
    "n_validated",
    "validity_percent",
    "magnetic_percent",
    "novelty_percent",
    "duplicate_percent",
    "avg_density",
    "avg_volume_per_atom",
]].to_string(index=False))


tmp = summary_df.sort_values("validity_percent", ascending=False).reset_index(drop=True)

fig, ax = plt.subplots(figsize=(9.5, 5.5))
fig.patch.set_facecolor("white")
x = np.arange(len(tmp))
ax.bar(x, tmp["n_validated"], width=0.65, color=COLORS["validated"], edgecolor="black", linewidth=0.4, label="Validated")
ax.bar(x, tmp["n_rejected"], width=0.65, bottom=tmp["n_validated"], color=COLORS["rejected"], edgecolor="black", linewidth=0.4, label="Rejected")
for i, (v, r) in enumerate(zip(tmp["n_validated"], tmp["n_rejected"])):
    ax.text(i, v / 2, f"{int(v)}", ha="center", va="center", fontsize=9, color="white", fontweight="bold")
    ax.text(i, v + r / 2, f"{int(r)}", ha="center", va="center", fontsize=9)
ax.set_title("Validated and Rejected Structures by Model", pad=12)
ax.set_ylabel("Number of structures")
ax.set_xticks(x)
ax.set_xticklabels(tmp["model"])
apply_paper_style(ax)
ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False)
save_close(fig, "01_validated_vs_rejected_stacked.png", legend_outside=True)


single_plots = [
    ("validity_percent", "Validity Rate by Model", "Percent", "02_validity_percent.png", COLORS["validity"], 105),
    ("magnetic_percent", "Magnetic Ratio by Model", "Percent", "03_magnetic_percent.png", COLORS["magnetic"], 105),
    ("novelty_percent", "Novelty Ratio by Model", "Percent", "04_novelty_percent.png", COLORS["novelty"], 105),
    ("duplicate_percent", "Duplicate Ratio by Model", "Percent", "05_duplicate_percent.png", COLORS["duplicate"], None),
    ("avg_density", "Average Density by Model", "Density", "06_avg_density.png", COLORS["density"], None),
    ("avg_volume_per_atom", "Average Volume per Atom by Model", "Volume per atom", "07_avg_volume_per_atom.png", COLORS["volume"], None),
]

for col, title, ylabel, fname, color, ylim in single_plots:
    tmp2 = summary_df.sort_values(col, ascending=False).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    fig.patch.set_facecolor("white")
    bars = ax.bar(tmp2["model"], tmp2[col], color=color, edgecolor="black", linewidth=0.4, width=0.62)
    add_value_labels(ax, bars, decimals=1 if "percent" in col else 2, y_offset=1.0 if "percent" in col else 0.12)
    ax.set_title(title, pad=12)
    ax.set_ylabel(ylabel)
    if ylim is not None:
        ax.set_ylim(0, ylim)
    else:
        max_val = tmp2[col].max(skipna=True)
        ax.set_ylim(0, max_val * 1.18 if pd.notna(max_val) and max_val > 0 else 1)
    apply_paper_style(ax)
    save_close(fig, fname)


tmp = summary_df.sort_values("validity_percent", ascending=False).reset_index(drop=True)
fig, ax = plt.subplots(figsize=(11, 5.8))
fig.patch.set_facecolor("white")
x = np.arange(len(tmp))
width = 0.18
bars1 = ax.bar(x - 1.5 * width, tmp["validity_percent"], width, label="Validity %", color=COLORS["validity"], edgecolor="black", linewidth=0.4)
bars2 = ax.bar(x - 0.5 * width, tmp["magnetic_percent"], width, label="Magnetic %", color=COLORS["magnetic"], edgecolor="black", linewidth=0.4)
bars3 = ax.bar(x + 0.5 * width, tmp["novelty_percent"], width, label="Novelty %", color=COLORS["novelty"], edgecolor="black", linewidth=0.4)
bars4 = ax.bar(x + 1.5 * width, tmp["duplicate_percent"], width, label="Duplicate %", color=COLORS["duplicate"], edgecolor="black", linewidth=0.4)
add_value_labels(ax, bars1, decimals=1, y_offset=1.2)
add_value_labels(ax, bars2, decimals=1, y_offset=1.2)
add_value_labels(ax, bars3, decimals=1, y_offset=1.2)
add_value_labels(ax, bars4, decimals=1, y_offset=1.2)
ax.set_title("Comparison of Main Ratios Across Generative Models", pad=14)
ax.set_ylabel("Percent")
ax.set_xticks(x)
ax.set_xticklabels(tmp["model"])
ax.set_ylim(0, 112)
apply_paper_style(ax)
ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, borderaxespad=0.0)
save_close(fig, "08_grouped_main_ratios.png", legend_outside=True)


all_reasons = sorted({r for rr in summary_df["rejection_reasons"] for r in rr.keys()})
reason_rows = []
for _, row in summary_df.iterrows():
    rec = {"model": row["model"]}
    total_rejected = row["n_rejected"]
    for reason in all_reasons:
        count = row["rejection_reasons"].get(reason, 0)
        rec[reason] = count
        rec[f"{reason}_percent_of_rejected"] = count / total_rejected * 100 if total_rejected > 0 else 0.0
    reason_rows.append(rec)

reasons_df = pd.DataFrame(reason_rows)
reasons_df.to_csv(OUTDIR / "rejection_reasons_summary.csv", index=False)

if all_reasons:
    tmp_reason = reasons_df.set_index("model")[all_reasons]
    fig, ax = plt.subplots(figsize=(10.5, 6))
    fig.patch.set_facecolor("white")
    bottom = np.zeros(len(tmp_reason))
    for reason in all_reasons:
        vals = tmp_reason[reason].values
        ax.bar(tmp_reason.index, vals, bottom=bottom, label=reason.replace("_", " "), color=REASON_COLORS.get(reason, "#999999"), edgecolor="black", linewidth=0.35)
        for i, v in enumerate(vals):
            if v >= 40:
                ax.text(i, bottom[i] + v / 2, f"{int(v)}", ha="center", va="center", fontsize=8)
        bottom = bottom + vals
    ax.set_title("Rejection Reasons by Model", pad=12)
    ax.set_ylabel("Rejected structures")
    apply_paper_style(ax)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, borderaxespad=0.0)
    save_close(fig, "09_rejection_reasons_stacked_counts.png", legend_outside=True)

    percent_cols = [f"{r}_percent_of_rejected" for r in all_reasons]
    tmp_pct = reasons_df.set_index("model")[percent_cols].copy()
    tmp_pct.columns = all_reasons
    fig, ax = plt.subplots(figsize=(10.5, 6))
    fig.patch.set_facecolor("white")
    bottom = np.zeros(len(tmp_pct))
    for reason in all_reasons:
        vals = tmp_pct[reason].values
        ax.bar(tmp_pct.index, vals, bottom=bottom, label=reason.replace("_", " "), color=REASON_COLORS.get(reason, "#999999"), edgecolor="black", linewidth=0.35)
        bottom = bottom + vals
    ax.set_title("Composition of Rejection Reasons Within Rejected Set", pad=12)
    ax.set_ylabel("Percent of rejected structures")
    ax.set_ylim(0, 100)
    apply_paper_style(ax)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, borderaxespad=0.0)
    save_close(fig, "10_rejection_reasons_stacked_percent.png", legend_outside=True)


heatmap_df = summary_df.set_index("model")[[
    "validity_percent",
    "magnetic_percent",
    "novelty_percent",
    "duplicate_percent",
    "avg_density",
    "avg_volume_per_atom",
]].copy()
heatmap_labels = ["Validity %", "Magnetic %", "Novelty %", "Duplicate %", "Avg density", "Avg vol/atom"]

fig, ax = plt.subplots(figsize=(9.6, 5.2))
fig.patch.set_facecolor("white")
im = ax.imshow(heatmap_df.values, aspect="auto", cmap="YlGnBu")
ax.set_xticks(np.arange(len(heatmap_df.columns)))
ax.set_xticklabels(heatmap_labels, rotation=30, ha="right")
ax.set_yticks(np.arange(len(heatmap_df.index)))
ax.set_yticklabels(heatmap_df.index)
ax.set_title("Heatmap of Core Benchmark Metrics", pad=12)
for i in range(heatmap_df.shape[0]):
    for j in range(heatmap_df.shape[1]):
        val = heatmap_df.iloc[i, j]
        ax.text(j, i, f"{val:.2f}" if pd.notna(val) else "NA", ha="center", va="center", fontsize=8)
cbar = fig.colorbar(im, ax=ax, shrink=0.92)
cbar.outline.set_linewidth(0.6)
save_close(fig, "11_heatmap_core_metrics.png")


radar_df = summary_df.copy()
radar_df["validity_norm"] = radar_df["validity_percent"] / 100.0
radar_df["magnetic_norm"] = radar_df["magnetic_percent"] / 100.0
radar_df["novelty_norm"] = radar_df["novelty_percent"] / 100.0
radar_df["low_duplicate_goodness"] = minmax_good_low(radar_df["duplicate_percent"])
radar_df["density_norm"] = minmax_good_high(radar_df["avg_density"])
radar_df["compactness_goodness"] = minmax_good_low(radar_df["avg_volume_per_atom"])

score_cols = [
    ("validity_norm", "Validity"),
    ("magnetic_norm", "Magnetic"),
    ("novelty_norm", "Novelty"),
    ("low_duplicate_goodness", "Low duplicates"),
    ("density_norm", "Density"),
    ("compactness_goodness", "Compactness"),
]

tmp = radar_df.sort_values("validity_percent", ascending=False).reset_index(drop=True)
fig, ax = plt.subplots(figsize=(12, 5.8))
fig.patch.set_facecolor("white")
x = np.arange(len(tmp))
bar_w = 0.12
palette = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2", "#B279A2"]
for idx, ((col, label), color) in enumerate(zip(score_cols, palette)):
    offsets = x + (idx - (len(score_cols) - 1) / 2) * bar_w
    bars = ax.bar(offsets, tmp[col], width=bar_w, label=label, color=color, edgecolor="black", linewidth=0.35)
    add_value_labels(ax, bars, decimals=2, y_offset=0.015, fontsize=8)
ax.set_title("Normalized Multi-Metric Comparison", pad=12)
ax.set_ylabel("Normalized score")
ax.set_xticks(x)
ax.set_xticklabels(tmp["model"])
ax.set_ylim(0, 1.08)
apply_paper_style(ax)
ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, borderaxespad=0.0)
save_close(fig, "12_normalized_multi_metric_comparison.png", legend_outside=True)

print(f"[OK] Saved paper-style figures to: {OUTDIR.resolve()}")
