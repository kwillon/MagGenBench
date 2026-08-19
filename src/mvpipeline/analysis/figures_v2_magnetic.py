from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .plotting_v2 import (
    ANALYSIS_V2_MAGNETIC_COHORT_COLORS,
    ANALYSIS_V2_MAGNETIC_COHORT_LABELS,
    ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
    ANALYSIS_V2_AUDIT_OUTPUT_DIR,
    ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    ANALYSIS_V2_OUTPUT_DIR,
    ANALYSIS_V2_PREVIEW_BASENAME,
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


def _plot_counts(ax, df) -> None:
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
    ax.set_xticks(x)
    ax.set_xticklabels(_cohort_labels(), rotation=0)
    ax.set_ylim(0, max(counts.values) * 1.14)
    _style_axis(ax)
    _panel_label(ax, "A")


def _plot_prevalence_and_nonzero_box(
    ax,
    df,
    *,
    variable: str,
    ylabel: str,
    panel: str,
) -> None:
    import numpy as np

    x = _cohort_positions()
    colors = _cohort_colors()
    prevalence = []
    nonzero = []
    for cohort in ANALYSIS_V2_MAGNETIC_COHORT_ORDER:
        values = _finite_values(df.loc[df["analysis_cohort"] == cohort, variable])
        prevalence.append(100.0 * float((values > 0).mean()) if len(values) else 0.0)
        nonzero.append(values[values > 0].to_numpy())

    ax.bar(
        x,
        prevalence,
        color=colors,
        alpha=0.84,
        edgecolor="#23324F",
        linewidth=0.45,
    )
    ax.set_ylabel("Structures with fraction > 0 (%)")
    ax.set_ylim(0, 100)
    ax.set_xticks(x)
    ax.set_xticklabels(_cohort_labels(), rotation=0)
    _style_axis(ax)

    inset = ax.inset_axes([0.08, 0.47, 0.86, 0.42])
    box_data = [
        values if len(values) else np.array([np.nan])
        for values in nonzero
    ]
    bp = inset.boxplot(
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
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.38)
    inset.set_xticks([])
    inset.set_ylabel("nonzero", fontsize=7)
    inset.tick_params(axis="y", labelsize=7)
    inset.set_title(ylabel, fontsize=8, pad=1)
    inset.grid(axis="y", color="#D5D5D5", linewidth=0.35, alpha=0.5)
    _panel_label(ax, panel)


def _plot_applicable_box(
    ax,
    df,
    *,
    variable: str,
    ylabel: str,
    panel: str,
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
    ax.set_ylim(0, 1.02)
    _style_axis(ax)
    _panel_label(ax, panel)


def generate_analysis_v2_magnetic_preview_figure(
    input_csv: str | Path = ANALYSIS_V2_MAGNETIC_INPUT,
    output_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> AnalysisV2MagneticPreviewReport:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_analysis_v2_publication_style()
    df = _read_analysis_v2_dataframe(input_csv)
    _require_audit_columns(df)

    fig, axes = plt.subplots(
        2,
        2,
        figsize=(12.0, 8.2),
        constrained_layout=True,
    )
    fig.patch.set_facecolor("white")

    _plot_counts(axes[0, 0], df)
    _plot_prevalence_and_nonzero_box(
        axes[0, 1],
        df,
        variable="transition_3d_fraction",
        ylabel="3d transition-metal fraction",
        panel="B",
    )
    _plot_prevalence_and_nonzero_box(
        axes[1, 0],
        df,
        variable="configured_lanthanide_fraction",
        ylabel="configured lanthanide fraction",
        panel="C",
    )
    _plot_applicable_box(
        axes[1, 1],
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

    return AnalysisV2MagneticPreviewReport(
        input_csv=Path(input_csv),
        output_dir=Path(output_dir),
        figure_paths=paths,
    )
