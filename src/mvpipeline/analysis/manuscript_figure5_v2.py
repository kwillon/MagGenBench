"""Ten-cohort Figure 5 from the frozen publication source; no inference runs."""
from dataclasses import dataclass
from pathlib import Path

from .manuscript_figure3_v2 import COHORT_ORDER
from .plotting_v2 import (
    ANALYSIS_V2_FIGURE_OUTPUT_DIR, FigureExportPaths, save_analysis_v2_figure_bundle,
)

# Figure 5 keeps the historical palette independently of Figure 3's new style.
# The ten-cohort PDF was introduced by d66be85c without its generating code.
HISTORICAL_COLORS = {
    "MatterGen": "#527DA3", "Con-CDVAE": "#47A8A0",
    "CrystalFormer": "#C47B50", "CrystaLLM": "#9A5F69",
    "Crys-JEPA": "#7772A5",
}

FIGURE_BASENAME = "manuscript_figure5_energy_magnetism_v2_preview"
FIGURE_SOURCE = Path("paper/tables/figure_sources/fig05_energy_magnetism.csv")
ENERGY = "energy_total_energy_eV_per_atom"
MOMENT = "magnetism_predicted_moment_value"


@dataclass(frozen=True)
class ManuscriptFigure5Report:
    input_csv: Path
    n_total: int
    n_paired: int
    figure_paths: FigureExportPaths


def load_paired_predictions(path=FIGURE_SOURCE):
    import numpy as np
    import pandas as pd

    df = pd.read_csv(path)
    if set(df.analysis_cohort) != set(COHORT_ORDER):
        raise ValueError("Figure 5 requires exactly the ten publication cohorts")
    if df.duplicated(["analysis_cohort", "sample_uid"]).any():
        raise ValueError("Duplicate prediction identities")
    finite = np.isfinite(df[[ENERGY, MOMENT]].to_numpy(float)).all(axis=1)
    paired = df.loc[finite].copy()
    if Path(path).resolve() == FIGURE_SOURCE.resolve() and len(paired) != 12277:
        raise ValueError(f"Publication source changed: expected 12277 finite pairs, got {len(paired)}")
    return df, paired


def save_manuscript_figure5(paired, *, output_dir=ANALYSIS_V2_FIGURE_OUTPUT_DIR):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    # Restore the pre-6df9c7c8 presentation, without changing the frozen pairs.
    plt.rcdefaults()
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.labelsize": 10, "axes.titlesize": 11,
        "axes.titleweight": "bold", "axes.linewidth": 0.8,
        "xtick.labelsize": 10, "ytick.labelsize": 10,
        "legend.fontsize": 10, "pdf.fonttype": 42, "svg.fonttype": "none",
        "figure.dpi": 160,
    })
    fig = plt.figure(figsize=(16, 13), layout="constrained")
    grid = fig.add_gridspec(3, 6, height_ratios=[1.5, 1, 1])
    axes = [fig.add_subplot(grid[0, :]),
            *[fig.add_subplot(grid[1, 2*i:2*i+2]) for i in range(3)],
            *[fig.add_subplot(grid[2, 3*i:3*i+3]) for i in range(2)]]
    axes[0].set_title("A  Predicted energy–magnetism landscape", loc="left", fontsize=12)
    for index, (name, color) in enumerate(HISTORICAL_COLORS.items()):
        ax = axes[index + 1]
        medians = []
        for version, cohort in enumerate(COHORT_ORDER[2*index:2*index+2]):
            subset = paired.loc[paired.analysis_cohort.eq(cohort)]
            point_style = dict(s=8, color=color,
                       marker="o" if version == 0 else "^",
                       alpha=0.18, linewidths=0, rasterized=True)
            axes[0].scatter(subset[ENERGY], subset[MOMENT], **point_style)
            ax.scatter(subset[ENERGY], subset[MOMENT], **point_style)
            median = subset[[ENERGY, MOMENT]].median().to_numpy()
            medians.append(median)
            # Historical encoding: open Base diamond, filled adapted diamond.
            ax.scatter(*median, s=65, marker="D", zorder=5,
                       facecolor="white" if version == 0 else color,
                       edgecolor=color if version == 0 else "black",
                       linewidth=1.5 if version == 0 else 0.6)
        ax.annotate("", xy=medians[1], xytext=medians[0],
                    arrowprops={"arrowstyle": "->", "color": "black", "lw": 1.8},
                    zorder=4)
        variant = "Refined" if index == 4 else "FT"
        ax.set_title(f"{'BCDEF'[index]}  {name}: Base to {variant}")
    # Restore the historical display window (0.5/99.5 percentiles plus padding).
    # Quantiles set view limits only; all finite records and full group medians
    # are passed to the artists. The audit reports records outside this window.
    xlo, xhi = paired[ENERGY].quantile([0.005, 0.995])
    ylo, yhi = paired[MOMENT].quantile([0.005, 0.995])
    for ax in axes:
        ax.set_xlim(xlo - 0.06*(xhi-xlo), xhi + 0.06*(xhi-xlo))
        ax.set_ylim(ylo - 0.08*(yhi-ylo), yhi + 0.08*(yhi-ylo))
        ax.grid(alpha=0.15, linewidth=0.6)
        ax.set_axisbelow(True)
        ax.set_xlabel("CHGNet total energy (eV/atom)")
        ax.set_ylabel("DXMag moment (μB/f.u.)")
    axes[0].legend(handles=[
        Line2D([], [], marker="o", linestyle="", color=color, label=name)
        for name, color in HISTORICAL_COLORS.items()
    ], loc="upper center", ncol=5, frameon=True)
    paths = save_analysis_v2_figure_bundle(fig, output_dir, FIGURE_BASENAME)
    plt.close(fig)
    return paths


def run_manuscript_figure5(input_csv=FIGURE_SOURCE, figure_dir=ANALYSIS_V2_FIGURE_OUTPUT_DIR):
    df, paired = load_paired_predictions(input_csv)
    paths = save_manuscript_figure5(paired, output_dir=figure_dir)
    return ManuscriptFigure5Report(Path(input_csv), len(df), len(paired), paths)
