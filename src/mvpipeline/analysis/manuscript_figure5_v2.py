from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .energy_magnetism_v2 import (
    ADAPTATION_PAIRS,
    _plot_adaptation_panel,
    _plot_all_cohorts,
    _read_analysis_v2,
    prepare_energy_magnetism_dataframe,
)
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


FIGURE_BASENAME = "manuscript_figure5_energy_magnetism_v2_preview"


@dataclass(frozen=True)
class ManuscriptFigure5Report:
    input_csv: Path
    n_total: int
    n_paired: int
    figure_paths: FigureExportPaths


def _panel_label(ax, label: str) -> None:
    ax.text(
        -0.075,
        1.06,
        label,
        transform=ax.transAxes,
        fontsize=12,
        fontweight="bold",
        va="top",
        ha="left",
        color=ANALYSIS_V2_DARK_TEXT,
    )


def _remove_axis_legend(ax) -> None:
    legend = ax.get_legend()

    if legend is not None:
        legend.remove()


def save_manuscript_figure5(
    paired,
    *,
    output_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> FigureExportPaths:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_analysis_v2_publication_style()

    fig = plt.figure(
        figsize=(13.4, 8.5),
        constrained_layout=True,
    )
    fig.patch.set_facecolor("white")

    outer = fig.add_gridspec(
        3,
        3,
        height_ratios=[1.20, 0.13, 0.82],
        width_ratios=[1.0, 1.0, 1.0],
    )

    # ------------------------------------------------------------
    # A. All-cohort energy–magnetism landscape
    # ------------------------------------------------------------

    ax_a = fig.add_subplot(
        outer[0, :],
    )

    _plot_all_cohorts(
        ax_a,
        paired,
    )

    _panel_label(
        ax_a,
        "A",
    )

    handles, labels = (
        ax_a.get_legend_handles_labels()
    )

    _remove_axis_legend(
        ax_a
    )

    ax_a.set_title(
        "Energy–magnetism landscape",
        pad=8,
    )

    # ------------------------------------------------------------
    # Shared cohort legend
    # ------------------------------------------------------------

    legend_ax = fig.add_subplot(
        outer[1, :],
    )
    legend_ax.axis("off")

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
    # B–D. Adaptation / refinement shifts
    # ------------------------------------------------------------

    shift_axes = [
        fig.add_subplot(
            outer[2, index],
            sharex=None if index == 0 else None,
            sharey=None if index == 0 else None,
        )
        for index in range(3)
    ]

    for ax, pair, panel_label in zip(
        shift_axes,
        ADAPTATION_PAIRS,
        ("B", "C", "D"),
    ):
        baseline, adapted, title = pair

        display_title = {
            "MatterGen adaptation": "MatterGen fine-tuning",
            "Con-CDVAE adaptation": "Con-CDVAE fine-tuning",
            "Crys-JEPA refinement": "Crys-JEPA refinement",
        }.get(title, title)

        _plot_adaptation_panel(
            ax,
            paired,
            baseline=baseline,
            adapted=adapted,
            title=display_title,
            panel_label=panel_label,
        )

        _remove_axis_legend(
            ax
        )

    # All lower panels represent the same physical coordinate system.
    # Enforce identical limits for direct visual comparison.
    x_limits = shift_axes[0].get_xlim()

    y_min = min(
        ax.get_ylim()[0]
        for ax in shift_axes
    )
    y_max = max(
        ax.get_ylim()[1]
        for ax in shift_axes
    )

    for index, ax in enumerate(
        shift_axes
    ):
        ax.set_xlim(
            x_limits
        )
        ax.set_ylim(
            y_min,
            y_max,
        )

        if index > 0:
            ax.set_ylabel("")

    shift_axes[0].set_ylabel(
        "DXMag-predicted magnetic moment (μB/f.u.)"
    )

    fig.supxlabel(
        "CHGNet-predicted total energy per atom (eV/atom)",
        fontsize=10,
        color=ANALYSIS_V2_DARK_TEXT,
    )


    paths = save_analysis_v2_figure_bundle(
        fig,
        output_dir,
        FIGURE_BASENAME,
    )

    plt.close(fig)

    return paths


def run_manuscript_figure5(
    input_csv: str | Path = ANALYSIS_V2_MAGNETIC_INPUT,
    figure_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> ManuscriptFigure5Report:
    path = Path(
        input_csv
    )

    if not path.is_file():
        raise FileNotFoundError(
            path
        )

    df = _read_analysis_v2(
        path
    )

    paired = prepare_energy_magnetism_dataframe(
        df
    )

    if paired.empty:
        raise RuntimeError(
            "No paired energy–magnetism rows "
            "available for manuscript Figure 5"
        )

    paths = save_manuscript_figure5(
        paired,
        output_dir=figure_dir,
    )

    return ManuscriptFigure5Report(
        input_csv=path,
        n_total=int(
            len(df)
        ),
        n_paired=int(
            len(paired)
        ),
        figure_paths=paths,
    )
