from __future__ import annotations

"""
Publication figure builder for the CIF-only magnetic-reference filter paper.

This script builds, from canonical post-extraction CSVs only:
  1. Figure 1 split into two high-resolution row figures:
       - Figure1_row_top_ABC
       - Figure1_row_bottom_DEFG
  2. Figure2_representation_robustness   (A-C; compact representation-ablation figure)
  3. FigureS1_generator_secondary_metrics
  4. FigureS2_dft_validation_details
  5. FigureS3_magndata_sha_dedup_sensitivity

Optional with --write-components:
  - reference-validation component (A-C)
  - generator-benchmark component (A-D)

All palettes are preserved from the publication version.
MatterGen conditioning is intentionally not a main-text figure.

It preserves the approved article palettes used in the existing article_figures.py,
never re-runs CIF extraction, and can run a strict publication audit against the
canonical 45-feature paper numbers.

Example
-------
python -m paper.figures \
  --reference-scores analysis_v1_45/main/reference_validation_scores.csv \
  --query-scores analysis_v1_45/main/query_scores.csv \
  --dft-join analysis_tables/dft_join_default.csv \
  --feature-manifest analysis_v1_45/main/feature_manifest.csv \
  --output-dir paper_output \
  --strict-paper-audit
"""

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap


# =============================================================================
# Canonical article ordering and labels
# =============================================================================

REF_ORDER = ["MAGNDATA", "AFM", "FM", "FiM", "NM"]
MAGNETIC_REF_ORDER = ["MAGNDATA", "AFM", "FM", "FiM"]

GENERATOR_ORDER = [
    "mattergen_base",
    "mattergen_finetuned",
    "concdvae_base",
    "concdvae_finetuned",
    "crysjepa_base",
    "crysjepa_refined",
    "crystalformer",
    "crystalllm",
]

DFT_GENERATOR_ORDER = [
    "mattergen_base",
    "concdvae_base",
    "crystalformer",
    "crystalllm",
]

DISPLAY_LABELS = {
    "mattergen_base": "MatterGen base",
    "mattergen_finetuned": "MatterGen tuned",
    "concdvae_base": "ConcDVAE base",
    "concdvae_finetuned": "ConcDVAE tuned",
    "crysjepa_base": "CrysJEPA base",
    "crysjepa_refined": "CrysJEPA refined",
    "crystalformer": "CrystalFormer",
    "crystalllm": "CrystALLM",
}

# Historical / alternate aliases accepted on input.
DATASET_ALIASES = {
    "mattergen_tuned": "mattergen_finetuned",
    "concdvae_tuned": "concdvae_finetuned",
    "mattergen": "mattergen_base",
    "concdvae": "concdvae_base",
}


# =============================================================================
# Approved article palettes (preserved from current article_figures.py)
# =============================================================================

REFERENCE_COLORS = {
    "MAGNDATA": "#7D8993",
    "AFM": "#D6A64F",
    "FM": "#5F7F57",
    "FiM": "#A65A73",
    "NM": "#C7CDD3",
}

GENERATOR_COLORS = {
    "mattergen_base": "#9DAA90",
    "mattergen_finetuned": "#4F6B46",
    "concdvae_base": "#E1B15A",
    "concdvae_finetuned": "#C05C17",
    "crystalformer": "#DD8B63",
    "crystalllm": "#B84D45",
    "crysjepa_base": "#8CA5AE",
    "crysjepa_refined": "#344E68",
}

KNOWN_LABEL_CMAP = LinearSegmentedColormap.from_list(
    "known_label_validation",
    ["#F7F7F5", "#EBE3CF", "#C8D2D0", "#8CA1B0", "#334B6C"],
)
KNOWN_LABEL_TEXT_DARK = "#2D3748"
KNOWN_LABEL_TEXT_LIGHT = "white"

CONTRAST_LINE_COLORS = {
    "MAGNDATA": "#4C98D8",
    "AFM": "#F28E2B",
    "FM": "#35A853",
    "FiM": "#E15759",
    "NM": "#9467BD",
}

DFT_ERROR_COLOR = "#333333"
REFERENCE_METRIC_BAR_COLOR = "#7D8993"


# =============================================================================
# Canonical paper audit targets (45-feature release)
# =============================================================================

def _load_paper_expected() -> dict:
    root = Path(__file__).resolve().parents[1]
    path = root / "paper" / "manifests" / "validation_metrics.json"
    if path.exists():
        d = json.loads(path.read_text(encoding="utf-8"))
        return {
            "n_features": int(d["feature_count"]),
            "n_reference": int(d["reference_total"]),
            "five_branch_agreement": float(d["reference_validation"]["five_branch_agreement"]),
            "magnetic_sensitivity": float(d["reference_validation"]["magnetic_sensitivity"]),
            "nm_specificity": float(d["reference_validation"]["nm_specificity"]),
            "balanced_accuracy": float(d["reference_validation"]["binary_balanced_accuracy"]),
            "dft_n": int(d["external_dft"]["n_total"]),
            "dft_n_positive": int(d["external_dft"]["pipeline_magnetic_like_n"]),
            "dft_positive_yield": float(d["external_dft"]["pipeline_magnetic_like_dft_magnetic_fraction"]),
            "dft_n_negative": int(d["external_dft"]["pipeline_nm_like_n"]),
            "dft_negative_yield": float(d["external_dft"]["pipeline_nm_like_dft_magnetic_fraction"]),
            "dft_positive_by_generator": {
                str(k): float(v)
                for k, v in d["external_dft"]["pipeline_magnetic_like_fraction_by_generator"].items()
            },
        }
    raise FileNotFoundError(f"Canonical paper metrics not found: {path}")


PAPER_EXPECTED = _load_paper_expected()



# =============================================================================
# Styling
# =============================================================================

def configure_style() -> None:
    plt.rcParams.update({
        "font.size": 8.8,
        "axes.titlesize": 10.0,
        "axes.labelsize": 8.8,
        "xtick.labelsize": 7.6,
        "ytick.labelsize": 7.6,
        "legend.fontsize": 7.2,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def pretty_dataset(x: str) -> str:
    return DISPLAY_LABELS.get(str(x).lower(), str(x).replace("_", " "))


def panel_label(ax, label: str) -> None:
    # Label is outside plotting region and does not collide with title/axes.
    ax.text(
        -0.09, 1.06, label,
        transform=ax.transAxes,
        fontsize=16,
        fontweight="bold",
        va="bottom",
        ha="left",
        clip_on=False,
    )


def style_grid_x(ax) -> None:
    ax.xaxis.grid(True, linewidth=0.5, alpha=0.18)
    ax.set_axisbelow(True)


def style_grid_y(ax) -> None:
    ax.yaxis.grid(True, linewidth=0.5, alpha=0.15)
    ax.set_axisbelow(True)


# =============================================================================
# IO and normalization
# =============================================================================

def _canon_reference_label(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    if s.lower() == "fim":
        return "FiM"
    u = s.upper()
    if u in {"MAGNDATA", "AFM", "FM", "NM"}:
        return u
    return s


def _canon_dataset(x):
    s = str(x).strip().lower()
    return DATASET_ALIASES.get(s, s)


def load_inputs(
    reference_scores_path: Path,
    query_scores_path: Path,
    dft_join_path: Path,
    feature_manifest_path: Path | None = None,
) -> dict[str, object]:
    ref = pd.read_csv(reference_scores_path, low_memory=False)
    query = pd.read_csv(query_scores_path, low_memory=False)
    dft = pd.read_csv(dft_join_path, low_memory=False)
    manifest = pd.read_csv(feature_manifest_path) if feature_manifest_path else None

    if "label_order" in ref:
        ref["label_order"] = ref["label_order"].map(_canon_reference_label)
    if "nearest_reference_branch" in ref:
        ref["nearest_reference_branch"] = ref["nearest_reference_branch"].map(_canon_reference_label)
    if "nearest_magnetic_reference_branch" in ref:
        ref["nearest_magnetic_reference_branch"] = ref["nearest_magnetic_reference_branch"].map(_canon_reference_label)

    for df in [ref, query, dft]:
        if "dataset" in df:
            df["dataset"] = df["dataset"].map(_canon_dataset)

    if "dataset_dft" in dft and "dataset" not in dft:
        dft["dataset"] = dft["dataset_dft"].map(_canon_dataset)

    if "dft_is_magnetic" in dft:
        dft["dft_is_magnetic"] = pd.to_numeric(dft["dft_is_magnetic"], errors="coerce")
    elif "is_magnetic_raw" in dft:
        dft["dft_is_magnetic"] = dft["is_magnetic_raw"].astype(str).str.lower().eq("yes").astype(int)
    elif "is_magnetic" in dft:
        dft["dft_is_magnetic"] = dft["is_magnetic"].astype(str).str.lower().isin(["yes", "true", "1"]).astype(int)

    return {
        "reference": ref,
        "query": query,
        "dft": dft,
        "feature_manifest": manifest,
    }


def require_columns(df: pd.DataFrame, columns: Iterable[str], name: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")


# =============================================================================
# Article summaries
# =============================================================================

def build_reference_summary(ref: pd.DataFrame) -> dict[str, object]:
    require_columns(
        ref,
        [
            "label_order",
            "nearest_reference_branch",
            "magnetic_reference_vs_NM_contrast",
            "is_closer_to_magnetic_reference_than_NM",
        ],
        "reference scores",
    )

    d = ref[ref["label_order"].isin(REF_ORDER)].copy()

    confusion_counts = pd.crosstab(d["label_order"], d["nearest_reference_branch"])
    confusion_counts = confusion_counts.reindex(index=REF_ORDER, columns=REF_ORDER, fill_value=0)
    confusion_fraction = confusion_counts.div(confusion_counts.sum(axis=1).replace(0, np.nan), axis=0)

    five = float((d["label_order"] == d["nearest_reference_branch"]).mean())

    true_mag = d["label_order"].isin(MAGNETIC_REF_ORDER)
    pred_mag = pd.to_numeric(
        d["is_closer_to_magnetic_reference_than_NM"], errors="coerce"
    ).fillna(0).astype(int).eq(1)

    sensitivity = float(pred_mag[true_mag].mean())
    specificity = float((~pred_mag[~true_mag]).mean())
    balanced = float(np.mean([sensitivity, specificity]))

    metrics = pd.DataFrame({
        "metric": [
            "Five-branch agreement",
            "Magnetic sensitivity",
            "NM specificity",
            "Balanced accuracy",
        ],
        "value": [five, sensitivity, specificity, balanced],
    })

    return {
        "confusion_fraction": confusion_fraction,
        "metrics": metrics,
        "five_branch_agreement": five,
        "magnetic_sensitivity": sensitivity,
        "nm_specificity": specificity,
        "balanced_accuracy": balanced,
        "n_reference": len(d),
    }


def _formula_cluster_bootstrap_fraction(
    g: pd.DataFrame,
    n_bootstrap: int = 1000,
    seed: int = 42,
) -> tuple[float, float]:
    """Formula-cluster bootstrap matching the paper logic for enrichment CI."""
    if g.empty:
        return np.nan, np.nan

    formula = g.get("formula_reduced", pd.Series(index=g.index, dtype=object)).copy()
    formula = formula.fillna("__SID__" + g.get("structure_id", pd.Series(g.index, index=g.index)).astype(str)).astype(str)
    tmp = pd.DataFrame({
        "formula": formula,
        "positive": pd.to_numeric(g["is_closer_to_magnetic_reference_than_NM"], errors="coerce").fillna(0).astype(int),
    })

    clusters = tmp.groupby("formula", sort=False).agg(n=("positive", "size"), k=("positive", "sum"))
    if clusters.empty:
        return np.nan, np.nan

    n = clusters["n"].to_numpy(float)
    k = clusters["k"].to_numpy(float)
    m = len(clusters)
    rng = np.random.default_rng(seed)

    # Chunk to limit memory for large formula counts.
    vals = []
    remaining = n_bootstrap
    chunk = 200
    while remaining > 0:
        b = min(chunk, remaining)
        picks = rng.integers(0, m, size=(b, m))
        den = n[picks].sum(axis=1)
        num = k[picks].sum(axis=1)
        vals.append(np.divide(num, den, out=np.full(b, np.nan), where=den > 0))
        remaining -= b

    arr = np.concatenate(vals)
    arr = arr[np.isfinite(arr)]
    if not len(arr):
        return np.nan, np.nan
    return float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975))


def build_generator_summary(
    query: pd.DataFrame,
    n_bootstrap: int = 1000,
    seed: int = 42,
) -> pd.DataFrame:
    require_columns(
        query,
        [
            "dataset",
            "magnetic_reference_vs_NM_contrast",
            "is_closer_to_magnetic_reference_than_NM",
            "nearest_magnetic_reference_branch",
        ],
        "query scores",
    )

    rows = []
    for rank, ds in enumerate(GENERATOR_ORDER):
        g = query[query["dataset"].astype(str).eq(ds)].copy()
        if "score_status" in g:
            g = g[g["score_status"].astype(str).eq("ok")].copy()
        if g.empty:
            continue

        pos = pd.to_numeric(g["is_closer_to_magnetic_reference_than_NM"], errors="coerce").fillna(0).astype(int)
        fmag = float(pos.mean())
        lo, hi = _formula_cluster_bootstrap_fraction(g, n_bootstrap=n_bootstrap, seed=seed + rank)

        positive = g[pos.eq(1)]
        row = {
            "dataset": ds,
            "n": len(g),
            "fmag": fmag,
            "fmag_ci_low": lo,
            "fmag_ci_high": hi,
            "median_contrast": float(pd.to_numeric(g["magnetic_reference_vs_NM_contrast"], errors="coerce").median()),
        }
        for branch in MAGNETIC_REF_ORDER:
            row[f"branch_{branch}"] = (
                float(positive["nearest_magnetic_reference_branch"].astype(str).eq(branch).mean())
                if len(positive) else np.nan
            )
        rows.append(row)

    return pd.DataFrame(rows)


def wilson_interval(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return np.nan, np.nan
    p = k / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n)) / den
    half = z * np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return float(center - half), float(center + half)


def build_dft_summary(dft: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float | int]]:
    require_columns(
        dft,
        ["dataset", "dft_is_magnetic", "is_closer_to_magnetic_reference_than_NM"],
        "DFT join",
    )

    d = dft.copy()
    if "variant" in d:
        # If multiple variants accidentally enter, prefer canonical 45-feature rows.
        if (d["variant"].astype(str) == "default").any():
            d = d[d["variant"].astype(str).eq("default")].copy()

    d = d[pd.to_numeric(d["dft_is_magnetic"], errors="coerce").notna()].copy()
    d["dft_is_magnetic"] = pd.to_numeric(d["dft_is_magnetic"], errors="coerce").astype(int)
    d["pipeline_positive"] = pd.to_numeric(
        d["is_closer_to_magnetic_reference_than_NM"], errors="coerce"
    ).fillna(0).astype(int).eq(1)

    rows = []
    for ds in DFT_GENERATOR_ORDER:
        g = d[d["dataset"].astype(str).eq(ds)]
        gp = g[g["pipeline_positive"]]
        n = len(gp)
        k = int(gp["dft_is_magnetic"].sum()) if n else 0
        lo, hi = wilson_interval(k, n)
        rows.append({
            "dataset": ds,
            "n_dft_total": len(g),
            "n_pipeline_positive": n,
            "dft_magnetic_count_positive": k,
            "dft_magnetic_given_pipeline_positive": (k/n if n else np.nan),
            "ci95_low": lo,
            "ci95_high": hi,
        })

    positive = d[d["pipeline_positive"]]
    negative = d[~d["pipeline_positive"]]
    overall = {
        "n_dft": int(len(d)),
        "n_pipeline_positive": int(len(positive)),
        "dft_positive_yield": float(positive["dft_is_magnetic"].mean()) if len(positive) else np.nan,
        "n_pipeline_negative": int(len(negative)),
        "dft_negative_yield": float(negative["dft_is_magnetic"].mean()) if len(negative) else np.nan,
    }
    return pd.DataFrame(rows), overall




def build_generator_secondary_summary(query: pd.DataFrame) -> pd.DataFrame:
    require_columns(
        query,
        [
            "dataset",
            "formula_reduced",
            "nearest_magnetic_reference_distance",
            "magnetic_reference_support_percentile",
        ],
        "query scores",
    )
    rows = []
    per_dataset_n = query.groupby("dataset").size().to_dict()
    default_den = max(per_dataset_n.values()) if per_dataset_n else np.nan
    for ds in GENERATOR_ORDER:
        g = query[query["dataset"].astype(str).eq(ds)].copy()
        if g.empty:
            continue
        n = len(g)
        denom = default_den if np.isfinite(default_den) and default_den > 0 else n
        rows.append({
            "dataset": ds,
            "n_scored": int(n),
            "scored_fraction": float(n / denom) if denom else np.nan,
            "median_dmag": float(pd.to_numeric(g["nearest_magnetic_reference_distance"], errors="coerce").median()),
            "median_support_percentile": float(pd.to_numeric(g["magnetic_reference_support_percentile"], errors="coerce").median()),
            "formula_diversity": float(g["formula_reduced"].astype(str).nunique() / n) if n else np.nan,
        })
    return pd.DataFrame(rows)


def load_afmfm_subset(path: Path | None) -> pd.DataFrame | None:
    if path is None:
        return None
    d = pd.read_csv(path, low_memory=False)
    require_columns(
        d,
        ["ground_state", "dE_per_atom_meV", "nearest_magnetic_reference_branch", "is_closer_to_magnetic_reference_than_NM"],
        "AFM/FM limitation subset",
    )
    return d


def load_sha_sensitivity_inputs(
    reference_path: Path | None,
    generator_path: Path | None,
    dft_path: Path | None,
) -> tuple[pd.DataFrame | None, pd.DataFrame | None, pd.DataFrame | None]:
    if reference_path is None and generator_path is None and dft_path is None:
        return None, None, None
    if any(x is None for x in [reference_path, generator_path, dft_path]):
        raise ValueError(
            "MAGNDATA SHA sensitivity figure requires --sha-reference-sensitivity, "
            "--sha-generator-sensitivity, and --sha-dft-sensitivity together"
        )
    ref = pd.read_csv(reference_path, low_memory=False)
    gen = pd.read_csv(generator_path, low_memory=False)
    dft = pd.read_csv(dft_path, low_memory=False)
    require_columns(ref, ["metric", "sha_deduplicated", "default", "delta_dedup_minus_main"], "SHA reference sensitivity")
    require_columns(gen, ["dataset", "delta_fmag", "delta_median_contrast"], "SHA generator sensitivity")
    require_columns(
        dft,
        ["variant", "p_dft_magnetic_given_pipeline_positive", "p_dft_magnetic_given_pipeline_negative"],
        "SHA DFT sensitivity",
    )
    gen["dataset"] = gen["dataset"].map(_canon_dataset)
    return ref, gen, dft

# =============================================================================
# Plot primitives used identically in separate and combined figures
# =============================================================================

def draw_confusion(ax, confusion: pd.DataFrame, add_colorbar: bool = True):
    c = confusion.reindex(index=REF_ORDER, columns=REF_ORDER)
    values = c.to_numpy(float)
    im = ax.imshow(values, aspect="auto", vmin=0, vmax=1, cmap=KNOWN_LABEL_CMAP, interpolation="nearest")

    ax.set_xticks(range(len(c.columns)))
    ax.set_xticklabels(c.columns, rotation=35, ha="right")
    ax.set_yticks(range(len(c.index)))
    ax.set_yticklabels(c.index)
    ax.set_xlabel("Nearest reference branch")
    ax.set_ylabel("Known database label")
    ax.set_title("Known-label validation", pad=8)

    ax.set_xticks(np.arange(-0.5, len(c.columns), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(c.index), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.4)
    ax.tick_params(which="minor", bottom=False, left=False)

    for i in range(c.shape[0]):
        for j in range(c.shape[1]):
            v = values[i, j]
            if np.isfinite(v):
                color = KNOWN_LABEL_TEXT_LIGHT if v >= 0.45 else KNOWN_LABEL_TEXT_DARK
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8.4, color=color)

    if add_colorbar:
        # Inset colorbar avoids shrinking this subplot relative to the other panels.
        cax = ax.inset_axes([1.035, 0.04, 0.035, 0.92])
        cb = ax.figure.colorbar(im, cax=cax)
        cb.set_label("Fraction")
    return im


def draw_reference_metrics(ax, metrics: pd.DataFrame):
    y = np.arange(len(metrics))
    vals = pd.to_numeric(metrics["value"], errors="coerce").to_numpy(float)
    ax.barh(y, vals, color=REFERENCE_METRIC_BAR_COLOR, height=0.68, edgecolor="none")
    ax.set_yticks(y)
    ax.set_yticklabels(metrics["metric"])
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xlabel("Score")
    ax.set_title("Reference validation", pad=8)
    style_grid_x(ax)


def draw_reference_contrast(ax, ref: pd.DataFrame):
    for lab in REF_ORDER:
        vals = pd.to_numeric(
            ref.loc[ref["label_order"].astype(str).eq(lab), "magnetic_reference_vs_NM_contrast"],
            errors="coerce",
        ).dropna()
        if len(vals):
            ax.hist(
                vals,
                bins=60,
                density=True,
                histtype="step",
                linewidth=1.45,
                color=CONTRAST_LINE_COLORS[lab],
                label=lab,
            )
    ax.axvline(0, linestyle="--", linewidth=1.0, color="#4C98D8")
    ax.set_xlabel("Magnetic-reference vs NM contrast")
    ax.set_ylabel("Density")
    ax.set_title("Reference contrast distributions", pad=8)
    ax.legend(frameon=False, ncol=2, loc="upper right")


def draw_enrichment(ax, summary: pd.DataFrame):
    d = summary.set_index("dataset").reindex([x for x in GENERATOR_ORDER if x in set(summary["dataset"])]).reset_index()
    y = np.arange(len(d))
    vals = d["fmag"].to_numpy(float)
    colors = [GENERATOR_COLORS.get(ds, "#888888") for ds in d["dataset"]]
    ax.barh(y, vals, color=colors, height=0.68, edgecolor="none")

    lo = pd.to_numeric(d["fmag_ci_low"], errors="coerce").to_numpy(float)
    hi = pd.to_numeric(d["fmag_ci_high"], errors="coerce").to_numpy(float)
    ok = np.isfinite(vals) & np.isfinite(lo) & np.isfinite(hi)
    if ok.any():
        ax.errorbar(
            vals[ok], y[ok],
            xerr=np.vstack([vals[ok]-lo[ok], hi[ok]-vals[ok]]),
            fmt="none", ecolor=DFT_ERROR_COLOR, elinewidth=1, capsize=2.5,
        )

    ax.set_yticks(y)
    ax.set_yticklabels([pretty_dataset(ds) for ds in d["dataset"]])
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xlabel("Fraction closer to magnetic than NM reference")
    ax.set_title("Magnetic-reference enrichment", pad=8)
    style_grid_x(ax)


def draw_median_contrast(ax, summary: pd.DataFrame):
    d = summary.set_index("dataset").reindex([x for x in GENERATOR_ORDER if x in set(summary["dataset"])]).reset_index()
    y = np.arange(len(d))
    vals = d["median_contrast"].to_numpy(float)
    colors = [GENERATOR_COLORS.get(ds, "#888888") for ds in d["dataset"]]
    ax.barh(y, vals, color=colors, height=0.68, edgecolor="none")
    ax.axvline(0, color="#555555", linewidth=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels([pretty_dataset(ds) for ds in d["dataset"]])
    ax.invert_yaxis()
    ax.set_xlabel(r"Median magnetic-reference contrast, $d_{NM}-d_{mag}$")
    ax.set_title("Median magnetic-reference contrast", pad=8)
    style_grid_x(ax)


def draw_branch_composition(ax, summary: pd.DataFrame):
    d = summary.set_index("dataset").reindex([x for x in GENERATOR_ORDER if x in set(summary["dataset"])]).reset_index()
    x = np.arange(len(d))
    bottom = np.zeros(len(d))
    for branch in MAGNETIC_REF_ORDER:
        vals = pd.to_numeric(d[f"branch_{branch}"], errors="coerce").fillna(0).to_numpy(float)
        ax.bar(
            x, vals, bottom=bottom, width=0.72,
            label=branch, color=REFERENCE_COLORS[branch], edgecolor="none",
        )
        bottom += vals
    ax.set_xticks(x)
    ax.set_xticklabels([pretty_dataset(ds) for ds in d["dataset"]], rotation=20, ha="right")
    ax.tick_params(axis="x", pad=2)
    ax.set_ylim(0, 1)
    ax.margins(x=0.05)
    ax.set_ylabel("Fraction among magnetic-like candidates")
    ax.set_title("Nearest magnetic-reference branch composition", pad=30)
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.03),
              handlelength=1.0, handletextpad=0.4, columnspacing=0.7, borderaxespad=0.15)
    style_grid_y(ax)


def draw_dft_confirmation(ax, dft_summary: pd.DataFrame):
    d = dft_summary.set_index("dataset").reindex([x for x in DFT_GENERATOR_ORDER if x in set(dft_summary["dataset"])]).reset_index()
    y = np.arange(len(d))
    vals = pd.to_numeric(d["dft_magnetic_given_pipeline_positive"], errors="coerce").to_numpy(float)
    colors = [GENERATOR_COLORS.get(ds, "#888888") for ds in d["dataset"]]
    ax.barh(y, vals, color=colors, height=0.68, edgecolor="none")

    lo = pd.to_numeric(d["ci95_low"], errors="coerce").to_numpy(float)
    hi = pd.to_numeric(d["ci95_high"], errors="coerce").to_numpy(float)
    ok = np.isfinite(vals) & np.isfinite(lo) & np.isfinite(hi)
    if ok.any():
        ax.errorbar(
            vals[ok], y[ok],
            xerr=np.vstack([vals[ok]-lo[ok], hi[ok]-vals[ok]]),
            fmt="none", ecolor=DFT_ERROR_COLOR, elinewidth=1, capsize=2.5,
        )

    ax.set_yticks(y)
    ax.set_yticklabels([pretty_dataset(ds) for ds in d["dataset"]])
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xlabel("Fraction confirmed magnetic by DFT")
    ax.set_title("DFT confirmation among pipeline-selected magnetic-like candidates", pad=8)
    style_grid_x(ax)


# =============================================================================
# Figure builders
# =============================================================================

def save_figure(fig, stem: Path, dpi: int = 600) -> tuple[Path, Path]:
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    png = stem.with_suffix(".png")
    pdf = stem.with_suffix(".pdf")
    fig.savefig(png, dpi=dpi, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return png, pdf


def build_figure1(ref: pd.DataFrame, ref_summary: dict[str, object], outdir: Path, dpi: int = 600):
    # 1 x 3 only: PCA deliberately removed from main text.
    fig = plt.figure(figsize=(16.0, 5.2))
    gs = fig.add_gridspec(1, 3, left=0.055, right=0.985, bottom=0.14, top=0.91, wspace=0.36)
    axes = [fig.add_subplot(gs[0, i]) for i in range(3)]

    draw_confusion(axes[0], ref_summary["confusion_fraction"], add_colorbar=True)
    draw_reference_metrics(axes[1], ref_summary["metrics"])
    draw_reference_contrast(axes[2], ref)
    for label, ax in zip("ABC", axes):
        panel_label(ax, label)

    return save_figure(fig, Path(outdir) / "Figure1_reference_validation", dpi)


def build_figure2(gen_summary: pd.DataFrame, dft_summary: pd.DataFrame, outdir: Path, dpi: int = 600):
    fig = plt.figure(figsize=(15.6, 10.0))
    gs = fig.add_gridspec(2, 2, left=0.075, right=0.985, bottom=0.09, top=0.945, wspace=0.24, hspace=0.34)
    axes = [
        fig.add_subplot(gs[0, 0]),
        fig.add_subplot(gs[0, 1]),
        fig.add_subplot(gs[1, 0]),
        fig.add_subplot(gs[1, 1]),
    ]

    draw_enrichment(axes[0], gen_summary)
    draw_median_contrast(axes[1], gen_summary)
    draw_branch_composition(axes[2], gen_summary)
    draw_dft_confirmation(axes[3], dft_summary)
    for label, ax in zip("ABCD", axes):
        panel_label(ax, label)

    return save_figure(fig, Path(outdir) / "Figure2_generator_benchmark", dpi)


def build_figure1_row_top(
    ref: pd.DataFrame,
    ref_summary: dict[str, object],
    outdir: Path,
    dpi: int = 600,
):
    """High-resolution top row of Figure 1: A-C."""
    fig = plt.figure(figsize=(17.8, 5.6))
    gs = fig.add_gridspec(
        1, 3,
        left=0.055, right=0.985, bottom=0.18, top=0.90,
        wspace=0.34,
        width_ratios=[1.08, 1.05, 1.02],
    )
    axes = [fig.add_subplot(gs[0, i]) for i in range(3)]
    draw_confusion(axes[0], ref_summary["confusion_fraction"], add_colorbar=True)
    draw_reference_metrics(axes[1], ref_summary["metrics"])
    draw_reference_contrast(axes[2], ref)
    for label, ax in zip("ABC", axes):
        panel_label(ax, label)
    return save_figure(fig, Path(outdir) / "Figure1_row_top_ABC", dpi)


def build_figure1_row_bottom(
    gen_summary: pd.DataFrame,
    dft_summary: pd.DataFrame,
    outdir: Path,
    dpi: int = 600,
):
    """High-resolution bottom row of Figure 1: D-G."""
    fig = plt.figure(figsize=(18.8, 8.8))
    gs = fig.add_gridspec(
        2, 2,
        left=0.070, right=0.985, bottom=0.10, top=0.95,
        wspace=0.20, hspace=0.80,
        width_ratios=[1.08, 1.0],
        height_ratios=[1.0, 1.18],
    )
    axD = fig.add_subplot(gs[0, 0])
    axE = fig.add_subplot(gs[0, 1])
    axF = fig.add_subplot(gs[1, 0])
    axG = fig.add_subplot(gs[1, 1])

    draw_enrichment(axD, gen_summary)
    draw_median_contrast(axE, gen_summary)
    draw_branch_composition(axF, gen_summary)
    draw_dft_confirmation(axG, dft_summary)

    for label, ax in zip("DEFG", [axD, axE, axF, axG]):
        panel_label(ax, label)
    return save_figure(fig, Path(outdir) / "Figure1_row_bottom_DEFG", dpi)



# =============================================================================
# Compact representation-ablation figure
# =============================================================================

ABLATION_REPRESENTATION_ORDER = ["full", "composition_only", "magnetic_topology"]
ABLATION_REPRESENTATION_LABELS = {
    "full": "Full representation\n(45 features)",
    "composition_only": "Composition only\n(7 features)",
    "magnetic_topology": "Magnetic topology\n(25 features)",
}
ABLATION_REPRESENTATION_COLORS = {
    "full": "#7D8993",
    "composition_only": "#D6A64F",
    "magnetic_topology": "#5F7F57",
}


def load_ablation_inputs(
    reference_ablation_path: Path,
    generator_ablation_path: Path,
    main_candidate: str = "default",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ref = pd.read_csv(reference_ablation_path, low_memory=False)
    gen = pd.read_csv(generator_ablation_path, low_memory=False)

    require_columns(
        ref,
        ["main_candidate", "representation", "n_features", "balanced_accuracy"],
        "reference ablation table",
    )
    require_columns(
        gen,
        ["main_candidate", "dataset", "ablation", "main_fmag", "ablation_fmag", "delta_fmag"],
        "generator ablation table",
    )

    ref = ref[ref["main_candidate"].astype(str).eq(main_candidate)].copy()
    gen = gen[gen["main_candidate"].astype(str).eq(main_candidate)].copy()
    gen["dataset"] = gen["dataset"].map(_canon_dataset)

    if ref.empty:
        raise ValueError(f"No reference-ablation rows for main_candidate={main_candidate}")
    if gen.empty:
        raise ValueError(f"No generator-ablation rows for main_candidate={main_candidate}")

    return ref, gen


def audit_ablation_inputs(ref: pd.DataFrame, gen: pd.DataFrame) -> dict[str, object]:
    expected_features = {
        "full": 45,
        "composition_only": 7,
        "magnetic_topology": 25,
    }

    present = set(ref["representation"].astype(str))
    missing = [r for r in ABLATION_REPRESENTATION_ORDER if r not in present]
    if missing:
        raise AssertionError(f"Ablation reference table is missing representations: {missing}")

    ref_idx = ref.set_index("representation")
    for rep, n_expected in expected_features.items():
        got = int(ref_idx.loc[rep, "n_features"])
        if got != n_expected:
            raise AssertionError(f"{rep}: n_features={got}, expected {n_expected}")

    required_generator_rows = {
        (ds, ab)
        for ds in GENERATOR_ORDER
        for ab in ["composition_only", "magnetic_topology"]
    }
    present_rows = set(zip(gen["dataset"].astype(str), gen["ablation"].astype(str)))
    missing_rows = sorted(required_generator_rows - present_rows)
    if missing_rows:
        raise AssertionError(f"Generator ablation table is missing rows: {missing_rows}")

    return {
        "reference_balanced_accuracy": {
            rep: float(ref_idx.loc[rep, "balanced_accuracy"])
            for rep in ABLATION_REPRESENTATION_ORDER
        },
        "n_features": expected_features,
        "n_generator_rows": int(len(gen)),
    }


def draw_ablation_reference_accuracy(ax, ref: pd.DataFrame):
    d = ref.set_index("representation").reindex(ABLATION_REPRESENTATION_ORDER).reset_index()
    vals = pd.to_numeric(d["balanced_accuracy"], errors="coerce").to_numpy(float)
    y = np.arange(len(d))
    colors = [ABLATION_REPRESENTATION_COLORS[r] for r in d["representation"]]

    ax.barh(y, vals, color=colors, height=0.62, edgecolor="none")
    ax.set_yticks(y)
    ax.set_yticklabels([ABLATION_REPRESENTATION_LABELS[r] for r in d["representation"]])
    ax.invert_yaxis()
    ax.set_xlim(0.84, 0.95)
    ax.set_xlabel("Binary balanced accuracy")
    ax.set_title("Reference validation across representations", pad=8)
    style_grid_x(ax)

    for yi, val in enumerate(vals):
        if np.isfinite(val):
            ax.text(val + 0.002, yi, f"{val:.3f}", va="center", ha="left", fontsize=8.3)


def _ablation_delta_pivot(gen: pd.DataFrame) -> pd.DataFrame:
    d = gen.pivot(index="dataset", columns="ablation", values="delta_fmag")
    d = d.reindex(GENERATOR_ORDER)
    return d


def draw_ablation_delta(ax, pivot: pd.DataFrame, column: str, title: str, symmetric_limit: float):
    vals = pd.to_numeric(pivot[column], errors="coerce").to_numpy(float)
    y = np.arange(len(pivot))
    colors = [GENERATOR_COLORS.get(ds, "#888888") for ds in pivot.index]

    ax.barh(y, vals, color=colors, height=0.68, edgecolor="none")
    ax.axvline(0, color="#555555", linewidth=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels([pretty_dataset(ds) for ds in pivot.index])
    ax.invert_yaxis()
    ax.set_xlim(-symmetric_limit, symmetric_limit)
    ax.set_xlabel(r"$\Delta f_{\mathrm{mag}}$ vs full representation")
    ax.set_title(title, pad=8)
    style_grid_x(ax)


def build_figure_ablation(
    reference_ablation: pd.DataFrame,
    generator_ablation: pd.DataFrame,
    outdir: Path,
    dpi: int = 600,
):
    """
    Compact A-C robustness figure:
      A. Reference binary balanced accuracy for full/composition/topology representations
      B. Generator enrichment shift for composition-only representation
      C. Generator enrichment shift for magnetic-topology representation

    B and C share the same symmetric x-range so effect magnitudes are directly comparable.
    Generator colors are identical to canonical Figure 1.
    """
    pivot = _ablation_delta_pivot(generator_ablation)

    all_delta = np.concatenate([
        pd.to_numeric(pivot.get("composition_only"), errors="coerce").to_numpy(float),
        pd.to_numeric(pivot.get("magnetic_topology"), errors="coerce").to_numpy(float),
    ])
    finite = np.abs(all_delta[np.isfinite(all_delta)])
    max_abs = float(finite.max()) if len(finite) else 0.05
    # Round up to an interpretable symmetric axis and leave a little headroom.
    symmetric_limit = max(0.05, np.ceil((max_abs * 1.10) / 0.05) * 0.05)

    fig = plt.figure(figsize=(15.9, 5.2))
    gs = fig.add_gridspec(
        1, 3,
        left=0.075, right=0.985, bottom=0.16, top=0.88,
        wspace=0.43,
        width_ratios=[0.92, 1.08, 1.08],
    )
    axes = [fig.add_subplot(gs[0, i]) for i in range(3)]

    draw_ablation_reference_accuracy(axes[0], reference_ablation)
    draw_ablation_delta(
        axes[1], pivot, "composition_only",
        "Composition-only shift", symmetric_limit
    )
    draw_ablation_delta(
        axes[2], pivot, "magnetic_topology",
        "Magnetic-topology shift", symmetric_limit
    )

    for label, ax in zip("ABC", axes):
        panel_label(ax, label)

    return save_figure(fig, Path(outdir) / "Figure2_representation_robustness", dpi)


# =============================================================================
# Supplementary figures
# =============================================================================

def draw_secondary_metric_barh(ax, summary: pd.DataFrame, value_col: str, title: str, xlabel: str,
                               xlim: tuple[float, float] | None = None, note: str | None = None):
    d = summary.set_index("dataset").reindex([x for x in GENERATOR_ORDER if x in set(summary["dataset"])]).reset_index()
    y = np.arange(len(d))
    vals = pd.to_numeric(d[value_col], errors="coerce").to_numpy(float)
    colors = [GENERATOR_COLORS.get(ds, "#888888") for ds in d["dataset"]]
    ax.barh(y, vals, color=colors, height=0.68, edgecolor="none")
    ax.set_yticks(y)
    ax.set_yticklabels([pretty_dataset(ds) for ds in d["dataset"]])
    ax.invert_yaxis()
    if xlim is not None:
        ax.set_xlim(*xlim)
    ax.set_xlabel(xlabel)
    ax.set_title(title, pad=8)
    style_grid_x(ax)
    if note:
        ax.text(0.98, 0.02, note, transform=ax.transAxes, ha="right", va="bottom", fontsize=7.8, color="#555555")


def build_figureS1_generator_secondary(summary: pd.DataFrame, outdir: Path, dpi: int = 600):
    fig = plt.figure(figsize=(15.2, 9.7))
    gs = fig.add_gridspec(2, 2, left=0.08, right=0.985, bottom=0.09, top=0.95, wspace=0.28, hspace=0.38)
    axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]
    draw_secondary_metric_barh(
        axes[0], summary, "median_dmag",
        "Nearest magnetic-reference distance", r"Median $d_{mag}$"
    )
    draw_secondary_metric_barh(
        axes[1], summary, "median_support_percentile",
        "Magnetic-reference support percentile", "Median support percentile (lower = deeper support)", (0, 100)
    )
    draw_secondary_metric_barh(
        axes[2], summary, "formula_diversity",
        "Formula diversity", "Unique reduced formulas / scored candidates", (0, 1),
        note="CrystALLM is target-conditioned"
    )
    draw_secondary_metric_barh(
        axes[3], summary, "scored_fraction",
        "Scored fraction", "Scored candidates / reference generator set size", (0, 1.02)
    )
    for label, ax in zip("ABCD", axes):
        panel_label(ax, label)
    return save_figure(fig, Path(outdir) / "FigureS1_generator_secondary_metrics", dpi)


def draw_dft_overall(ax, dft_overall: dict[str, float | int]):
    labels = ["Pipeline\nmagnetic-like", "Pipeline\nNM-like"]
    vals = [dft_overall["dft_positive_yield"], dft_overall["dft_negative_yield"]]
    ns = [int(dft_overall["n_pipeline_positive"]), int(dft_overall["n_pipeline_negative"])]
    colors = ["#5F7F57", "#C7CDD3"]
    x = np.arange(2)
    ax.bar(x, vals, color=colors, width=0.62, edgecolor="none")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Fraction confirmed magnetic by DFT")
    ax.set_title("Conditional DFT confirmation", pad=8)
    style_grid_y(ax)
    for xi, v, n in zip(x, vals, ns):
        ax.text(xi, v + 0.025, f"{v:.2f}\n(n={n})", ha="center", va="bottom", fontsize=8.2)


def draw_afmfm_ground_state(ax, afmfm: pd.DataFrame):
    d = afmfm.copy()
    gs = d["ground_state"].astype(str).str.upper().replace({"DEGENERATE": "Degenerate"})
    order = ["AFM", "FM", "Degenerate"]
    pretty = ["AFM", "FM", "Degenerate"]
    vals = [float(gs.eq(o).mean()) for o in order]
    colors = [REFERENCE_COLORS["AFM"], REFERENCE_COLORS["FM"], REFERENCE_COLORS["NM"]]
    x = np.arange(3)
    ax.bar(x, vals, color=colors, width=0.62, edgecolor="none")
    ax.set_xticks(x)
    ax.set_xticklabels(pretty)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Fraction of AFM-like selected candidates")
    ax.set_title("AFM-like candidates: DFT ground state", pad=8)
    style_grid_y(ax)
    n = len(d)
    counts = [int(gs.eq(o).sum()) for o in order]
    for xi, v, c in zip(x, vals, counts):
        ax.text(xi, v + 0.025, f"{c}/{n}", ha="center", va="bottom", fontsize=8.2)


def draw_afmfm_energy(ax, afmfm: pd.DataFrame):
    vals = pd.to_numeric(afmfm["dE_per_atom_meV"], errors="coerce").dropna()
    ax.hist(vals, bins=22, color="#7D8993", edgecolor="white", linewidth=0.8)
    ax.axvline(0, color="#555555", linestyle="--", linewidth=1.0)
    ax.set_xlabel(r"$E_{AFM} - E_{FM}$ (meV atom$^{-1}$)")
    ax.set_ylabel("Count")
    ax.set_title("AFM-vs-FM DFT energy difference", pad=8)
    style_grid_y(ax)
    ax.text(0.02, 0.96, "AFM lower", transform=ax.transAxes, ha="left", va="top", fontsize=8)
    ax.text(0.98, 0.96, "FM lower", transform=ax.transAxes, ha="right", va="top", fontsize=8)


def build_figureS2_dft_details(dft_summary: pd.DataFrame, dft_overall: dict[str, float | int], afmfm: pd.DataFrame | None, outdir: Path, dpi: int = 600):
    fig = plt.figure(figsize=(15.2, 9.8))
    gs = fig.add_gridspec(2, 2, left=0.08, right=0.985, bottom=0.09, top=0.95, wspace=0.30, hspace=0.40)
    axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]
    draw_dft_overall(axes[0], dft_overall)
    draw_dft_confirmation(axes[1], dft_summary)
    if afmfm is not None and len(afmfm):
        draw_afmfm_ground_state(axes[2], afmfm)
        draw_afmfm_energy(axes[3], afmfm)
    else:
        for ax in axes[2:]:
            ax.axis("off")
            ax.text(0.5, 0.5, "AFM/FM limitation data not provided", ha="center", va="center")
    for label, ax in zip("ABCD", axes):
        panel_label(ax, label)
    return save_figure(fig, Path(outdir) / "FigureS2_dft_validation_details", dpi)


def draw_sha_reference_metrics(ax, ref_sens: pd.DataFrame):
    order = ["five_branch_agreement", "magnetic_sensitivity", "nm_specificity", "binary_balanced_accuracy"]
    labels = ["Five-branch agreement", "Magnetic sensitivity", "NM specificity", "Balanced accuracy"]
    d = ref_sens.set_index("metric").reindex(order)
    x = np.arange(len(order))
    width = 0.34
    ax.bar(x - width/2, pd.to_numeric(d["default"], errors="coerce"), width=width, color="#7D8993", label="Default representation")
    ax.bar(x + width/2, pd.to_numeric(d["sha_deduplicated"], errors="coerce"), width=width, color="#4C98D8", label="MAGNDATA SHA dedup")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Score")
    ax.set_title("Reference validation sensitivity", pad=8)
    ax.legend(frameon=False, loc="upper left")
    style_grid_y(ax)


def draw_sha_delta_barh(ax, gen_sens: pd.DataFrame, column: str, title: str, xlabel: str):
    d = gen_sens.set_index("dataset").reindex([x for x in GENERATOR_ORDER if x in set(gen_sens["dataset"])]).reset_index()
    vals = pd.to_numeric(d[column], errors="coerce").to_numpy(float)
    y = np.arange(len(d))
    colors = [GENERATOR_COLORS.get(ds, "#888888") for ds in d["dataset"]]
    lim = max(0.01, float(np.nanmax(np.abs(vals))) * 1.25 if np.isfinite(vals).any() else 0.01)
    ax.barh(y, vals, color=colors, height=0.68, edgecolor="none")
    ax.axvline(0, color="#555555", linewidth=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels([pretty_dataset(ds) for ds in d["dataset"]])
    ax.invert_yaxis()
    ax.set_xlim(-lim, lim)
    ax.set_xlabel(xlabel)
    ax.set_title(title, pad=8)
    style_grid_x(ax)


def draw_sha_dft(ax, dft_sens: pd.DataFrame):
    d = dft_sens.set_index("variant")
    variants = [v for v in ["default", "sha_deduplicated"] if v in d.index]
    x = np.arange(2)
    width = 0.32
    pos = [float(d.loc[v, "p_dft_magnetic_given_pipeline_positive"]) for v in variants]
    neg = [float(d.loc[v, "p_dft_magnetic_given_pipeline_negative"]) for v in variants]
    ax.bar(x - width/2, [pos[0], neg[0]], width=width, color="#7D8993", label="Default representation")
    if len(variants) > 1:
        ax.bar(x + width/2, [pos[1], neg[1]], width=width, color="#4C98D8", label="MAGNDATA SHA dedup")
    ax.set_xticks(x)
    ax.set_xticklabels(["Pipeline\nmagnetic-like", "Pipeline\nNM-like"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Fraction confirmed magnetic by DFT")
    ax.set_title("DFT confirmation sensitivity", pad=8)
    ax.legend(frameon=False, loc="upper left")
    style_grid_y(ax)
    if len(variants) > 1:
        frac = float(d.loc[variants[1], "binary_assignment_fraction_changed_vs_main"])
        ax.text(0.98, 0.02, f"Changed binary assignments: {frac:.3f}", transform=ax.transAxes,
                ha="right", va="bottom", fontsize=7.8, color="#555555")


def build_figureS3_sha_sensitivity(ref_sens: pd.DataFrame, gen_sens: pd.DataFrame, dft_sens: pd.DataFrame, outdir: Path, dpi: int = 600):
    fig = plt.figure(figsize=(15.3, 10.0))
    gs = fig.add_gridspec(2, 2, left=0.08, right=0.985, bottom=0.09, top=0.95, wspace=0.30, hspace=0.42)
    axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]
    draw_sha_reference_metrics(axes[0], ref_sens)
    draw_sha_delta_barh(axes[1], gen_sens, "delta_fmag", "Generator enrichment change after MAGNDATA dedup", r"$\Delta f_{mag}$")
    draw_sha_delta_barh(axes[2], gen_sens, "delta_median_contrast", "Generator contrast change after MAGNDATA dedup", r"$\Delta(d_{NM}-d_{mag})$")
    draw_sha_dft(axes[3], dft_sens)
    for label, ax in zip("ABCD", axes):
        panel_label(ax, label)
    return save_figure(fig, Path(outdir) / "FigureS3_magndata_sha_dedup_sensitivity", dpi)

# =============================================================================
# Publication audit
# =============================================================================

def _assert_close(name: str, got: float, expected: float, atol: float = 5e-4):
    if not np.isfinite(got) or abs(got - expected) > atol:
        raise AssertionError(f"{name}: got {got}, expected {expected} +/- {atol}")


def run_publication_audit(
    bundle: dict[str, object],
    ref_summary: dict[str, object],
    gen_summary: pd.DataFrame,
    dft_summary: pd.DataFrame,
    dft_overall: dict[str, float | int],
    strict: bool,
) -> dict[str, object]:
    ref = bundle["reference"]
    query = bundle["query"]
    dft = bundle["dft"]
    manifest = bundle["feature_manifest"]

    # Structural sanity checks (always enforced).
    require_columns(ref, ["label_order", "nearest_reference_branch"], "reference scores")
    require_columns(query, ["dataset", "is_closer_to_magnetic_reference_than_NM"], "query scores")
    require_columns(dft, ["dataset", "dft_is_magnetic"], "DFT join")

    present_generators = set(gen_summary["dataset"])
    missing_generators = [g for g in GENERATOR_ORDER if g not in present_generators]
    if missing_generators:
        raise AssertionError(f"Generator summary is missing: {missing_generators}")

    present_dft = set(dft_summary["dataset"])
    missing_dft = [g for g in DFT_GENERATOR_ORDER if g not in present_dft]
    if missing_dft:
        raise AssertionError(f"DFT panel is missing datasets: {missing_dft}")

    # Correct scientific meaning of panel G.
    if "dft_magnetic_given_pipeline_positive" not in dft_summary.columns:
        raise AssertionError("DFT panel is not the conditional confirmation P(DFT magnetic | pipeline magnetic-like)")

    if strict:
        if manifest is None:
            raise AssertionError("Strict paper audit requires --feature-manifest")
        if len(manifest) != PAPER_EXPECTED["n_features"]:
            raise AssertionError(f"Feature manifest has {len(manifest)} rows; expected 45")

        if int(ref_summary["n_reference"]) != PAPER_EXPECTED["n_reference"]:
            raise AssertionError(
                f"Reference cohort size {ref_summary['n_reference']} != {PAPER_EXPECTED['n_reference']}"
            )

        _assert_close("five_branch_agreement", ref_summary["five_branch_agreement"], PAPER_EXPECTED["five_branch_agreement"])
        _assert_close("magnetic_sensitivity", ref_summary["magnetic_sensitivity"], PAPER_EXPECTED["magnetic_sensitivity"])
        _assert_close("nm_specificity", ref_summary["nm_specificity"], PAPER_EXPECTED["nm_specificity"])
        _assert_close("balanced_accuracy", ref_summary["balanced_accuracy"], PAPER_EXPECTED["balanced_accuracy"])

        if int(dft_overall["n_dft"]) != PAPER_EXPECTED["dft_n"]:
            raise AssertionError(f"DFT n={dft_overall['n_dft']} != {PAPER_EXPECTED['dft_n']}")
        if int(dft_overall["n_pipeline_positive"]) != PAPER_EXPECTED["dft_n_positive"]:
            raise AssertionError("Unexpected number of pipeline-positive DFT structures")
        if int(dft_overall["n_pipeline_negative"]) != PAPER_EXPECTED["dft_n_negative"]:
            raise AssertionError("Unexpected number of pipeline-negative DFT structures")
        _assert_close("DFT positive yield", dft_overall["dft_positive_yield"], PAPER_EXPECTED["dft_positive_yield"])
        _assert_close("DFT negative yield", dft_overall["dft_negative_yield"], PAPER_EXPECTED["dft_negative_yield"])

        dft_idx = dft_summary.set_index("dataset")
        for ds, expected in PAPER_EXPECTED["dft_positive_by_generator"].items():
            got = float(dft_idx.loc[ds, "dft_magnetic_given_pipeline_positive"])
            _assert_close(f"DFT positive yield {ds}", got, expected)

    return {
        "status": "PASS",
        "strict": bool(strict),
        "n_features": (int(len(manifest)) if manifest is not None else None),
        "n_reference": int(ref_summary["n_reference"]),
        "five_branch_agreement": float(ref_summary["five_branch_agreement"]),
        "magnetic_sensitivity": float(ref_summary["magnetic_sensitivity"]),
        "nm_specificity": float(ref_summary["nm_specificity"]),
        "balanced_accuracy": float(ref_summary["balanced_accuracy"]),
        **{k: (int(v) if isinstance(v, (int, np.integer)) else float(v)) for k, v in dft_overall.items()},
    }


def write_tables(
    outdir: Path,
    ref_summary: dict[str, object],
    gen_summary: pd.DataFrame,
    dft_summary: pd.DataFrame,
    dft_overall: dict[str, float | int],
    audit: dict[str, object],
    reference_ablation: pd.DataFrame | None = None,
    generator_ablation: pd.DataFrame | None = None,
    ablation_audit: dict[str, object] | None = None,
    secondary_summary: pd.DataFrame | None = None,
    afmfm_subset: pd.DataFrame | None = None,
    sha_ref_sens: pd.DataFrame | None = None,
    sha_gen_sens: pd.DataFrame | None = None,
    sha_dft_sens: pd.DataFrame | None = None,
) -> None:
    outdir = Path(outdir)
    tables = outdir / "tables"
    tables.mkdir(parents=True, exist_ok=True)

    ref_summary["confusion_fraction"].to_csv(tables / "figure1_confusion_fraction.csv")
    ref_summary["metrics"].to_csv(tables / "figure1_reference_metrics.csv", index=False)
    gen_summary.to_csv(tables / "figure1DEFG_generator_summary.csv", index=False)
    dft_summary.to_csv(tables / "figure1G_dft_confirmation.csv", index=False)
    pd.DataFrame([dft_overall]).to_csv(tables / "figureS2_dft_overall.csv", index=False)
    (tables / "publication_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    if reference_ablation is not None:
        reference_ablation.to_csv(tables / "figure2A_reference_ablation.csv", index=False)
    if generator_ablation is not None:
        generator_ablation.to_csv(tables / "figure2BC_generator_ablation.csv", index=False)
    if ablation_audit is not None:
        (tables / "figure2_ablation_audit.json").write_text(
            json.dumps(ablation_audit, indent=2), encoding="utf-8"
        )
    if secondary_summary is not None:
        secondary_summary.to_csv(tables / "figureS1_generator_secondary_metrics.csv", index=False)
    if afmfm_subset is not None:
        afmfm_subset.to_csv(tables / "figureS2_afmfm_limitation_subset.csv", index=False)
    if sha_ref_sens is not None:
        sha_ref_sens.to_csv(tables / "figureS3_reference_validation_sensitivity.csv", index=False)
    if sha_gen_sens is not None:
        sha_gen_sens.to_csv(tables / "figureS3_generator_sensitivity.csv", index=False)
    if sha_dft_sens is not None:
        sha_dft_sens.to_csv(tables / "figureS3_dft_sensitivity.csv", index=False)


# =============================================================================
# Main
# =============================================================================

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build and audit final publication figures from canonical 45-feature outputs.")
    p.add_argument("--reference-scores", type=Path, required=True)
    p.add_argument("--query-scores", type=Path, required=True)
    p.add_argument("--dft-join", type=Path, required=True)
    p.add_argument("--feature-manifest", type=Path, default=None)
    p.add_argument("--ablation-reference", type=Path, default=None,
                   help="figure3_ablation_reference_comparison.csv from the canonical model-selection analysis")
    p.add_argument("--ablation-generator", type=Path, default=None,
                   help="figure3_generator_ablation_comparison.csv from the canonical model-selection analysis")
    p.add_argument("--ablation-main-candidate", type=str, default="default")
    p.add_argument("--afmfm-subset", type=Path, default=None,
                   help="afm_fm_subset_rescored_default.csv for the AFM-vs-FM limitation SI figure")
    p.add_argument("--sha-reference-sensitivity", type=Path, default=None,
                   help="reference_validation_sensitivity.csv from MAGNDATA SHA-dedup analysis")
    p.add_argument("--sha-generator-sensitivity", type=Path, default=None,
                   help="generator_benchmark_sensitivity.csv from MAGNDATA SHA-dedup analysis")
    p.add_argument("--sha-dft-sensitivity", type=Path, default=None,
                   help="dft_confirmation_sensitivity.csv from MAGNDATA SHA-dedup analysis")
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--dpi", type=int, default=600)
    p.add_argument("--n-bootstrap", type=int, default=1000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--strict-paper-audit", action="store_true")
    p.add_argument("--write-components", action="store_true",
                   help="Also write separate reference-validation and generator-benchmark component figures")
    p.add_argument("--audit-only", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    configure_style()

    bundle = load_inputs(
        args.reference_scores,
        args.query_scores,
        args.dft_join,
        args.feature_manifest,
    )

    ref = bundle["reference"]
    query = bundle["query"]
    dft = bundle["dft"]

    ref_summary = build_reference_summary(ref)
    gen_summary = build_generator_summary(query, n_bootstrap=args.n_bootstrap, seed=args.seed)
    secondary_summary = build_generator_secondary_summary(query)
    dft_summary, dft_overall = build_dft_summary(dft)
    afmfm_subset = load_afmfm_subset(args.afmfm_subset)
    sha_ref_sens, sha_gen_sens, sha_dft_sens = load_sha_sensitivity_inputs(
        args.sha_reference_sensitivity,
        args.sha_generator_sensitivity,
        args.sha_dft_sensitivity,
    )

    audit = run_publication_audit(
        bundle=bundle,
        ref_summary=ref_summary,
        gen_summary=gen_summary,
        dft_summary=dft_summary,
        dft_overall=dft_overall,
        strict=args.strict_paper_audit,
    )

    reference_ablation = None
    generator_ablation = None
    ablation_audit = None
    if (args.ablation_reference is None) ^ (args.ablation_generator is None):
        raise ValueError("--ablation-reference and --ablation-generator must be provided together")
    if args.ablation_reference is not None:
        reference_ablation, generator_ablation = load_ablation_inputs(
            args.ablation_reference,
            args.ablation_generator,
            main_candidate=args.ablation_main_candidate,
        )
        ablation_audit = audit_ablation_inputs(reference_ablation, generator_ablation)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_tables(
        args.output_dir,
        ref_summary,
        gen_summary,
        dft_summary,
        dft_overall,
        audit,
        reference_ablation=reference_ablation,
        generator_ablation=generator_ablation,
        ablation_audit=ablation_audit,
        secondary_summary=secondary_summary,
        afmfm_subset=afmfm_subset,
        sha_ref_sens=sha_ref_sens,
        sha_gen_sens=sha_gen_sens,
        sha_dft_sens=sha_dft_sens,
    )

    if not args.audit_only:
        # Canonical outputs organized into folders.
        figure1_dir = args.output_dir / "Figure1_rows"
        figure2_dir = args.output_dir / "Figure2"
        supp_dir = args.output_dir / "Supplementary"
        figure1_dir.mkdir(parents=True, exist_ok=True)
        figure2_dir.mkdir(parents=True, exist_ok=True)
        supp_dir.mkdir(parents=True, exist_ok=True)

        build_figure1_row_top(ref, ref_summary, figure1_dir, dpi=args.dpi)
        build_figure1_row_bottom(gen_summary, dft_summary, figure1_dir, dpi=args.dpi)
        if reference_ablation is not None:
            build_figure_ablation(
                reference_ablation, generator_ablation,
                figure2_dir, dpi=args.dpi
            )
        build_figureS1_generator_secondary(secondary_summary, supp_dir, dpi=args.dpi)
        build_figureS2_dft_details(dft_summary, dft_overall, afmfm_subset, supp_dir, dpi=args.dpi)
        if sha_ref_sens is not None:
            build_figureS3_sha_sensitivity(sha_ref_sens, sha_gen_sens, sha_dft_sens, supp_dir, dpi=args.dpi)

        # Optional inspection/component outputs only.
        if args.write_components:
            components_dir = args.output_dir / "components"
            components_dir.mkdir(parents=True, exist_ok=True)
            build_figure1(ref, ref_summary, components_dir, dpi=args.dpi)
            build_figure2(gen_summary, dft_summary, components_dir, dpi=args.dpi)

    print(json.dumps(audit, indent=2))
    if not args.audit_only:
        print(f"Figures written to: {args.output_dir.resolve()}")
        print("Figure 1 row outputs: Figure1_rows/Figure1_row_top_ABC and Figure1_rows/Figure1_row_bottom_DEFG")
        print("Figure 2 output: Figure2/Figure2_representation_robustness")
        print("Supplementary outputs: Supplementary/FigureS1_generator_secondary_metrics, Supplementary/FigureS2_dft_validation_details, and optionally Supplementary/FigureS3_magndata_sha_dedup_sensitivity")


if __name__ == "__main__":
    main()
