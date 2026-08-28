from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .figures_v2_magnetic import (
    ANALYSIS_V2_MAGNETIC_INPUT,
)
from .plotting_v2 import (
    ANALYSIS_V2_DARK_TEXT,
    ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    FigureExportPaths,
    apply_analysis_v2_publication_style,
    save_analysis_v2_figure_bundle,
)
from .projections_v2 import (
    build_analysis_v2_pca_spaces,
    _plot_shift_panel,
    _scatter_pca_space,
    _style_pca_axis,
)


FIGURE_BASENAME = "manuscript_figure4_descriptor_space_v2_preview"

ADAPTATION_PAIRS = (
    (
        "mattergen_baseline",
        "mattergen_finetuned",
        "MatterGen adaptation",
    ),
    (
        "concdvae_baseline",
        "concdvae_finetuned",
        "Con-CDVAE adaptation",
    ),
    (
        "crysjepa_base",
        "crysjepa_refined",
        "Crys-JEPA refinement",
    ),
)


@dataclass(frozen=True)
class ManuscriptFigure4Report:
    input_csv: Path
    n_composition_rows: int
    n_magnetic_geometry_rows: int
    figure_paths: FigureExportPaths


def _panel_label(ax, label: str) -> None:
    ax.text(
        -0.10,
        1.06,
        label,
        transform=ax.transAxes,
        fontsize=12,
        fontweight="bold",
        va="top",
        ha="left",
        color=ANALYSIS_V2_DARK_TEXT,
    )


def _remove_shift_annotation_and_legend(ax) -> None:
    legend = ax.get_legend()
    if legend is not None:
        legend.remove()

    for text in list(ax.texts):
        if text.get_text() == "centroid shift":
            text.remove()


def save_manuscript_figure4(
    composition,
    magnetic_geometry,
    *,
    output_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> FigureExportPaths:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_analysis_v2_publication_style()

    fig = plt.figure(
        figsize=(13.4, 8.4),
        constrained_layout=True,
    )
    fig.patch.set_facecolor("white")

    outer = fig.add_gridspec(
        3,
        2,
        height_ratios=[1.0, 0.14, 0.76],
        width_ratios=[1.0, 1.0],
    )

    # ------------------------------------------------------------
    # A. Composition + symmetry PCA
    # ------------------------------------------------------------

    ax_a = fig.add_subplot(
        outer[0, 0],
    )

    _scatter_pca_space(
        ax_a,
        composition,
        title="Composition and symmetry PCA",
    )

    _panel_label(
        ax_a,
        "A",
    )

    # ------------------------------------------------------------
    # B. Magnetic-sublattice geometry PCA
    # ------------------------------------------------------------

    ax_b = fig.add_subplot(
        outer[0, 1],
    )

    _scatter_pca_space(
        ax_b,
        magnetic_geometry,
        title="Magnetic-sublattice geometry PCA",
    )

    _panel_label(
        ax_b,
        "B",
    )

    # ------------------------------------------------------------
    # Shared cohort legend
    # ------------------------------------------------------------

    legend_ax = fig.add_subplot(
        outer[1, :],
    )
    legend_ax.axis("off")

    handles, labels = (
        ax_a.get_legend_handles_labels()
    )

    legend_ax.legend(
        handles,
        labels,
        loc="center",
        ncol=4,
        frameon=False,
        markerscale=1.7,
        columnspacing=1.8,
        handletextpad=0.5,
    )

    # ------------------------------------------------------------
    # C. Adaptation / refinement centroid shifts
    # ------------------------------------------------------------

    shift_grid = outer[2, :].subgridspec(
        1,
        3,
        wspace=0.08,
    )

    shift_axes = [
        fig.add_subplot(
            shift_grid[0, index],
            sharex=None if index == 0 else None,
            sharey=None if index == 0 else None,
        )
        for index in range(3)
    ]

    for index, (
        ax,
        (baseline, adapted, title),
    ) in enumerate(
        zip(
            shift_axes,
            ADAPTATION_PAIRS,
        )
    ):
        _plot_shift_panel(
            ax,
            composition,
            baseline,
            adapted,
        )

        _remove_shift_annotation_and_legend(
            ax
        )

        _style_pca_axis(
            ax,
            composition,
            title=title,
        )

        if index > 0:
            ax.set_ylabel("")

    # All three panels occupy the same PCA coordinate system.
    # Identical limits are required for direct visual comparison.
    composition_xlim = ax_a.get_xlim()
    composition_ylim = ax_a.get_ylim()

    for ax in shift_axes:
        ax.set_xlim(composition_xlim)
        ax.set_ylim(composition_ylim)

    _panel_label(
        shift_axes[0],
        "C",
    )

    paths = save_analysis_v2_figure_bundle(
        fig,
        output_dir,
        FIGURE_BASENAME,
    )

    plt.close(fig)

    return paths


def run_manuscript_figure4(
    input_csv: str | Path = ANALYSIS_V2_MAGNETIC_INPUT,
    figure_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> ManuscriptFigure4Report:
    import pandas as pd

    path = Path(input_csv)

    if not path.is_file():
        raise FileNotFoundError(path)

    df = pd.read_csv(
        path,
        low_memory=False,
    )

    composition, magnetic_geometry = (
        build_analysis_v2_pca_spaces(
            df
        )
    )

    paths = save_manuscript_figure4(
        composition,
        magnetic_geometry,
        output_dir=figure_dir,
    )

    return ManuscriptFigure4Report(
        input_csv=path,
        n_composition_rows=len(
            composition.scores
        ),
        n_magnetic_geometry_rows=len(
            magnetic_geometry.scores
        ),
        figure_paths=paths,
    )
