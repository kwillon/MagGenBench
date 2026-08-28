from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .figures_v2_magnetic import (
    ANALYSIS_V2_MAGNETIC_INPUT,
    _plot_applicable_box,
    _plot_fraction_panel,
    _read_analysis_v2_dataframe,
    _require_audit_columns,
)
from .plotting_v2 import (
    ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    ANALYSIS_V2_MAGNETIC_COHORT_LABELS,
    ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
    FigureExportPaths,
    apply_analysis_v2_publication_style,
    save_analysis_v2_figure_bundle,
)


FIGURE_BASENAME = "manuscript_figure3_magnetic_domain_v2_preview"

TRANSITION_3D_VARIABLE = "transition_3d_fraction"
LANTHANIDE_VARIABLE = "configured_lanthanide_fraction"
MAGNETIC_NEIGHBOR_VARIABLE = (
    "magnetic_site_magnetic_neighbor_fraction_mean"
)


@dataclass(frozen=True)
class ManuscriptFigure3Report:
    input_csv: Path
    figure_paths: FigureExportPaths


def save_manuscript_figure3(
    df,
    *,
    output_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> FigureExportPaths:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_analysis_v2_publication_style()

    fig = plt.figure(
        figsize=(13.2, 9.0),
        constrained_layout=True,
    )
    fig.patch.set_facecolor("white")

    outer = fig.add_gridspec(
        2,
        2,
        height_ratios=[1.35, 0.78],
        width_ratios=[1.0, 1.0],
    )

    # ------------------------------------------------------------
    # Panel A: 3d transition-metal content
    # ------------------------------------------------------------

    grid_a = outer[0, 0].subgridspec(
        2,
        1,
        height_ratios=[1.0, 1.25],
        hspace=0.07,
    )

    ax_a_top = fig.add_subplot(
        grid_a[0, 0],
    )
    ax_a_bottom = fig.add_subplot(
        grid_a[1, 0],
        sharex=ax_a_top,
    )

    _plot_fraction_panel(
        ax_a_top,
        ax_a_bottom,
        df,
        variable=TRANSITION_3D_VARIABLE,
        title="3d transition-metal content",
        panel="A",
    )

    ax_a_top.tick_params(
        axis="x",
        which="both",
        bottom=False,
        labelbottom=False,
    )

    # ------------------------------------------------------------
    # Panel B: configured lanthanide content
    # ------------------------------------------------------------

    grid_b = outer[0, 1].subgridspec(
        2,
        1,
        height_ratios=[1.0, 1.25],
        hspace=0.07,
    )

    ax_b_top = fig.add_subplot(
        grid_b[0, 0],
    )
    ax_b_bottom = fig.add_subplot(
        grid_b[1, 0],
        sharex=ax_b_top,
    )

    _plot_fraction_panel(
        ax_b_top,
        ax_b_bottom,
        df,
        variable=LANTHANIDE_VARIABLE,
        title="Configured lanthanide content",
        panel="B",
    )

    ax_b_top.tick_params(
        axis="x",
        which="both",
        bottom=False,
        labelbottom=False,
    )

    # ------------------------------------------------------------
    # Panel C: local magnetic-neighbor environment
    # ------------------------------------------------------------

    ax_c = fig.add_subplot(
        outer[1, :],
    )

    _plot_applicable_box(
        ax_c,
        df,
        variable=MAGNETIC_NEIGHBOR_VARIABLE,
        ylabel="Magnetic-neighbor fraction",
        panel="C",
    )

    ax_c.set_xticklabels(
        [
            ANALYSIS_V2_MAGNETIC_COHORT_LABELS[cohort]
            for cohort in ANALYSIS_V2_MAGNETIC_COHORT_ORDER
        ]
    )

    ax_c.set_title(
        "Local magnetic-neighbor environment",
        pad=8,
    )

    paths = save_analysis_v2_figure_bundle(
        fig,
        output_dir,
        FIGURE_BASENAME,
    )

    plt.close(fig)

    return paths


def run_manuscript_figure3(
    input_csv: str | Path = ANALYSIS_V2_MAGNETIC_INPUT,
    figure_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> ManuscriptFigure3Report:
    df = _read_analysis_v2_dataframe(
        input_csv
    )
    _require_audit_columns(df)

    required = (
        TRANSITION_3D_VARIABLE,
        LANTHANIDE_VARIABLE,
        MAGNETIC_NEIGHBOR_VARIABLE,
        "magnetic_geometry_status",
        "analysis_cohort",
    )

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:
        raise RuntimeError(
            "Manuscript Figure 3 input is missing "
            f"required columns: {missing}"
        )

    paths = save_manuscript_figure3(
        df,
        output_dir=figure_dir,
    )

    return ManuscriptFigure3Report(
        input_csv=Path(input_csv),
        figure_paths=paths,
    )
