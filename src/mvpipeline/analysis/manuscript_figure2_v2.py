from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .figures_v2_magnetic import (
    ANALYSIS_V2_MAGNETIC_INPUT,
    _read_analysis_v2_dataframe,
)
from .plotting_v2 import (
    ANALYSIS_V2_DARK_TEXT,
    ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    ANALYSIS_V2_MAGNETIC_COHORT_COLORS,
    ANALYSIS_V2_MAGNETIC_COHORT_LABELS,
    ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
    ANALYSIS_V2_OVERVIEW_CREAM,
    FigureExportPaths,
    apply_analysis_v2_publication_style,
    save_analysis_v2_figure_bundle,
)
from .validation_figures_v2 import (
    MODEL_COLORS,
    MODEL_ORDER,
    REJECTION_REASON_LABELS,
    REJECTION_REASON_ORDER,
    VALIDATION_INPUT,
    build_validation_tables,
    read_ragged_validation_records,
)


FIGURE_BASENAME = "manuscript_figure2_structural_overview_v2_preview"

CRYSJEPA_BASE_VALIDATION_INPUT = Path(
    "tables/03_features/crysjepa_base_with_classes.csv"
)

BASELINE_DISPLAY_ORDER = (
    "MatterGen",
    "Con-CDVAE",
    "CrystalFormer",
    "CrystaLLM",
    "Crys-JEPA",
)

BASELINE_DISPLAY_COLORS = {
    **MODEL_COLORS,
    "Crys-JEPA": ANALYSIS_V2_MAGNETIC_COHORT_COLORS["crysjepa_base"],
}


@dataclass(frozen=True)
class ManuscriptFigure2Report:
    analysis_input_csv: Path
    validation_input_csv: Path
    analysis_counts: object
    validation_summary: object
    rejection_summary: object
    figure_paths: FigureExportPaths


def _panel_label(ax, label: str) -> None:
    ax.text(
        -0.075,
        1.07,
        label,
        transform=ax.transAxes,
        fontsize=12,
        fontweight="bold",
        va="top",
        ha="left",
        color=ANALYSIS_V2_DARK_TEXT,
    )


def build_analysis_cohort_counts(df):
    import pandas as pd

    if "analysis_cohort" not in df.columns:
        raise RuntimeError(
            "Analysis v2 input is missing analysis_cohort"
        )

    observed = set(
        df["analysis_cohort"]
        .dropna()
        .astype(str)
    )
    expected = set(ANALYSIS_V2_MAGNETIC_COHORT_ORDER)

    if observed != expected:
        raise RuntimeError(
            "Analysis v2 cohort set differs from manuscript Figure 2 "
            f"contract: observed={sorted(observed)}"
        )

    counts = (
        df["analysis_cohort"]
        .value_counts()
        .reindex(ANALYSIS_V2_MAGNETIC_COHORT_ORDER)
        .astype(int)
    )

    if counts.isna().any():
        raise RuntimeError(
            "Analysis v2 cohort counts contain missing values"
        )

    return pd.Series(
        counts.to_numpy(dtype=int),
        index=counts.index,
        name="n_structures",
    )


def _plot_analysis_cohort_sizes(ax, counts) -> None:
    cohorts = list(ANALYSIS_V2_MAGNETIC_COHORT_ORDER)
    x = list(range(len(cohorts)))

    values = [
        int(counts.loc[cohort])
        for cohort in cohorts
    ]

    colors = [
        ANALYSIS_V2_MAGNETIC_COHORT_COLORS[cohort]
        for cohort in cohorts
    ]

    bars = ax.bar(
        x,
        values,
        color=colors,
        edgecolor=ANALYSIS_V2_DARK_TEXT,
        linewidth=0.5,
        width=0.72,
    )

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value}",
            ha="center",
            va="bottom",
            fontsize=7.5,
            color=ANALYSIS_V2_DARK_TEXT,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(
        [
            ANALYSIS_V2_MAGNETIC_COHORT_LABELS[cohort]
            for cohort in cohorts
        ]
    )

    ax.tick_params(axis="x", pad=5)

    ax.set_ylabel("Structures")
    ax.set_title(
        "Number of structures retained for analysis",
        pad=8,
    )

    ax.set_ylim(
        0,
        max(values) * 1.16,
    )

    ax.grid(
        axis="y",
        color="#D5D5D5",
        linewidth=0.45,
        alpha=0.55,
    )
    ax.set_axisbelow(True)

    _panel_label(ax, "A")


def _plot_validation_outcome(ax, model_summary) -> None:
    y = list(range(len(BASELINE_DISPLAY_ORDER)))

    ax.barh(
        y,
        [100.0] * len(BASELINE_DISPLAY_ORDER),
        color="#EEEAE2",
        edgecolor="none",
        height=0.60,
        zorder=1,
    )

    for index, model in enumerate(BASELINE_DISPLAY_ORDER):
        value = float(
            model_summary.loc[
                model,
                "validated_percent",
            ]
        )
        n_validated = int(
            model_summary.loc[
                model,
                "n_validated",
            ]
        )
        n_total = int(
            model_summary.loc[
                model,
                "n_total",
            ]
        )

        ax.barh(
            index,
            value,
            color=BASELINE_DISPLAY_COLORS[model],
            edgecolor=ANALYSIS_V2_DARK_TEXT,
            linewidth=0.55,
            height=0.60,
            zorder=2,
        )

        ax.text(
            min(value + 1.5, 97.0),
            index,
            f"{n_validated}/{n_total} ({value:.1f}%)",
            va="center",
            ha="left" if value < 85 else "right",
            fontsize=7.5,
            color=ANALYSIS_V2_DARK_TEXT,
            zorder=3,
        )

    ax.set_yticks(y)
    ax.set_yticklabels(BASELINE_DISPLAY_ORDER)
    ax.invert_yaxis()

    ax.set_xlim(0, 100)
    ax.set_xlabel("Validated structures (%)")

    ax.set_title(
        "Base generated sets: structural validation",
        pad=8,
    )

    ax.grid(
        axis="x",
        color="#D5D5D5",
        linewidth=0.45,
        alpha=0.50,
    )
    ax.set_axisbelow(True)

    _panel_label(ax, "B")


def _rejection_cmap():
    from matplotlib.colors import LinearSegmentedColormap

    return LinearSegmentedColormap.from_list(
        "manuscript_figure2_rejection",
        [
            "#FFFFFF",
            ANALYSIS_V2_OVERVIEW_CREAM,
            "#829DA6",
            "#304862",
        ],
    )


def _plot_rejection_profile(ax, rejection_summary) -> None:
    import numpy as np

    values = rejection_summary.to_numpy(dtype=float)
    vmax = float(values.max())

    image = ax.imshow(
        values,
        aspect="auto",
        vmin=0.0,
        vmax=vmax,
        cmap=_rejection_cmap(),
    )

    ax.set_xticks(
        range(len(REJECTION_REASON_ORDER))
    )
    ax.set_xticklabels(
        [
            REJECTION_REASON_LABELS[key]
            for key in REJECTION_REASON_ORDER
        ]
    )

    ax.set_yticks(
        range(len(BASELINE_DISPLAY_ORDER))
    )
    ax.set_yticklabels(BASELINE_DISPLAY_ORDER)

    ax.set_title(
        "Base generated sets: rejection profile",
        pad=8,
    )

    threshold = 0.52 * vmax

    for row_index in range(values.shape[0]):
        for column_index in range(values.shape[1]):
            value = float(
                values[
                    row_index,
                    column_index,
                ]
            )

            if abs(value) < 0.05:
                continue

            text_color = (
                "white"
                if value >= threshold
                else ANALYSIS_V2_DARK_TEXT
            )

            ax.text(
                column_index,
                row_index,
                f"{value:.1f}",
                ha="center",
                va="center",
                fontsize=7.4,
                color=text_color,
            )

    cbar = ax.figure.colorbar(
        image,
        ax=ax,
        pad=0.020,
        fraction=0.035,
    )
    cbar.set_label(
        "Share among rejected structures (%)"
    )

    _panel_label(ax, "C")


def _extend_with_crysjepa_base(
    validation_summary,
    rejection_summary,
    *,
    input_csv: str | Path = CRYSJEPA_BASE_VALIDATION_INPUT,
):
    import pandas as pd

    path = Path(input_csv)
    if not path.is_file():
        raise FileNotFoundError(path)

    df = pd.read_csv(path, low_memory=False)

    required = {"status", "rejection_reason"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise RuntimeError(
            f"Crys-JEPA Base validation table is missing columns: {missing}"
        )

    status = (
        df["status"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )
    reasons = (
        df["rejection_reason"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    n_total = int(len(df))
    n_validated = int(status.eq("validated").sum())
    n_rejected = int(status.eq("rejected").sum())

    if n_total != 2000:
        raise RuntimeError(
            f"Expected 2000 Crys-JEPA Base structures, found {n_total}"
        )

    if n_validated + n_rejected != n_total:
        raise RuntimeError(
            "Crys-JEPA Base validation statuses do not cover all rows"
        )

    summary = validation_summary.copy()
    summary.loc["Crys-JEPA", "n_total"] = n_total
    summary.loc["Crys-JEPA", "n_validated"] = n_validated
    summary.loc["Crys-JEPA", "n_rejected"] = n_rejected
    summary.loc["Crys-JEPA", "validated_percent"] = (
        100.0 * n_validated / n_total
    )
    summary.loc["Crys-JEPA", "rejected_percent"] = (
        100.0 * n_rejected / n_total
    )
    summary = summary.reindex(BASELINE_DISPLAY_ORDER)

    rejection = rejection_summary.copy()

    if n_rejected:
        rejection.loc["Crys-JEPA"] = [
            100.0 * int(reasons.eq(reason).sum()) / n_rejected
            for reason in REJECTION_REASON_ORDER
        ]
    else:
        rejection.loc["Crys-JEPA"] = [0.0] * len(REJECTION_REASON_ORDER)

    rejection = rejection.reindex(
        index=BASELINE_DISPLAY_ORDER,
        columns=REJECTION_REASON_ORDER,
    )

    if abs(float(rejection.loc["Crys-JEPA"].sum()) - 100.0) > 1e-8:
        raise RuntimeError(
            "Crys-JEPA Base rejection profile does not sum to 100%"
        )

    return summary, rejection


def save_manuscript_figure2(
    analysis_counts,
    validation_summary,
    rejection_summary,
    *,
    output_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> FigureExportPaths:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_analysis_v2_publication_style()

    fig = plt.figure(
        figsize=(13.2, 8.0),
        constrained_layout=True,
    )
    fig.patch.set_facecolor("white")

    grid = fig.add_gridspec(
        2,
        2,
        height_ratios=[0.72, 1.0],
        width_ratios=[0.90, 1.30],
    )

    ax_a = fig.add_subplot(
        grid[0, :],
    )
    ax_b = fig.add_subplot(
        grid[1, 0],
    )
    ax_c = fig.add_subplot(
        grid[1, 1],
    )

    _plot_analysis_cohort_sizes(
        ax_a,
        analysis_counts,
    )
    _plot_validation_outcome(
        ax_b,
        validation_summary,
    )
    _plot_rejection_profile(
        ax_c,
        rejection_summary,
    )

    paths = save_analysis_v2_figure_bundle(
        fig,
        output_dir,
        FIGURE_BASENAME,
    )

    plt.close(fig)

    return paths


def run_manuscript_figure2(
    analysis_input_csv: str | Path = ANALYSIS_V2_MAGNETIC_INPUT,
    validation_input_csv: str | Path = VALIDATION_INPUT,
    figure_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> ManuscriptFigure2Report:
    analysis_df = _read_analysis_v2_dataframe(
        analysis_input_csv
    )
    analysis_counts = build_analysis_cohort_counts(
        analysis_df
    )

    validation_records = read_ragged_validation_records(
        validation_input_csv
    )
    validation_summary, rejection_summary = (
        build_validation_tables(
            validation_records
        )
    )

    validation_summary, rejection_summary = (
        _extend_with_crysjepa_base(
            validation_summary,
            rejection_summary,
        )
    )

    paths = save_manuscript_figure2(
        analysis_counts,
        validation_summary,
        rejection_summary,
        output_dir=figure_dir,
    )

    return ManuscriptFigure2Report(
        analysis_input_csv=Path(
            analysis_input_csv
        ),
        validation_input_csv=Path(
            validation_input_csv
        ),
        analysis_counts=analysis_counts,
        validation_summary=validation_summary,
        rejection_summary=rejection_summary,
        figure_paths=paths,
    )
