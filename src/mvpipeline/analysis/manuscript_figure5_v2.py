"""Ten-cohort Figure 5 from the frozen publication source; no inference runs."""
from dataclasses import dataclass
from pathlib import Path

from .manuscript_figure3_v2 import COHORT_ORDER
from .plotting_v2 import (
    ANALYSIS_V2_FIGURE_OUTPUT_DIR, FigureExportPaths, save_analysis_v2_figure_bundle,
)
from .publication_style import GENERATOR_COLORS, apply_publication_style

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

    apply_publication_style()
    fig, axes = plt.subplots(2, 3, figsize=(10, 7.4), layout="constrained",
                             sharex=True, sharey=True)
    axes = axes.ravel()
    ax = axes[0]
    density = ax.hexbin(paired[ENERGY], paired[MOMENT], gridsize=55,
                        bins="log", mincnt=1, cmap="Greys", linewidths=0)
    fig.colorbar(density, ax=ax, location="top", fraction=0.08, pad=0.03,
                 label="Structures per hexagon (log scale)")
    ax.set_title(f"A   Pooled distribution (n = {len(paired):,})", loc="left")
    for index, (name, color) in enumerate(GENERATOR_COLORS.items()):
        ax = axes[index + 1]
        medians = []
        for version, cohort in enumerate(COHORT_ORDER[2*index:2*index+2]):
            subset = paired.loc[paired.analysis_cohort.eq(cohort)]
            ax.scatter(subset[ENERGY], subset[MOMENT], s=9, color=color,
                       marker="o" if version == 0 else "^",
                       alpha=0.22 if version == 0 else 0.4, linewidths=0,
                       rasterized=True)
            median = subset[[ENERGY, MOMENT]].median().to_numpy()
            medians.append(median)
            ax.scatter(*median, s=65, marker="D", zorder=5,
                       facecolor=color if version == 0 else "white",
                       edgecolor="#23324F", linewidth=1.1)
        ax.annotate("", xy=medians[1], xytext=medians[0],
                    arrowprops={"arrowstyle": "->", "color": "#23324F", "lw": 1.5},
                    zorder=4)
        ax.set_title(f"{'BCDEF'[index]}   {name}", loc="left")
    for ax in axes:
        ax.margins(x=0.03, y=0.05)
        ax.grid(alpha=0.25)
        ax.set_axisbelow(True)
        ax.tick_params(labelbottom=True, labelleft=True)
    fig.supxlabel("CHGNet-predicted total energy per atom (eV/atom)")
    fig.supylabel(r"DXMag-predicted magnetic moment ($\mu_B$/f.u.)")
    fig.legend(handles=[
        Line2D([], [], marker="o", linestyle="", color="#64717B", label="Base points"),
        Line2D([], [], marker="^", linestyle="", color="#64717B", label="Adapted points"),
        Line2D([], [], marker="D", linestyle="", color="#23324F", label="Base median"),
        Line2D([], [], marker="D", linestyle="", color="#23324F", markerfacecolor="white",
               label="Adapted median"),
    ], loc="outside upper right", ncol=4, frameon=False, fontsize=10)
    paths = save_analysis_v2_figure_bundle(fig, output_dir, FIGURE_BASENAME)
    plt.close(fig)
    return paths


def run_manuscript_figure5(input_csv=FIGURE_SOURCE, figure_dir=ANALYSIS_V2_FIGURE_OUTPUT_DIR):
    df, paired = load_paired_predictions(input_csv)
    paths = save_manuscript_figure5(paired, output_dir=figure_dir)
    return ManuscriptFigure5Report(Path(input_csv), len(df), len(paired), paths)
