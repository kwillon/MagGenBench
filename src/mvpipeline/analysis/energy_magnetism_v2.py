from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .figures_v2_magnetic import ANALYSIS_V2_MAGNETIC_INPUT
from .plotting_v2 import (
    ANALYSIS_V2_DARK_TEXT,
    ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    ANALYSIS_V2_MAGNETIC_COHORT_COLORS,
    ANALYSIS_V2_MAGNETIC_COHORT_LABELS,
    ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
    FigureExportPaths,
    apply_analysis_v2_publication_style,
    save_analysis_v2_figure_bundle,
)


ENERGY_COLUMN = "energy_total_energy_eV_per_atom"
MOMENT_COLUMN = "magnetism_predicted_moment_value"

EXPECTED_ANALYSIS_V2_ROWS = 10684
EXPECTED_PAIRED_ROWS = 10680

ENERGY_MAGNETISM_BASENAMES = (
    "09_energy_moment_landscape_v2",
    "10_energy_moment_adaptation_v2",
)

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
class EnergyMagnetismReport:
    input_csv: Path
    output_dir: Path
    n_total: int
    n_paired: int
    summary: object
    figure_paths: tuple[FigureExportPaths, ...]


def _read_analysis_v2(input_csv: str | Path):
    import pandas as pd

    path = Path(input_csv)
    if not path.is_file():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def _require_columns(df) -> None:
    required = {
        "analysis_cohort",
        "structure_id",
        "sample_uid",
        "energy_status",
        "magnetism_status",
        ENERGY_COLUMN,
        MOMENT_COLUMN,
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise RuntimeError(
            f"Analysis v2 input missing energy-magnetism columns: {missing}"
        )


def prepare_energy_magnetism_dataframe(
    df,
    *,
    expected_total_rows: int | None = EXPECTED_ANALYSIS_V2_ROWS,
    expected_paired_rows: int | None = EXPECTED_PAIRED_ROWS,
):
    import numpy as np
    import pandas as pd

    _require_columns(df)

    if expected_total_rows is not None and len(df) != expected_total_rows:
        raise RuntimeError(
            f"Expected {expected_total_rows} Analysis v2 rows, found {len(df)}"
        )

    work = df.loc[
        :,
        [
            "structure_id",
            "sample_uid",
            "analysis_cohort",
            "energy_status",
            "magnetism_status",
            ENERGY_COLUMN,
            MOMENT_COLUMN,
        ],
    ].copy()

    work[ENERGY_COLUMN] = pd.to_numeric(work[ENERGY_COLUMN], errors="coerce")
    work[MOMENT_COLUMN] = pd.to_numeric(work[MOMENT_COLUMN], errors="coerce")

    energy = work[ENERGY_COLUMN].to_numpy(dtype=float)
    moment = work[MOMENT_COLUMN].to_numpy(dtype=float)
    finite = np.isfinite(energy) & np.isfinite(moment)

    paired = work.loc[finite].copy()

    if expected_paired_rows is not None and len(paired) != expected_paired_rows:
        raise RuntimeError(
            f"Expected {expected_paired_rows} paired energy-moment rows, "
            f"found {len(paired)}"
        )

    unknown_cohorts = sorted(
        set(paired["analysis_cohort"].astype(str)).difference(
            ANALYSIS_V2_MAGNETIC_COHORT_ORDER
        )
    )
    if unknown_cohorts:
        raise RuntimeError(
            f"Unexpected Analysis v2 cohorts: {unknown_cohorts}"
        )

    missing_cohorts = [
        cohort
        for cohort in ANALYSIS_V2_MAGNETIC_COHORT_ORDER
        if not paired["analysis_cohort"].astype(str).eq(cohort).any()
    ]
    if missing_cohorts:
        raise RuntimeError(
            f"Paired energy-moment data missing cohorts: {missing_cohorts}"
        )

    return paired


def summarize_energy_magnetism(paired):
    import pandas as pd

    records = []

    for cohort in ANALYSIS_V2_MAGNETIC_COHORT_ORDER:
        subset = paired[paired["analysis_cohort"] == cohort]
        x = subset[ENERGY_COLUMN]
        y = subset[MOMENT_COLUMN]

        correlation = subset[[ENERGY_COLUMN, MOMENT_COLUMN]]

        records.append(
            {
                "analysis_cohort": cohort,
                "cohort_label": ANALYSIS_V2_MAGNETIC_COHORT_LABELS[
                    cohort
                ].replace("\n", " "),
                "n": int(len(subset)),
                "energy_mean_eV_per_atom": float(x.mean()),
                "energy_median_eV_per_atom": float(x.median()),
                "energy_q01_eV_per_atom": float(x.quantile(0.01)),
                "energy_q99_eV_per_atom": float(x.quantile(0.99)),
                "moment_mean": float(y.mean()),
                "moment_median": float(y.median()),
                "moment_q01": float(y.quantile(0.01)),
                "moment_q99": float(y.quantile(0.99)),
                "pearson_r": float(
                    correlation.corr(method="pearson").iloc[0, 1]
                ),
                "spearman_rho": float(
                    correlation.corr(method="spearman").iloc[0, 1]
                ),
            }
        )

    return pd.DataFrame.from_records(records)


def _new_figure(figsize: tuple[float, float]):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_analysis_v2_publication_style()
    fig = plt.figure(figsize=figsize, constrained_layout=True)
    fig.patch.set_facecolor("white")
    return fig


def _style_energy_moment_axis(ax) -> None:
    ax.axhline(0, color="#D5D5D5", linewidth=0.6, zorder=0)
    ax.grid(color="#D5D5D5", linewidth=0.45, alpha=0.45)
    ax.set_axisbelow(True)
    ax.set_xlabel("CHGNet-predicted total energy per atom (eV/atom)")
    ax.set_ylabel("DXMag-predicted magnetic moment (μB/f.u.)")


def _cohort_median_point(subset) -> tuple[float, float]:
    return (
        float(subset[ENERGY_COLUMN].median()),
        float(subset[MOMENT_COLUMN].median()),
    )


def _robust_energy_limits(paired) -> tuple[float, float]:
    lower = float(paired[ENERGY_COLUMN].quantile(0.01))
    upper = float(paired[ENERGY_COLUMN].quantile(0.99))
    span = upper - lower
    padding = 0.02 * span
    return lower - padding, upper + padding


def _plot_all_cohorts(ax, paired) -> None:
    for cohort in ANALYSIS_V2_MAGNETIC_COHORT_ORDER:
        subset = paired[paired["analysis_cohort"] == cohort]
        color = ANALYSIS_V2_MAGNETIC_COHORT_COLORS[cohort]
        label = ANALYSIS_V2_MAGNETIC_COHORT_LABELS[cohort].replace("\n", " ")

        ax.scatter(
            subset[ENERGY_COLUMN],
            subset[MOMENT_COLUMN],
            s=8,
            alpha=0.20,
            color=color,
            linewidths=0,
            rasterized=True,
            label=label,
        )

        median_point = _cohort_median_point(subset)
        ax.scatter(
            [median_point[0]],
            [median_point[1]],
            s=72,
            marker="D",
            color=color,
            edgecolor=ANALYSIS_V2_DARK_TEXT,
            linewidth=0.8,
            zorder=5,
        )

    _style_energy_moment_axis(ax)
    ax.set_xlim(*_robust_energy_limits(paired))
    ax.set_title("Energy–magnetism landscape across generated sets", pad=7)
    ax.legend(
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=False,
        borderaxespad=0.0,
        markerscale=1.7,
    )


def _plot_adaptation_panel(
    ax,
    paired,
    *,
    baseline: str,
    adapted: str,
    title: str,
    panel_label: str,
) -> None:
    median_points = {}

    for cohort in (baseline, adapted):
        subset = paired[paired["analysis_cohort"] == cohort]
        color = ANALYSIS_V2_MAGNETIC_COHORT_COLORS[cohort]
        label = ANALYSIS_V2_MAGNETIC_COHORT_LABELS[cohort].replace("\n", " ")

        ax.scatter(
            subset[ENERGY_COLUMN],
            subset[MOMENT_COLUMN],
            s=8,
            alpha=0.22,
            color=color,
            linewidths=0,
            rasterized=True,
            label=label,
        )

        median_point = _cohort_median_point(subset)
        median_points[cohort] = median_point

        ax.scatter(
            [median_point[0]],
            [median_point[1]],
            s=78,
            marker="D",
            color=color,
            edgecolor=ANALYSIS_V2_DARK_TEXT,
            linewidth=0.8,
            zorder=5,
        )

    start = median_points[baseline]
    end = median_points[adapted]

    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops={
            "arrowstyle": "->",
            "color": ANALYSIS_V2_DARK_TEXT,
            "linewidth": 1.3,
            "shrinkA": 8,
            "shrinkB": 8,
        },
        zorder=4,
    )

    ax.set_title(title, pad=7)
    ax.text(
        -0.08,
        1.05,
        panel_label,
        transform=ax.transAxes,
        fontsize=12,
        fontweight="bold",
        va="top",
        ha="left",
    )
    ax.grid(color="#D5D5D5", linewidth=0.45, alpha=0.45)
    ax.axhline(0, color="#D5D5D5", linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xlim(*_robust_energy_limits(paired))
    ax.legend(frameon=False, loc="best")


def save_energy_moment_landscape(
    paired,
    *,
    output_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> FigureExportPaths:
    import matplotlib.pyplot as plt

    fig = _new_figure((8.0, 6.0))
    ax = fig.add_subplot(1, 1, 1)
    _plot_all_cohorts(ax, paired)

    paths = save_analysis_v2_figure_bundle(
        fig,
        output_dir,
        ENERGY_MAGNETISM_BASENAMES[0],
    )
    plt.close(fig)
    return paths


def save_energy_moment_adaptation(
    paired,
    *,
    output_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> FigureExportPaths:
    import matplotlib.pyplot as plt

    fig = _new_figure((12.2, 4.2))
    axes = fig.subplots(1, 3, sharex=True, sharey=True)

    for ax, pair, panel_label in zip(
        axes,
        ADAPTATION_PAIRS,
        ("A", "B", "C"),
    ):
        baseline, adapted, title = pair
        _plot_adaptation_panel(
            ax,
            paired,
            baseline=baseline,
            adapted=adapted,
            title=title,
            panel_label=panel_label,
        )

    fig.supxlabel("CHGNet-predicted total energy per atom (eV/atom)")
    fig.supylabel("DXMag-predicted magnetic moment (μB/f.u.)")

    paths = save_analysis_v2_figure_bundle(
        fig,
        output_dir,
        ENERGY_MAGNETISM_BASENAMES[1],
    )
    plt.close(fig)
    return paths


def run_analysis_v2_energy_magnetism(
    input_csv: str | Path = ANALYSIS_V2_MAGNETIC_INPUT,
    output_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> EnergyMagnetismReport:
    df = _read_analysis_v2(input_csv)
    paired = prepare_energy_magnetism_dataframe(df)
    summary = summarize_energy_magnetism(paired)

    figure_paths = (
        save_energy_moment_landscape(paired, output_dir=output_dir),
        save_energy_moment_adaptation(paired, output_dir=output_dir),
    )

    return EnergyMagnetismReport(
        input_csv=Path(input_csv),
        output_dir=Path(output_dir),
        n_total=int(len(df)),
        n_paired=int(len(paired)),
        summary=summary,
        figure_paths=figure_paths,
    )
