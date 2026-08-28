from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .figures_v2_magnetic import ANALYSIS_V2_MAGNETIC_INPUT
from .plotting_v2 import (
    ANALYSIS_V2_AUDIT_OUTPUT_DIR,
    ANALYSIS_V2_DARK_TEXT,
    ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    ANALYSIS_V2_MAGNETIC_COHORT_LABELS,
    ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
    ANALYSIS_V2_OVERVIEW_CREAM,
    FigureExportPaths,
    apply_analysis_v2_publication_style,
    save_analysis_v2_figure_bundle,
)


COMPOUND_CLASS_COLUMN = "compound_class"
EXPECTED_ANALYSIS_V2_ROWS = 10684
TOP_N_COMPOUND_CLASSES = 10
OTHER_CLASS_LABEL = "Other"

COMPOUND_CLASS_BASENAMES = (
    "11_compound_class_heatmap_v2",
    "12_compound_class_adaptation_shifts_v2",
)

COMPOUND_CLASS_DISTRIBUTION_CSV = (
    "compound_class_distribution_percent_v2.csv"
)
COMPOUND_CLASS_ADAPTATION_CSV = (
    "compound_class_adaptation_delta_pp_v2.csv"
)

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
class CompoundClassV2Report:
    input_csv: Path
    figure_dir: Path
    audit_dir: Path
    class_order: tuple[str, ...]
    distribution_table: object
    adaptation_delta_table: object
    distribution_csv: Path
    adaptation_delta_csv: Path
    figure_paths: tuple[FigureExportPaths, ...]


def _read_analysis_v2(input_csv: str | Path):
    import pandas as pd

    path = Path(input_csv)
    if not path.is_file():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def _require_compound_class_columns(df) -> None:
    required = {
        "structure_id",
        "sample_uid",
        "analysis_cohort",
        COMPOUND_CLASS_COLUMN,
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise RuntimeError(
            f"Analysis v2 input missing compound-class columns: {missing}"
        )


def _validate_analysis_v2_compound_classes(
    df,
    *,
    expected_total_rows: int | None = EXPECTED_ANALYSIS_V2_ROWS,
) -> None:
    _require_compound_class_columns(df)

    if expected_total_rows is not None and len(df) != expected_total_rows:
        raise RuntimeError(
            f"Expected {expected_total_rows} Analysis v2 rows, found {len(df)}"
        )

    if df[COMPOUND_CLASS_COLUMN].isna().any():
        count = int(df[COMPOUND_CLASS_COLUMN].isna().sum())
        raise RuntimeError(
            f"Analysis v2 compound_class contains {count} missing values"
        )

    blank = df[COMPOUND_CLASS_COLUMN].astype(str).str.strip().eq("")
    if blank.any():
        raise RuntimeError(
            f"Analysis v2 compound_class contains {int(blank.sum())} blank values"
        )

    cohort_values = set(df["analysis_cohort"].astype(str))
    expected = set(ANALYSIS_V2_MAGNETIC_COHORT_ORDER)

    unknown = sorted(cohort_values.difference(expected))
    if unknown:
        raise RuntimeError(f"Unexpected Analysis v2 cohorts: {unknown}")

    missing_cohorts = [
        cohort
        for cohort in ANALYSIS_V2_MAGNETIC_COHORT_ORDER
        if cohort not in cohort_values
    ]
    if missing_cohorts:
        raise RuntimeError(
            f"Analysis v2 input missing cohorts: {missing_cohorts}"
        )


def build_compound_class_tables(
    df,
    *,
    top_n: int = TOP_N_COMPOUND_CLASSES,
    expected_total_rows: int | None = EXPECTED_ANALYSIS_V2_ROWS,
):
    import numpy as np
    import pandas as pd

    _validate_analysis_v2_compound_classes(
        df,
        expected_total_rows=expected_total_rows,
    )

    if top_n < 1:
        raise ValueError("top_n must be at least 1")

    labels = df[COMPOUND_CLASS_COLUMN].astype(str)

    if OTHER_CLASS_LABEL in set(labels):
        raise RuntimeError(
            f"Reserved plotting label {OTHER_CLASS_LABEL!r} "
            "already exists as a compound class"
        )

    global_counts = labels.value_counts()
    top_classes = global_counts.head(top_n).index.tolist()
    class_order = tuple(top_classes + [OTHER_CLASS_LABEL])

    plot_df = df.loc[:, ["analysis_cohort", COMPOUND_CLASS_COLUMN]].copy()
    plot_df["compound_class_plot"] = labels.where(
        labels.isin(top_classes),
        OTHER_CLASS_LABEL,
    )

    distribution = (
        pd.crosstab(
            plot_df["analysis_cohort"],
            plot_df["compound_class_plot"],
            normalize="index",
        )
        * 100.0
    )
    distribution = distribution.reindex(
        index=ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
        columns=class_order,
        fill_value=0.0,
    )

    row_sums = distribution.sum(axis=1).to_numpy(dtype=float)
    if not np.allclose(row_sums, 100.0, atol=1e-8):
        raise RuntimeError(
            "Compound-class percentage rows do not sum to 100%"
        )

    delta_rows = []
    delta_index = []

    for label, baseline, adapted in ADAPTATION_PAIRS:
        delta_rows.append(
            (
                distribution.loc[adapted]
                - distribution.loc[baseline]
            ).to_numpy(dtype=float)
        )
        delta_index.append(label)

    adaptation_delta = pd.DataFrame(
        delta_rows,
        index=delta_index,
        columns=class_order,
    )

    delta_sums = adaptation_delta.sum(axis=1).to_numpy(dtype=float)
    if not np.allclose(delta_sums, 0.0, atol=1e-8):
        raise RuntimeError(
            "Compound-class adaptation deltas do not sum to zero"
        )

    return class_order, distribution, adaptation_delta


def _new_figure(figsize: tuple[float, float]):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_analysis_v2_publication_style()
    fig = plt.figure(figsize=figsize, constrained_layout=True)
    fig.patch.set_facecolor("white")
    return fig


def _sequential_compound_class_cmap():
    from matplotlib.colors import LinearSegmentedColormap

    return LinearSegmentedColormap.from_list(
        "analysis_v2_compound_class_sequential",
        [
            "#FFFFFF",
            ANALYSIS_V2_OVERVIEW_CREAM,
            "#829DA6",
            "#304862",
        ],
    )


def _diverging_compound_class_cmap():
    from matplotlib.colors import LinearSegmentedColormap

    return LinearSegmentedColormap.from_list(
        "analysis_v2_compound_class_diverging",
        [
            "#304862",
            "#829DA6",
            ANALYSIS_V2_OVERVIEW_CREAM,
            "#DCAD5B",
            "#BA5F19",
        ],
    )


def _format_class_axis(ax, class_order: tuple[str, ...]) -> None:
    ax.set_xticks(range(len(class_order)))
    ax.set_xticklabels(
        class_order,
        rotation=36,
        ha="right",
        rotation_mode="anchor",
    )
    ax.tick_params(axis="x", pad=4)


def _distribution_row_labels() -> list[str]:
    return [
        ANALYSIS_V2_MAGNETIC_COHORT_LABELS[cohort].replace("\n", " ")
        for cohort in ANALYSIS_V2_MAGNETIC_COHORT_ORDER
    ]


def _annotate_distribution_heatmap(ax, table, *, vmax: float) -> None:
    threshold = 0.52 * vmax

    for row_index in range(table.shape[0]):
        for column_index in range(table.shape[1]):
            value = float(table.iat[row_index, column_index])
            text_color = "white" if value >= threshold else ANALYSIS_V2_DARK_TEXT

            ax.text(
                column_index,
                row_index,
                f"{value:.1f}",
                ha="center",
                va="center",
                fontsize=7.5,
                color=text_color,
            )


def _annotate_delta_heatmap(ax, table, *, vmax: float) -> None:
    threshold = 0.52 * vmax

    for row_index in range(table.shape[0]):
        for column_index in range(table.shape[1]):
            value = float(table.iat[row_index, column_index])
            text_color = (
                "white"
                if abs(value) >= threshold
                else ANALYSIS_V2_DARK_TEXT
            )

            ax.text(
                column_index,
                row_index,
                f"{value:+.1f}",
                ha="center",
                va="center",
                fontsize=7.5,
                color=text_color,
            )


def save_compound_class_distribution_heatmap(
    distribution,
    class_order: tuple[str, ...],
    *,
    output_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> FigureExportPaths:
    import matplotlib.pyplot as plt

    fig = _new_figure((12.6, 6.0))
    ax = fig.add_subplot(1, 1, 1)

    vmax = float(distribution.to_numpy(dtype=float).max())

    image = ax.imshow(
        distribution.to_numpy(dtype=float),
        aspect="auto",
        vmin=0.0,
        vmax=vmax,
        cmap=_sequential_compound_class_cmap(),
    )

    _format_class_axis(ax, class_order)

    ax.set_yticks(range(len(ANALYSIS_V2_MAGNETIC_COHORT_ORDER)))
    ax.set_yticklabels(_distribution_row_labels())
    ax.set_title(
        "Compound-class distribution across generated sets",
        pad=9,
    )

    _annotate_distribution_heatmap(
        ax,
        distribution,
        vmax=vmax,
    )

    cbar = fig.colorbar(image, ax=ax, pad=0.02)
    cbar.set_label("Share within generated set (%)")

    paths = save_analysis_v2_figure_bundle(
        fig,
        output_dir,
        COMPOUND_CLASS_BASENAMES[0],
    )
    plt.close(fig)
    return paths


def save_compound_class_adaptation_heatmap(
    adaptation_delta,
    class_order: tuple[str, ...],
    *,
    output_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> FigureExportPaths:
    import matplotlib.pyplot as plt

    fig = _new_figure((12.6, 3.7))
    ax = fig.add_subplot(1, 1, 1)

    values = adaptation_delta.to_numpy(dtype=float)
    vmax = float(abs(values).max())

    image = ax.imshow(
        values,
        aspect="auto",
        vmin=-vmax,
        vmax=vmax,
        cmap=_diverging_compound_class_cmap(),
    )

    _format_class_axis(ax, class_order)

    ax.set_yticks(range(len(adaptation_delta.index)))
    ax.set_yticklabels(adaptation_delta.index)
    ax.set_title(
        "Compound-class shifts after adaptation and refinement",
        pad=9,
    )

    _annotate_delta_heatmap(
        ax,
        adaptation_delta,
        vmax=vmax,
    )

    cbar = fig.colorbar(image, ax=ax, pad=0.02)
    cbar.set_label(
        "Change from baseline (percentage points)"
    )

    paths = save_analysis_v2_figure_bundle(
        fig,
        output_dir,
        COMPOUND_CLASS_BASENAMES[1],
    )
    plt.close(fig)
    return paths


def run_analysis_v2_compound_classes(
    input_csv: str | Path = ANALYSIS_V2_MAGNETIC_INPUT,
    figure_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    audit_dir: str | Path = ANALYSIS_V2_AUDIT_OUTPUT_DIR,
) -> CompoundClassV2Report:
    df = _read_analysis_v2(input_csv)

    class_order, distribution, adaptation_delta = (
        build_compound_class_tables(df)
    )

    audit_root = Path(audit_dir)
    audit_root.mkdir(parents=True, exist_ok=True)

    distribution_csv = audit_root / COMPOUND_CLASS_DISTRIBUTION_CSV
    adaptation_delta_csv = audit_root / COMPOUND_CLASS_ADAPTATION_CSV

    distribution.to_csv(distribution_csv)
    adaptation_delta.to_csv(adaptation_delta_csv)

    figure_paths = (
        save_compound_class_distribution_heatmap(
            distribution,
            class_order,
            output_dir=figure_dir,
        ),
        save_compound_class_adaptation_heatmap(
            adaptation_delta,
            class_order,
            output_dir=figure_dir,
        ),
    )

    return CompoundClassV2Report(
        input_csv=Path(input_csv),
        figure_dir=Path(figure_dir),
        audit_dir=audit_root,
        class_order=class_order,
        distribution_table=distribution,
        adaptation_delta_table=adaptation_delta,
        distribution_csv=distribution_csv,
        adaptation_delta_csv=adaptation_delta_csv,
        figure_paths=figure_paths,
    )
