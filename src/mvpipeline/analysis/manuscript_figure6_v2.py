from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .compound_classes_v2 import (
    ADAPTATION_PAIRS as COMPOUND_ADAPTATION_PAIRS,
    COMPOUND_CLASS_BASENAMES,
    EXPECTED_ANALYSIS_V2_ROWS as COMPOUND_EXPECTED_ROWS,
    OTHER_CLASS_LABEL,
    TOP_N_COMPOUND_CLASSES,
    _annotate_delta_heatmap,
    _annotate_distribution_heatmap,
    _diverging_compound_class_cmap,
    _format_class_axis,
    _sequential_compound_class_cmap,
    build_compound_class_tables,
)
from .diversity_figures_v2 import (
    ADAPTATION_PAIRS as DIVERSITY_ADAPTATION_PAIRS,
    EXPECTED_ANALYSIS_V2_ROWS as DIVERSITY_EXPECTED_ROWS,
    FIGURE_BASENAME as DIVERSITY_STANDALONE_BASENAME,
    _plot_uniqueness_panel,
    build_diversity_tables,
    load_analysis_v2_diversity_input,
)
from .figures_v2_magnetic import (
    ANALYSIS_V2_MAGNETIC_INPUT,
)
from .plotting_v2 import (
    ANALYSIS_V2_DARK_TEXT,
    ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    ANALYSIS_V2_MAGNETIC_COHORT_LABELS,
    ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
    FigureExportPaths,
    apply_analysis_v2_publication_style,
    save_analysis_v2_figure_bundle,
)


FIGURE_BASENAME = (
    "manuscript_figure6_diversity_adaptation_v2_preview"
)


@dataclass(frozen=True)
class ManuscriptFigure6Report:
    input_csv: Path
    n_rows: int
    class_order: tuple[str, ...]
    figure_paths: FigureExportPaths


def _panel_label(
    ax,
    label: str,
    *,
    x: float = -0.075,
    y: float = 1.06,
) -> None:
    ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        fontsize=12,
        fontweight="bold",
        va="top",
        ha="left",
        color=ANALYSIS_V2_DARK_TEXT,
    )


def _plot_compound_distribution(
    ax,
    distribution,
    class_order: tuple[str, ...],
):
    values = distribution.to_numpy(
        dtype=float
    )
    vmax = float(
        values.max()
    )

    image = ax.imshow(
        values,
        aspect="auto",
        vmin=0.0,
        vmax=vmax,
        cmap=_sequential_compound_class_cmap(),
    )

    # Panel B carries the shared compound-class labels.
    ax.set_xticks(
        range(
            len(class_order)
        )
    )
    ax.set_xticklabels([])
    ax.tick_params(
        axis="x",
        bottom=False,
    )

    ax.set_yticks(
        range(
            len(
                ANALYSIS_V2_MAGNETIC_COHORT_ORDER
            )
        )
    )
    ax.set_yticklabels(
        [
            ANALYSIS_V2_MAGNETIC_COHORT_LABELS[
                cohort
            ].replace("\n", " ")
            for cohort in (
                ANALYSIS_V2_MAGNETIC_COHORT_ORDER
            )
        ]
    )

    ax.set_title(
        "Compound-class distribution across generated sets",
        pad=8,
    )

    _annotate_distribution_heatmap(
        ax,
        distribution,
        vmax=vmax,
    )

    _panel_label(
        ax,
        "A",
    )

    return image


def _plot_compound_shifts(
    ax,
    adaptation_delta,
    class_order: tuple[str, ...],
):
    values = adaptation_delta.to_numpy(
        dtype=float
    )
    vmax = float(
        abs(values).max()
    )

    image = ax.imshow(
        values,
        aspect="auto",
        vmin=-vmax,
        vmax=vmax,
        cmap=_diverging_compound_class_cmap(),
    )

    _format_class_axis(
        ax,
        class_order,
    )

    ax.set_yticks(
        range(
            len(
                adaptation_delta.index
            )
        )
    )
    ax.set_yticklabels(
        adaptation_delta.index
    )

    ax.set_title(
        "Fine-tuning and refinement shifts in compound classes",
        pad=8,
    )

    _annotate_delta_heatmap(
        ax,
        adaptation_delta,
        vmax=vmax,
    )

    _panel_label(
        ax,
        "B",
    )

    return image


def save_manuscript_figure6(
    class_order,
    distribution,
    adaptation_delta,
    diversity_summary,
    *,
    output_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> FigureExportPaths:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_analysis_v2_publication_style()

    fig = plt.figure(
        figsize=(13.8, 10.2),
        constrained_layout=True,
    )
    fig.patch.set_facecolor(
        "white"
    )

    outer = fig.add_gridspec(
        3,
        2,
        height_ratios=[
            1.12,
            0.72,
            1.12,
        ],
        width_ratios=[
            1.0,
            1.0,
        ],
    )

    # ------------------------------------------------------------
    # A. Compound-class distribution
    # ------------------------------------------------------------

    ax_a = fig.add_subplot(
        outer[0, :],
    )

    image_a = _plot_compound_distribution(
        ax_a,
        distribution,
        class_order,
    )

    cbar_a = fig.colorbar(
        image_a,
        ax=ax_a,
        pad=0.012,
        fraction=0.022,
    )
    cbar_a.set_label(
        "Share within generated set (%)"
    )

    # ------------------------------------------------------------
    # B. Fine-tuning / refinement shifts
    # ------------------------------------------------------------

    ax_b = fig.add_subplot(
        outer[1, :],
    )

    manuscript_delta = adaptation_delta.copy()
    manuscript_delta.index = (
        "MatterGen\nFine-tuned − Base",
        "Con-CDVAE\nFine-tuned − Base",
        "Crys-JEPA\nRefined − Base",
    )

    image_b = _plot_compound_shifts(
        ax_b,
        manuscript_delta,
        class_order,
    )

    cbar_b = fig.colorbar(
        image_b,
        ax=ax_b,
        pad=0.012,
        fraction=0.022,
    )
    cbar_b.set_label(
        "Change from baseline (percentage points)"
    )

    # ------------------------------------------------------------
    # C–D. Chemical / crystallographic uniqueness
    # ------------------------------------------------------------

    ax_c = fig.add_subplot(
        outer[2, 0],
    )

    ax_d = fig.add_subplot(
        outer[2, 1],
        sharey=ax_c,
    )

    _plot_uniqueness_panel(
        ax_c,
        diversity_summary,
        metric="unique_formula_percent",
        count_column="n_unique_formula",
        title="Unique reduced formulas",
        xlabel="Unique reduced formulas (%)",
        panel_label="C",
        show_ylabels=True,
    )

    _plot_uniqueness_panel(
        ax_d,
        diversity_summary,
        metric="unique_formula_sg_percent",
        count_column="n_unique_formula_sg",
        title="Unique formula–space-group pairs",
        xlabel="Unique formula–space-group pairs (%)",
        panel_label="D",
        show_ylabels=False,
    )

    # Shared y-axis: invert exactly once.
    ax_c.invert_yaxis()

    paths = save_analysis_v2_figure_bundle(
        fig,
        output_dir,
        FIGURE_BASENAME,
    )

    plt.close(
        fig
    )

    return paths


def run_manuscript_figure6(
    input_csv: str | Path = ANALYSIS_V2_MAGNETIC_INPUT,
    figure_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> ManuscriptFigure6Report:
    path = Path(
        input_csv
    )

    # This validates row count, cohorts, formulas,
    # and recomputed space groups.
    df = load_analysis_v2_diversity_input(
        path
    )

    class_order, distribution, adaptation_delta = (
        build_compound_class_tables(
            df
        )
    )

    diversity_summary, _ = (
        build_diversity_tables(
            df
        )
    )

    paths = save_manuscript_figure6(
        class_order,
        distribution,
        adaptation_delta,
        diversity_summary,
        output_dir=figure_dir,
    )

    return ManuscriptFigure6Report(
        input_csv=path,
        n_rows=int(
            len(df)
        ),
        class_order=class_order,
        figure_paths=paths,
    )
