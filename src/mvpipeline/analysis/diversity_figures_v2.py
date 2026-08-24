from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .figures_v2_magnetic import ANALYSIS_V2_MAGNETIC_INPUT
from .plotting_v2 import (
    ANALYSIS_V2_AUDIT_OUTPUT_DIR,
    ANALYSIS_V2_DARK_TEXT,
    ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    ANALYSIS_V2_MAGNETIC_COHORT_COLORS,
    ANALYSIS_V2_MAGNETIC_COHORT_LABELS,
    ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
    FigureExportPaths,
    apply_analysis_v2_publication_style,
    save_analysis_v2_figure_bundle,
)


EXPECTED_ANALYSIS_V2_ROWS = 10684

FORMULA_COLUMN = "formula_reduced"
SPACE_GROUP_COLUMN = "space_group_number_recomputed"

FIGURE_BASENAME = "14_chemical_uniqueness_v2"
SUMMARY_CSV = "chemical_uniqueness_summary_v2.csv"
ADAPTATION_DELTA_CSV = "chemical_uniqueness_adaptation_delta_pp_v2.csv"

ADAPTATION_PAIRS = (
    (
        "MatterGen\nFT − Base",
        "mattergen_baseline",
        "mattergen_finetuned",
    ),
    (
        "Con-CDVAE\nFT − Base",
        "concdvae_baseline",
        "concdvae_finetuned",
    ),
    (
        "Crys-JEPA\nRef. − Base",
        "crysjepa_base",
        "crysjepa_refined",
    ),
)


@dataclass(frozen=True)
class DiversityFigureReport:
    input_csv: Path
    summary_table: object
    adaptation_delta_table: object
    summary_csv: Path
    adaptation_delta_csv: Path
    figure_paths: FigureExportPaths


def load_analysis_v2_diversity_input(
    input_csv: str | Path = ANALYSIS_V2_MAGNETIC_INPUT,
):
    import pandas as pd

    path = Path(input_csv)
    if not path.is_file():
        raise FileNotFoundError(path)

    df = pd.read_csv(path, low_memory=False)

    required = {
        "analysis_cohort",
        FORMULA_COLUMN,
        SPACE_GROUP_COLUMN,
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise RuntimeError(
            f"Analysis v2 diversity input is missing columns: {missing}"
        )

    if len(df) != EXPECTED_ANALYSIS_V2_ROWS:
        raise RuntimeError(
            f"Expected {EXPECTED_ANALYSIS_V2_ROWS} Analysis v2 rows, "
            f"found {len(df)}"
        )

    observed_cohorts = set(df["analysis_cohort"].dropna().astype(str))
    expected_cohorts = set(ANALYSIS_V2_MAGNETIC_COHORT_ORDER)

    if observed_cohorts != expected_cohorts:
        raise RuntimeError(
            "Analysis v2 cohort set differs from diversity figure contract: "
            f"observed={sorted(observed_cohorts)}"
        )

    if df[FORMULA_COLUMN].isna().any():
        raise RuntimeError(
            f"{FORMULA_COLUMN} contains missing values"
        )

    space_group = pd.to_numeric(
        df[SPACE_GROUP_COLUMN],
        errors="raise",
    )

    if space_group.isna().any():
        raise RuntimeError(
            f"{SPACE_GROUP_COLUMN} contains missing values"
        )

    integer_mask = (space_group % 1).eq(0)
    range_mask = space_group.between(1, 230)

    if not integer_mask.all() or not range_mask.all():
        raise RuntimeError(
            f"{SPACE_GROUP_COLUMN} contains invalid space-group numbers"
        )

    df = df.copy()
    df[SPACE_GROUP_COLUMN] = space_group.astype(int)

    return df


def build_diversity_tables(df):
    import pandas as pd

    rows = []

    for cohort in ANALYSIS_V2_MAGNETIC_COHORT_ORDER:
        d = df.loc[df["analysis_cohort"].eq(cohort)].copy()
        n = len(d)

        if n == 0:
            raise RuntimeError(
                f"Analysis v2 cohort is empty: {cohort}"
            )

        n_unique_formula = int(
            d[FORMULA_COLUMN].nunique(dropna=False)
        )

        n_unique_formula_sg = int(
            d[[FORMULA_COLUMN, SPACE_GROUP_COLUMN]]
            .drop_duplicates()
            .shape[0]
        )

        rows.append(
            {
                "analysis_cohort": cohort,
                "n_structures": n,
                "n_unique_formula": n_unique_formula,
                "unique_formula_percent": (
                    100.0 * n_unique_formula / n
                ),
                "n_unique_formula_sg": n_unique_formula_sg,
                "unique_formula_sg_percent": (
                    100.0 * n_unique_formula_sg / n
                ),
            }
        )

    summary = (
        pd.DataFrame(rows)
        .set_index("analysis_cohort")
        .reindex(ANALYSIS_V2_MAGNETIC_COHORT_ORDER)
    )

    delta_rows = []

    for label, baseline, adapted in ADAPTATION_PAIRS:
        delta_rows.append(
            {
                "comparison": label,
                "unique_formula_delta_pp": (
                    summary.loc[
                        adapted,
                        "unique_formula_percent",
                    ]
                    - summary.loc[
                        baseline,
                        "unique_formula_percent",
                    ]
                ),
                "unique_formula_sg_delta_pp": (
                    summary.loc[
                        adapted,
                        "unique_formula_sg_percent",
                    ]
                    - summary.loc[
                        baseline,
                        "unique_formula_sg_percent",
                    ]
                ),
            }
        )

    delta = (
        pd.DataFrame(delta_rows)
        .set_index("comparison")
    )

    return summary, delta


def _panel_label(ax, label: str) -> None:
    ax.text(
        -0.08,
        1.06,
        label,
        transform=ax.transAxes,
        fontsize=12,
        fontweight="bold",
        va="top",
        ha="left",
        color=ANALYSIS_V2_DARK_TEXT,
    )


def _plot_uniqueness_panel(
    ax,
    summary,
    *,
    metric: str,
    count_column: str,
    title: str,
    xlabel: str,
    panel_label: str,
    show_ylabels: bool,
) -> None:
    cohorts = list(ANALYSIS_V2_MAGNETIC_COHORT_ORDER)
    y = list(range(len(cohorts)))

    values = [
        float(summary.loc[cohort, metric])
        for cohort in cohorts
    ]

    colors = [
        ANALYSIS_V2_MAGNETIC_COHORT_COLORS[cohort]
        for cohort in cohorts
    ]

    bars = ax.barh(
        y,
        values,
        color=colors,
        edgecolor=ANALYSIS_V2_DARK_TEXT,
        linewidth=0.55,
        height=0.62,
    )

    for bar, cohort, value in zip(bars, cohorts, values):
        count = int(summary.loc[cohort, count_column])
        total = int(summary.loc[cohort, "n_structures"])

        ax.text(
            value + 1.3,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f}%  ({count}/{total})",
            va="center",
            ha="left",
            fontsize=7.5,
            color=ANALYSIS_V2_DARK_TEXT,
            clip_on=False,
        )

    ax.set_yticks(y)
    ax.set_yticklabels(
        [
            ANALYSIS_V2_MAGNETIC_COHORT_LABELS[cohort]
            for cohort in cohorts
        ]
    )
    ax.tick_params(
        axis="y",
        labelleft=show_ylabels,
    )

    ax.set_xlim(0, 112)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xlabel(xlabel)
    ax.set_title(title, pad=8)
    ax.grid(
        axis="x",
        color="#D5D5D5",
        linewidth=0.45,
        alpha=0.5,
    )
    ax.set_axisbelow(True)

    _panel_label(ax, panel_label)


def save_diversity_figure(
    summary,
    *,
    output_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> FigureExportPaths:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_analysis_v2_publication_style()

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(12.8, 5.6),
        sharey=True,
        constrained_layout=True,
    )
    fig.patch.set_facecolor("white")

    _plot_uniqueness_panel(
        axes[0],
        summary,
        metric="unique_formula_percent",
        count_column="n_unique_formula",
        title="Unique reduced formulas",
        xlabel="Unique reduced formulas (%)",
        panel_label="A",
        show_ylabels=True,
    )

    _plot_uniqueness_panel(
        axes[1],
        summary,
        metric="unique_formula_sg_percent",
        count_column="n_unique_formula_sg",
        title="Unique formula–space-group pairs",
        xlabel="Unique formula–space-group pairs (%)",
        panel_label="B",
        show_ylabels=False,
    )

    # The two panels share the y-axis. Invert it exactly once so that
    # ANALYSIS_V2_MAGNETIC_COHORT_ORDER is read from top to bottom.
    axes[0].invert_yaxis()

    paths = save_analysis_v2_figure_bundle(
        fig,
        output_dir,
        FIGURE_BASENAME,
    )
    plt.close(fig)

    return paths


def run_analysis_v2_diversity(
    input_csv: str | Path = ANALYSIS_V2_MAGNETIC_INPUT,
    figure_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    audit_dir: str | Path = ANALYSIS_V2_AUDIT_OUTPUT_DIR,
) -> DiversityFigureReport:
    df = load_analysis_v2_diversity_input(input_csv)
    summary, delta = build_diversity_tables(df)

    audit_root = Path(audit_dir)
    audit_root.mkdir(parents=True, exist_ok=True)

    summary_csv = audit_root / SUMMARY_CSV
    adaptation_delta_csv = audit_root / ADAPTATION_DELTA_CSV

    summary.to_csv(summary_csv)
    delta.to_csv(adaptation_delta_csv)

    figure_paths = save_diversity_figure(
        summary,
        output_dir=figure_dir,
    )

    return DiversityFigureReport(
        input_csv=Path(input_csv),
        summary_table=summary,
        adaptation_delta_table=delta,
        summary_csv=summary_csv,
        adaptation_delta_csv=adaptation_delta_csv,
        figure_paths=figure_paths,
    )
