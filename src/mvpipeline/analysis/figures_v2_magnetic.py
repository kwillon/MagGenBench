from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .plotting_v2 import (
    ANALYSIS_V2_MAGNETIC_COHORT_COLORS,
    ANALYSIS_V2_MAGNETIC_COHORT_LABELS,
    ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
    ANALYSIS_V2_AUDIT_OUTPUT_DIR,
    ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    ANALYSIS_V2_PREVIEW_BASENAME,
    ANALYSIS_V2_STANDALONE_BASENAMES,
    FigureExportPaths,
    apply_analysis_v2_publication_style,
    save_analysis_v2_figure_bundle,
)


ANALYSIS_V2_MAGNETIC_INPUT = Path(
    "tables/10_analysis_v2_magnetic/analysis_v2_magnetic.csv"
)

AUDIT_VARIABLES = (
    "transition_3d_fraction",
    "selected_4d_5d_fraction",
    "configured_lanthanide_fraction",
    "magnetic_site_nearest_neighbor_distance_min",
    "magnetic_site_nearest_neighbor_distance_mean",
    "magnetic_site_nearest_magnetic_neighbor_distance_min",
    "magnetic_site_nearest_magnetic_neighbor_distance_mean",
    "magnetic_site_coordination_mean",
    "magnetic_site_magnetic_coordination_mean",
    "magnetic_site_magnetic_neighbor_fraction_mean",
    "symmetry_unique_site_fraction",
    "symmetry_unique_magnetic_site_fraction",
    "site_multiplicity_entropy",
)

COMPOSITION_FRACTION_VARIABLES = (
    "transition_3d_fraction",
    "selected_4d_5d_fraction",
    "configured_lanthanide_fraction",
)

MAGNETIC_GEOMETRY_VARIABLES = (
    "magnetic_site_nearest_neighbor_distance_min",
    "magnetic_site_nearest_neighbor_distance_mean",
    "magnetic_site_nearest_magnetic_neighbor_distance_min",
    "magnetic_site_nearest_magnetic_neighbor_distance_mean",
    "magnetic_site_coordination_mean",
    "magnetic_site_magnetic_coordination_mean",
    "magnetic_site_magnetic_neighbor_fraction_mean",
    "symmetry_unique_magnetic_site_fraction",
)

ENERGY_COLUMN_CANDIDATES = (
    "energy_total_energy_eV",
    "energy_total_energy_eV_per_atom",
    "energy_formation_energy_proxy_eV",
    "energy_formation_energy_proxy_eV_per_atom",
    "energy_stability_energy_proxy_eV_per_atom",
)
DXMAG_COLUMN_CANDIDATES = (
    "magnetism_predicted_moment_value",
)


@dataclass(frozen=True)
class AnalysisV2MagneticAuditReport:
    input_csv: Path
    output_dir: Path
    audit_csv: Path
    audit_markdown: Path
    energy_columns: tuple[str, ...]
    dxmag_columns: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisV2MagneticPreviewReport:
    input_csv: Path
    output_dir: Path
    figure_paths: FigureExportPaths
    standalone_paths: tuple[FigureExportPaths, ...] = ()


def _read_analysis_v2_dataframe(input_csv: str | Path):
    import pandas as pd

    path = Path(input_csv)
    if not path.is_file():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def _as_numeric(series):
    import pandas as pd

    return pd.to_numeric(series, errors="coerce")


def _quantile(values, q: float) -> float | None:
    if values.empty:
        return None
    return float(values.quantile(q))


def _finite_values(series):
    import numpy as np

    numeric = _as_numeric(series)
    return numeric[np.isfinite(numeric)]


def _audit_variable_for_cohort(df, variable: str, cohort: str) -> dict[str, object]:
    cohort_df = df[df["analysis_cohort"] == cohort]
    finite = _finite_values(cohort_df[variable])
    n_total = int(len(cohort_df))
    n_finite = int(len(finite))
    n_missing = n_total - n_finite
    n_zero = int((finite == 0).sum()) if n_finite else 0
    geometry_applicable = cohort_df["magnetic_geometry_status"].astype(str).eq("ok")

    record: dict[str, object] = {
        "variable": variable,
        "analysis_cohort": cohort,
        "cohort_label": ANALYSIS_V2_MAGNETIC_COHORT_LABELS[cohort].replace("\n", " "),
        "n_total": n_total,
        "n_finite": n_finite,
        "n_missing": n_missing,
        "missing_fraction": n_missing / n_total if n_total else None,
        "n_zero": n_zero,
        "zero_fraction_available": n_zero / n_finite if n_finite else None,
        "min": float(finite.min()) if n_finite else None,
        "q1": _quantile(finite, 0.25),
        "median": _quantile(finite, 0.5),
        "mean": float(finite.mean()) if n_finite else None,
        "q3": _quantile(finite, 0.75),
        "max": float(finite.max()) if n_finite else None,
    }

    if variable in COMPOSITION_FRACTION_VARIABLES:
        record["prevalence_gt_zero"] = (
            int((finite > 0).sum()) / n_finite if n_finite else None
        )
    else:
        record["prevalence_gt_zero"] = None

    if variable in MAGNETIC_GEOMETRY_VARIABLES:
        expected_not_applicable = int(
            cohort_df["magnetic_geometry_status"]
            .astype(str)
            .eq("not_applicable")
            .sum()
        )
        unexpected_missing = int(
            (geometry_applicable & _as_numeric(cohort_df[variable]).isna()).sum()
        )
        record["expected_not_applicable_rows"] = expected_not_applicable
        record["unexpected_missing_or_error_rows"] = unexpected_missing
    else:
        record["expected_not_applicable_rows"] = None
        record["unexpected_missing_or_error_rows"] = None

    return record


def _require_audit_columns(df) -> None:
    required = {
        "analysis_cohort",
        "structure_id",
        "sample_uid",
        "magnetic_geometry_status",
        *AUDIT_VARIABLES,
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise RuntimeError(f"Analysis v2 input missing audit columns: {missing}")


def audit_analysis_v2_magnetic_inputs(
    input_csv: str | Path = ANALYSIS_V2_MAGNETIC_INPUT,
    output_dir: str | Path = ANALYSIS_V2_AUDIT_OUTPUT_DIR,
) -> AnalysisV2MagneticAuditReport:
    df = _read_analysis_v2_dataframe(input_csv)
    _require_audit_columns(df)

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    cohort_counts = (
        df["analysis_cohort"]
        .value_counts()
        .reindex(ANALYSIS_V2_MAGNETIC_COHORT_ORDER)
    )
    if cohort_counts.isna().any():
        raise RuntimeError("Analysis v2 input missing one or more v2 cohorts")

    records = []
    for variable in AUDIT_VARIABLES:
        for cohort in ANALYSIS_V2_MAGNETIC_COHORT_ORDER:
            records.append(_audit_variable_for_cohort(df, variable, cohort))

    import pandas as pd

    audit_df = pd.DataFrame(records)
    audit_csv = output_root / "analysis_v2_magnetic_variable_audit.csv"
    audit_df.to_csv(audit_csv, index=False)

    energy_columns = tuple(
        column for column in ENERGY_COLUMN_CANDIDATES if column in df.columns
    )
    dxmag_columns = tuple(
        column for column in DXMAG_COLUMN_CANDIDATES if column in df.columns
    )

    markdown = output_root / "analysis_v2_magnetic_audit.md"
    lines = [
        "# Analysis v2 magnetic figure-input audit",
        "",
        f"Input: `{Path(input_csv)}`",
        f"Rows: `{len(df)}`",
        f"Columns: `{len(df.columns)}`",
        "",
        "## Cohort Counts",
        "",
    ]
    for cohort in ANALYSIS_V2_MAGNETIC_COHORT_ORDER:
        lines.append(
            f"- `{cohort}`: `{int(cohort_counts.loc[cohort])}`"
        )

    lines.extend(
        [
            "",
            "## Energy And DXMag Columns",
            "",
            "Energy-related columns detected:",
            *(f"- `{column}`" for column in energy_columns),
            "",
            "DXMag predicted moment columns detected:",
            *(f"- `{column}`" for column in dxmag_columns),
            "",
            "## Variable Audit",
            "",
            f"Full per-cohort audit CSV: `{audit_csv.name}`",
        ]
    )
    markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return AnalysisV2MagneticAuditReport(
        input_csv=Path(input_csv),
        output_dir=output_root,
        audit_csv=audit_csv,
        audit_markdown=markdown,
        energy_columns=energy_columns,
        dxmag_columns=dxmag_columns,
    )


def _cohort_positions():
    return list(range(len(ANALYSIS_V2_MAGNETIC_COHORT_ORDER)))


def _cohort_labels():
    return [
        ANALYSIS_V2_MAGNETIC_COHORT_LABELS[cohort]
        for cohort in ANALYSIS_V2_MAGNETIC_COHORT_ORDER
    ]


def _cohort_colors():
    return [
        ANALYSIS_V2_MAGNETIC_COHORT_COLORS[cohort]
        for cohort in ANALYSIS_V2_MAGNETIC_COHORT_ORDER
    ]


def _style_axis(ax, *, grid_axis: str = "y") -> None:
    ax.grid(axis=grid_axis, color="#D5D5D5", linewidth=0.45, alpha=0.55)
    ax.set_axisbelow(True)


def _panel_label(ax, label: str) -> None:
    ax.text(
        -0.09,
        1.05,
        label,
        transform=ax.transAxes,
        fontsize=12,
        fontweight="bold",
        va="top",
        ha="left",
    )


def _format_cohort_axis(ax, *, with_labels: bool = True) -> None:
    x = _cohort_positions()
    ax.set_xticks(x)
    if with_labels:
        ax.set_xticklabels(_cohort_labels(), rotation=0)
        ax.tick_params(axis="x", pad=5)
    else:
        ax.set_xticklabels([])
        ax.tick_params(axis="x", length=0)


def _plot_counts(ax, df, *, panel: str | None = None) -> None:
    counts = (
        df["analysis_cohort"]
        .value_counts()
        .reindex(ANALYSIS_V2_MAGNETIC_COHORT_ORDER)
        .astype(int)
    )
    x = _cohort_positions()
    bars = ax.bar(
        x,
        counts.values,
        color=_cohort_colors(),
        edgecolor="#23324F",
        linewidth=0.45,
    )
    for bar, count in zip(bars, counts.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{int(count)}",
            ha="center",
            va="bottom",
            fontsize=7.2,
        )
    ax.set_ylabel("Structures")
    _format_cohort_axis(ax)
    ax.set_ylim(0, max(counts.values) * 1.14)
    _style_axis(ax)
    if panel:
        _panel_label(ax, panel)


def _nonzero_values_by_cohort(df, variable: str):
    values_by_cohort = []
    prevalence = []
    for cohort in ANALYSIS_V2_MAGNETIC_COHORT_ORDER:
        values = _finite_values(df.loc[df["analysis_cohort"] == cohort, variable])
        prevalence.append(100.0 * float((values > 0).mean()) if len(values) else 0.0)
        values_by_cohort.append(values[values > 0].to_numpy())
    return prevalence, values_by_cohort


def _plot_fraction_prevalence_axis(
    df,
    *,
    variable: str,
    ax,
    with_labels: bool,
) -> None:
    x = _cohort_positions()
    prevalence, _ = _nonzero_values_by_cohort(df, variable)
    ax.bar(
        x,
        prevalence,
        color=_cohort_colors(),
        alpha=0.84,
        edgecolor="#23324F",
        linewidth=0.45,
    )
    ax.set_ylabel("Prevalence (>0), %")
    ax.set_ylim(0, 100)
    _format_cohort_axis(ax, with_labels=with_labels)
    _style_axis(ax)

def _plot_fraction_nonzero_axis(
    df,
    *,
    variable: str,
    ax,
    with_labels: bool,
) -> None:
    import numpy as np

    x = _cohort_positions()
    _, nonzero = _nonzero_values_by_cohort(df, variable)
    box_data = [
        values if len(values) else np.array([np.nan])
        for values in nonzero
    ]
    bp = ax.boxplot(
        box_data,
        positions=x,
        widths=0.58,
        patch_artist=True,
        showfliers=False,
        medianprops={"color": "#23324F", "linewidth": 0.95},
        boxprops={"linewidth": 0.55, "color": "#23324F"},
        whiskerprops={"linewidth": 0.55, "color": "#23324F"},
        capprops={"linewidth": 0.55, "color": "#23324F"},
    )
    for patch, color in zip(bp["boxes"], _cohort_colors()):
        patch.set_facecolor(color)
        patch.set_alpha(0.52)
    ax.set_ylabel("Fraction among\nnonzero structures")
    ax.set_ylim(0, 1.02)
    _format_cohort_axis(ax, with_labels=with_labels)
    _style_axis(ax)


def _plot_fraction_panel(
    top_ax,
    bottom_ax,
    df,
    *,
    variable: str,
    title: str,
    panel: str | None = None,
) -> None:
    _plot_fraction_prevalence_axis(
        df,
        variable=variable,
        ax=top_ax,
        with_labels=False,
    )
    _plot_fraction_nonzero_axis(
        df,
        variable=variable,
        ax=bottom_ax,
        with_labels=True,
    )
    top_ax.set_title(title, pad=6)
    if panel:
        _panel_label(top_ax, panel)


def _plot_applicable_box(
    ax,
    df,
    *,
    variable: str,
    ylabel: str,
    panel: str | None = None,
) -> None:
    colors = _cohort_colors()
    x = _cohort_positions()
    data = []
    labels = []
    for cohort in ANALYSIS_V2_MAGNETIC_COHORT_ORDER:
        subset = df[
            (df["analysis_cohort"] == cohort)
            & (df["magnetic_geometry_status"].astype(str) == "ok")
        ]
        values = _finite_values(subset[variable])
        data.append(values.to_numpy())
        labels.append(
            f"{ANALYSIS_V2_MAGNETIC_COHORT_LABELS[cohort]}\n"
            f"n={len(values)}"
        )

    bp = ax.boxplot(
        data,
        positions=x,
        widths=0.62,
        patch_artist=True,
        showfliers=False,
        medianprops={"color": "#23324F", "linewidth": 1.05},
        boxprops={"linewidth": 0.6, "color": "#23324F"},
        whiskerprops={"linewidth": 0.6, "color": "#23324F"},
        capprops={"linewidth": 0.6, "color": "#23324F"},
    )
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.62)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=0)
    ax.tick_params(axis="x", pad=5)
    ax.set_ylim(0, 1.02)
    _style_axis(ax)
    if panel:
        _panel_label(ax, panel)


def _new_figure(figsize: tuple[float, float]):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_analysis_v2_publication_style()
    fig = plt.figure(figsize=figsize, constrained_layout=True)
    fig.patch.set_facecolor("white")
    return fig


def generate_analysis_v2_magnetic_standalone_figures(
    input_csv: str | Path = ANALYSIS_V2_MAGNETIC_INPUT,
    output_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> tuple[FigureExportPaths, ...]:
    df = _read_analysis_v2_dataframe(input_csv)
    _require_audit_columns(df)
    output_root = Path(output_dir)

    paths: list[FigureExportPaths] = []

    fig = _new_figure((8.8, 4.2))
    import matplotlib.pyplot as plt

    ax = fig.add_subplot(1, 1, 1)
    _plot_counts(ax, df)
    paths.append(save_analysis_v2_figure_bundle(
        fig, output_root, ANALYSIS_V2_STANDALONE_BASENAMES[0]
    ))
    plt.close(fig)

    for basename, variable, title in (
        (
            ANALYSIS_V2_STANDALONE_BASENAMES[1],
            "transition_3d_fraction",
            "3d transition-metal fraction",
        ),
        (
            ANALYSIS_V2_STANDALONE_BASENAMES[2],
            "configured_lanthanide_fraction",
            "Configured lanthanide fraction",
        ),
    ):
        fig = _new_figure((8.8, 5.8))
        sub = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.25], hspace=0.08)
        top_ax = fig.add_subplot(sub[0, 0])
        bottom_ax = fig.add_subplot(sub[1, 0], sharex=top_ax)
        _plot_fraction_panel(
            top_ax,
            bottom_ax,
            df,
            variable=variable,
            title=title,
        )
        paths.append(save_analysis_v2_figure_bundle(fig, output_root, basename))
        plt.close(fig)

    fig = _new_figure((8.8, 4.8))
    ax = fig.add_subplot(1, 1, 1)
    _plot_applicable_box(
        ax,
        df,
        variable="magnetic_site_magnetic_neighbor_fraction_mean",
        ylabel="Magnetic-neighbor fraction",
    )
    paths.append(save_analysis_v2_figure_bundle(
        fig, output_root, ANALYSIS_V2_STANDALONE_BASENAMES[3]
    ))
    plt.close(fig)

    return tuple(paths)


def generate_analysis_v2_magnetic_preview_figure(
    input_csv: str | Path = ANALYSIS_V2_MAGNETIC_INPUT,
    output_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    *,
    export_standalone: bool = True,
) -> AnalysisV2MagneticPreviewReport:
    df = _read_analysis_v2_dataframe(input_csv)
    _require_audit_columns(df)

    fig = _new_figure((14.2, 9.4))
    import matplotlib.pyplot as plt

    outer = fig.add_gridspec(2, 2, wspace=0.12, hspace=0.22)
    ax_counts = fig.add_subplot(outer[0, 0])
    transition_grid = outer[0, 1].subgridspec(
        2, 1, height_ratios=[1.0, 1.25], hspace=0.08
    )
    ax_transition_top = fig.add_subplot(transition_grid[0, 0])
    ax_transition_bottom = fig.add_subplot(
        transition_grid[1, 0], sharex=ax_transition_top
    )
    lanthanide_grid = outer[1, 0].subgridspec(
        2, 1, height_ratios=[1.0, 1.25], hspace=0.08
    )
    ax_lanthanide_top = fig.add_subplot(lanthanide_grid[0, 0])
    ax_lanthanide_bottom = fig.add_subplot(
        lanthanide_grid[1, 0], sharex=ax_lanthanide_top
    )
    ax_neighbor = fig.add_subplot(outer[1, 1])

    _plot_counts(ax_counts, df, panel="A")
    _plot_fraction_panel(
        ax_transition_top,
        ax_transition_bottom,
        df,
        variable="transition_3d_fraction",
        panel="B",
        title="3d transition-metal fraction",
    )
    _plot_fraction_panel(
        ax_lanthanide_top,
        ax_lanthanide_bottom,
        df,
        variable="configured_lanthanide_fraction",
        panel="C",
        title="Configured lanthanide fraction",
    )
    _plot_applicable_box(
        ax_neighbor,
        df,
        variable="magnetic_site_magnetic_neighbor_fraction_mean",
        ylabel="Magnetic-neighbor fraction",
        panel="D",
    )

    paths = save_analysis_v2_figure_bundle(
        fig,
        output_dir,
        ANALYSIS_V2_PREVIEW_BASENAME,
    )
    plt.close(fig)
    standalone_paths = (
        generate_analysis_v2_magnetic_standalone_figures(
            input_csv=input_csv,
            output_dir=output_dir,
        )
        if export_standalone
        else ()
    )

    return AnalysisV2MagneticPreviewReport(
        input_csv=Path(input_csv),
        output_dir=Path(output_dir),
        figure_paths=paths,
        standalone_paths=standalone_paths,
    )
