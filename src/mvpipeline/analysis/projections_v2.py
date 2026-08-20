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
    ANALYSIS_V2_OUTPUT_DIR,
    ANALYSIS_V2_PCA_BASENAMES,
    FigureExportPaths,
    apply_analysis_v2_publication_style,
    save_analysis_v2_figure_bundle,
)


COMPOSITION_SYMMETRY_PCA_FEATURES = (
    "transition_3d_fraction",
    "selected_4d_5d_fraction",
    "configured_lanthanide_fraction",
    "n_transition_3d_species",
    "n_selected_4d_5d_species",
    "n_configured_lanthanide_species",
    "contains_3d_and_configured_lanthanide",
    "n_symmetry_unique_sites",
    "symmetry_unique_site_fraction",
    "n_symmetry_unique_magnetic_sites",
    "site_multiplicity_entropy",
)

MAGNETIC_GEOMETRY_PCA_FEATURES = (
    "magnetic_site_nearest_neighbor_distance_min",
    "magnetic_site_nearest_neighbor_distance_mean",
    "magnetic_site_nearest_neighbor_distance_std",
    "magnetic_site_nearest_magnetic_neighbor_distance_min",
    "magnetic_site_nearest_magnetic_neighbor_distance_mean",
    "magnetic_site_nearest_magnetic_neighbor_distance_std",
    "magnetic_site_coordination_mean",
    "magnetic_site_coordination_std",
    "magnetic_site_magnetic_coordination_mean",
    "magnetic_site_magnetic_coordination_std",
    "magnetic_site_magnetic_neighbor_fraction_mean",
    "magnetic_site_magnetic_neighbor_fraction_std",
    "symmetry_unique_magnetic_site_fraction",
)

IDENTITY_COLUMNS = (
    "structure_id",
    "sample_uid",
    "analysis_cohort",
    "model_name",
    "model_short",
)

EXPECTED_ANALYSIS_V2_ROWS = 10684
EXPECTED_MAGNETIC_GEOMETRY_PCA_ROWS = 7756
PCA_OUTPUT_DIR = ANALYSIS_V2_OUTPUT_DIR / "projections"


@dataclass(frozen=True)
class PcaSpaceResult:
    name: str
    features: tuple[str, ...]
    scores: object
    loadings: object
    explained_variance_ratio: tuple[float, float]
    cumulative_explained_variance: tuple[float, float]
    cohort_counts: dict[str, int]


@dataclass(frozen=True)
class AnalysisV2PcaReport:
    input_csv: Path
    output_dir: Path
    figure_dir: Path
    composition_scores_csv: Path
    composition_loadings_csv: Path
    magnetic_geometry_scores_csv: Path
    magnetic_geometry_loadings_csv: Path
    summary_markdown: Path
    figure_paths: tuple[FigureExportPaths, ...]
    composition: PcaSpaceResult
    magnetic_geometry: PcaSpaceResult


def _read_analysis_v2(input_csv: str | Path):
    import pandas as pd

    path = Path(input_csv)
    if not path.is_file():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def _require_columns(df, columns: tuple[str, ...], *, context: str) -> None:
    missing = sorted(set(columns).difference(df.columns))
    if missing:
        raise RuntimeError(f"{context}: missing PCA columns: {missing}")


def _numeric_feature_matrix(df, features: tuple[str, ...], *, context: str):
    import numpy as np
    import pandas as pd

    _require_columns(df, features, context=context)
    numeric = df.loc[:, features].apply(pd.to_numeric, errors="coerce")
    values = numeric.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        bad_features = [
            feature
            for feature in features
            if not np.isfinite(numeric[feature].to_numpy(dtype=float)).all()
        ]
        raise RuntimeError(f"{context}: non-finite PCA feature values: {bad_features}")
    variances = values.var(axis=0)
    zero_variance = [
        feature
        for feature, variance in zip(features, variances)
        if bool(np.isclose(variance, 0.0))
    ]
    if zero_variance:
        raise RuntimeError(f"{context}: zero-variance PCA features: {zero_variance}")
    return values


def _identity_frame(df):
    existing = [column for column in IDENTITY_COLUMNS if column in df.columns]
    return df.loc[:, existing].copy()


def _cohort_counts(df) -> dict[str, int]:
    counts = df["analysis_cohort"].value_counts()
    return {
        cohort: int(counts.get(cohort, 0))
        for cohort in ANALYSIS_V2_MAGNETIC_COHORT_ORDER
    }


def _fit_pca_space(
    df,
    *,
    name: str,
    features: tuple[str, ...],
    expected_rows: int | None,
) -> PcaSpaceResult:
    if expected_rows is not None and len(df) != expected_rows:
        raise RuntimeError(
            f"{name}: expected {expected_rows} rows for PCA, found {len(df)}"
        )

    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    values = _numeric_feature_matrix(df, features, context=name)
    scaled = StandardScaler().fit_transform(values)
    pca = PCA(n_components=2)
    coordinates = pca.fit_transform(scaled)

    scores = _identity_frame(df)
    scores["PC1"] = coordinates[:, 0]
    scores["PC2"] = coordinates[:, 1]

    import pandas as pd

    loadings = pd.DataFrame(
        {
            "feature": features,
            "PC1": pca.components_[0],
            "PC2": pca.components_[1],
        }
    )
    explained = tuple(float(value) for value in pca.explained_variance_ratio_)
    cumulative = (
        explained[0],
        explained[0] + explained[1],
    )
    return PcaSpaceResult(
        name=name,
        features=features,
        scores=scores,
        loadings=loadings,
        explained_variance_ratio=explained,
        cumulative_explained_variance=cumulative,
        cohort_counts=_cohort_counts(df),
    )


def build_analysis_v2_pca_spaces(
    df,
    *,
    expected_total_rows: int | None = EXPECTED_ANALYSIS_V2_ROWS,
    expected_geometry_rows: int | None = EXPECTED_MAGNETIC_GEOMETRY_PCA_ROWS,
) -> tuple[PcaSpaceResult, PcaSpaceResult]:
    _require_columns(
        df,
        ("analysis_cohort", "magnetic_geometry_status"),
        context="analysis v2 PCA",
    )

    composition = _fit_pca_space(
        df,
        name="composition_symmetry",
        features=COMPOSITION_SYMMETRY_PCA_FEATURES,
        expected_rows=expected_total_rows,
    )

    geometry_df = df[df["magnetic_geometry_status"].astype(str) == "ok"].copy()
    magnetic_geometry = _fit_pca_space(
        geometry_df,
        name="magnetic_geometry",
        features=MAGNETIC_GEOMETRY_PCA_FEATURES,
        expected_rows=expected_geometry_rows,
    )
    return composition, magnetic_geometry


def _new_figure(figsize: tuple[float, float]):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_analysis_v2_publication_style()
    fig = plt.figure(figsize=figsize, constrained_layout=True)
    fig.patch.set_facecolor("white")
    return fig


def _style_pca_axis(ax, result: PcaSpaceResult, *, title: str) -> None:
    ax.axhline(0, color="#D5D5D5", linewidth=0.6, zorder=0)
    ax.axvline(0, color="#D5D5D5", linewidth=0.6, zorder=0)
    ax.grid(color="#D5D5D5", linewidth=0.45, alpha=0.45)
    ax.set_axisbelow(True)
    ax.set_title(title, pad=7)
    ax.set_xlabel(
        f"PC1 ({result.explained_variance_ratio[0] * 100:.1f}% variance)"
    )
    ax.set_ylabel(
        f"PC2 ({result.explained_variance_ratio[1] * 100:.1f}% variance)"
    )


def _scatter_pca_space(ax, result: PcaSpaceResult, *, title: str) -> None:
    for cohort in ANALYSIS_V2_MAGNETIC_COHORT_ORDER:
        subset = result.scores[result.scores["analysis_cohort"] == cohort]
        if subset.empty:
            continue
        ax.scatter(
            subset["PC1"],
            subset["PC2"],
            s=7,
            alpha=0.24,
            color=ANALYSIS_V2_MAGNETIC_COHORT_COLORS[cohort],
            linewidths=0,
            rasterized=True,
            label=ANALYSIS_V2_MAGNETIC_COHORT_LABELS[cohort].replace("\n", " "),
        )
        ax.scatter(
            [subset["PC1"].mean()],
            [subset["PC2"].mean()],
            s=66,
            marker="D",
            color=ANALYSIS_V2_MAGNETIC_COHORT_COLORS[cohort],
            edgecolor=ANALYSIS_V2_DARK_TEXT,
            linewidth=0.75,
            zorder=4,
        )
    _style_pca_axis(ax, result, title=title)


def _save_scatter_figure(
    result: PcaSpaceResult,
    *,
    output_dir: Path,
    basename: str,
    title: str,
) -> FigureExportPaths:
    import matplotlib.pyplot as plt

    fig = _new_figure((7.7, 6.0))
    ax = fig.add_subplot(1, 1, 1)
    _scatter_pca_space(ax, result, title=title)
    ax.legend(
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=False,
        borderaxespad=0.0,
        markerscale=1.7,
    )
    paths = save_analysis_v2_figure_bundle(fig, output_dir, basename)
    plt.close(fig)
    return paths


def _plot_shift_panel(ax, result: PcaSpaceResult, baseline: str, adapted: str) -> None:
    for cohort in (baseline, adapted):
        subset = result.scores[result.scores["analysis_cohort"] == cohort]
        ax.scatter(
            subset["PC1"],
            subset["PC2"],
            s=8,
            alpha=0.22,
            color=ANALYSIS_V2_MAGNETIC_COHORT_COLORS[cohort],
            linewidths=0,
            rasterized=True,
            label=ANALYSIS_V2_MAGNETIC_COHORT_LABELS[cohort].replace("\n", " "),
        )
    start = result.scores[result.scores["analysis_cohort"] == baseline][["PC1", "PC2"]]
    end = result.scores[result.scores["analysis_cohort"] == adapted][["PC1", "PC2"]]
    start_xy = (float(start["PC1"].mean()), float(start["PC2"].mean()))
    end_xy = (float(end["PC1"].mean()), float(end["PC2"].mean()))
    ax.scatter(
        [start_xy[0], end_xy[0]],
        [start_xy[1], end_xy[1]],
        s=76,
        marker="D",
        color=[
            ANALYSIS_V2_MAGNETIC_COHORT_COLORS[baseline],
            ANALYSIS_V2_MAGNETIC_COHORT_COLORS[adapted],
        ],
        edgecolor=ANALYSIS_V2_DARK_TEXT,
        linewidth=0.75,
        zorder=4,
    )
    ax.annotate(
        "",
        xy=end_xy,
        xytext=start_xy,
        arrowprops={
            "arrowstyle": "->",
            "color": ANALYSIS_V2_DARK_TEXT,
            "linewidth": 1.25,
            "shrinkA": 8,
            "shrinkB": 8,
        },
    )
    ax.text(
        0.02,
        0.97,
        "centroid shift",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=8,
        color=ANALYSIS_V2_DARK_TEXT,
    )
    ax.legend(frameon=False, loc="lower right")


def _save_adaptation_shift_figure(
    result: PcaSpaceResult,
    *,
    output_dir: Path,
) -> FigureExportPaths:
    import matplotlib.pyplot as plt

    fig = _new_figure((12.2, 4.6))
    fig.suptitle(
        "Centroid shifts in composition + global symmetry PCA space",
        fontsize=11,
    )
    axes = fig.subplots(1, 3, sharex=True, sharey=True)
    panels = (
        ("mattergen_baseline", "mattergen_finetuned", "MatterGen adaptation"),
        ("concdvae_baseline", "concdvae_finetuned", "Con-CDVAE adaptation"),
        ("crysjepa_base", "crysjepa_refined", "Crys-JEPA refinement"),
    )
    for ax, (baseline, adapted, title) in zip(axes, panels):
        _plot_shift_panel(ax, result, baseline, adapted)
        _style_pca_axis(ax, result, title=title)
    paths = save_analysis_v2_figure_bundle(
        fig,
        output_dir,
        ANALYSIS_V2_PCA_BASENAMES[2],
    )
    plt.close(fig)
    return paths


def _top_loadings(loadings, pc: str, *, n: int = 6):
    selected = loadings.copy()
    selected["abs_loading"] = selected[pc].abs()
    return selected.sort_values("abs_loading", ascending=True).tail(n)


def _plot_loading_axis(ax, loadings, pc: str, *, title: str) -> None:
    selected = _top_loadings(loadings, pc)
    colors = [
        "#4F6745" if value >= 0 else "#AC473D"
        for value in selected[pc]
    ]
    ax.barh(selected["feature"], selected[pc], color=colors, alpha=0.82)
    ax.axvline(0, color=ANALYSIS_V2_DARK_TEXT, linewidth=0.75)
    ax.set_title(title, pad=6)
    ax.set_xlabel("PCA loading")
    ax.grid(axis="x", color="#D5D5D5", linewidth=0.45, alpha=0.55)


def _save_loadings_figure(
    composition: PcaSpaceResult,
    magnetic_geometry: PcaSpaceResult,
    *,
    output_dir: Path,
) -> FigureExportPaths:
    import matplotlib.pyplot as plt

    fig = _new_figure((13.5, 8.0))
    axes = fig.subplots(2, 2)
    _plot_loading_axis(
        axes[0, 0],
        composition.loadings,
        "PC1",
        title="Composition + symmetry PC1",
    )
    _plot_loading_axis(
        axes[0, 1],
        composition.loadings,
        "PC2",
        title="Composition + symmetry PC2",
    )
    _plot_loading_axis(
        axes[1, 0],
        magnetic_geometry.loadings,
        "PC1",
        title="Magnetic geometry PC1",
    )
    _plot_loading_axis(
        axes[1, 1],
        magnetic_geometry.loadings,
        "PC2",
        title="Magnetic geometry PC2",
    )
    paths = save_analysis_v2_figure_bundle(
        fig,
        output_dir,
        ANALYSIS_V2_PCA_BASENAMES[3],
    )
    plt.close(fig)
    return paths


def _format_percent(values: tuple[float, float]) -> str:
    return ", ".join(f"{value * 100:.2f}%" for value in values)


def _loading_lines(result: PcaSpaceResult, pc: str) -> list[str]:
    selected = _top_loadings(result.loadings, pc, n=5).sort_values(
        "abs_loading",
        ascending=False,
    )
    return [
        f"- `{row.feature}`: `{getattr(row, pc):.6f}`"
        for row in selected.itertuples(index=False)
    ]


def _write_summary(
    path: Path,
    *,
    input_csv: Path,
    input_rows: int,
    composition: PcaSpaceResult,
    magnetic_geometry: PcaSpaceResult,
) -> None:
    lines = [
        "# Analysis v2 magnetic PCA summary",
        "",
        f"Input: `{input_csv}`",
        f"Input rows: `{input_rows}`",
        "Scaling: `sklearn.preprocessing.StandardScaler` fit separately for each PCA space.",
        "PCA: `sklearn.decomposition.PCA(n_components=2)` fit once across eligible rows from all eight cohorts.",
        "CHGNet and DXMag fields are not PCA features.",
        "",
        "## Composition + Global Symmetry PCA",
        "",
        f"Rows used: `{len(composition.scores)}`",
        "Features:",
        *(f"- `{feature}`" for feature in composition.features),
        "",
        f"Explained variance ratio: `{_format_percent(composition.explained_variance_ratio)}`",
        f"Cumulative explained variance: `{_format_percent(composition.cumulative_explained_variance)}`",
        "",
        "Per-cohort rows:",
        *(f"- `{cohort}`: `{count}`" for cohort, count in composition.cohort_counts.items()),
        "",
        "Top absolute loadings for PC1:",
        *_loading_lines(composition, "PC1"),
        "",
        "Top absolute loadings for PC2:",
        *_loading_lines(composition, "PC2"),
        "",
        "## Magnetic-Sublattice Geometry/Symmetry PCA",
        "",
        f"Rows used: `{len(magnetic_geometry.scores)}`",
        "Selection: `magnetic_geometry_status == \"ok\"`; not_applicable rows are excluded, not imputed.",
        "Features:",
        *(f"- `{feature}`" for feature in magnetic_geometry.features),
        "",
        f"Explained variance ratio: `{_format_percent(magnetic_geometry.explained_variance_ratio)}`",
        f"Cumulative explained variance: `{_format_percent(magnetic_geometry.cumulative_explained_variance)}`",
        "",
        "Per-cohort applicable rows:",
        *(f"- `{cohort}`: `{count}`" for cohort, count in magnetic_geometry.cohort_counts.items()),
        "",
        "Top absolute loadings for PC1:",
        *_loading_lines(magnetic_geometry, "PC1"),
        "",
        "Top absolute loadings for PC2:",
        *_loading_lines(magnetic_geometry, "PC2"),
        "",
        "Interpretation boundary: PCA is descriptive. Centroid arrows denote cohort-level centroid shifts, not paired trajectories or causal improvement.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_analysis_v2_pca_outputs(
    input_csv: str | Path = ANALYSIS_V2_MAGNETIC_INPUT,
    output_dir: str | Path = PCA_OUTPUT_DIR,
    figure_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    *,
    expected_total_rows: int | None = EXPECTED_ANALYSIS_V2_ROWS,
    expected_geometry_rows: int | None = EXPECTED_MAGNETIC_GEOMETRY_PCA_ROWS,
) -> AnalysisV2PcaReport:
    df = _read_analysis_v2(input_csv)
    composition, magnetic_geometry = build_analysis_v2_pca_spaces(
        df,
        expected_total_rows=expected_total_rows,
        expected_geometry_rows=expected_geometry_rows,
    )

    output_root = Path(output_dir)
    figure_root = Path(figure_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    composition_scores_csv = output_root / "composition_symmetry_pca_scores.csv"
    composition_loadings_csv = output_root / "composition_symmetry_pca_loadings.csv"
    magnetic_geometry_scores_csv = output_root / "magnetic_geometry_pca_scores.csv"
    magnetic_geometry_loadings_csv = output_root / "magnetic_geometry_pca_loadings.csv"
    summary_markdown = output_root / "pca_summary.md"

    composition.scores.to_csv(composition_scores_csv, index=False)
    composition.loadings.to_csv(composition_loadings_csv, index=False)
    magnetic_geometry.scores.to_csv(magnetic_geometry_scores_csv, index=False)
    magnetic_geometry.loadings.to_csv(magnetic_geometry_loadings_csv, index=False)
    _write_summary(
        summary_markdown,
        input_csv=Path(input_csv),
        input_rows=len(df),
        composition=composition,
        magnetic_geometry=magnetic_geometry,
    )

    figure_paths = (
        _save_scatter_figure(
            composition,
            output_dir=figure_root,
            basename=ANALYSIS_V2_PCA_BASENAMES[0],
            title="Composition + global symmetry PCA",
        ),
        _save_scatter_figure(
            magnetic_geometry,
            output_dir=figure_root,
            basename=ANALYSIS_V2_PCA_BASENAMES[1],
            title="Magnetic-sublattice geometry PCA",
        ),
        _save_adaptation_shift_figure(composition, output_dir=figure_root),
        _save_loadings_figure(
            composition,
            magnetic_geometry,
            output_dir=figure_root,
        ),
    )

    return AnalysisV2PcaReport(
        input_csv=Path(input_csv),
        output_dir=output_root,
        figure_dir=figure_root,
        composition_scores_csv=composition_scores_csv,
        composition_loadings_csv=composition_loadings_csv,
        magnetic_geometry_scores_csv=magnetic_geometry_scores_csv,
        magnetic_geometry_loadings_csv=magnetic_geometry_loadings_csv,
        summary_markdown=summary_markdown,
        figure_paths=figure_paths,
        composition=composition,
        magnetic_geometry=magnetic_geometry,
    )
