from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ANALYSIS_V1_FIGURE_FILENAMES = (
    "01_crystal_system_core_baseline.png",
    "02_crystal_system_finetuning.png",
    "03_crystal_system_crysjepa.png",
    "structural_distribution_summary.csv",
    "04_density_distribution.png",
    "05_volume_per_site_distribution.png",
    "06_sites_per_cell_distribution.png",
    "compound_class_distribution_percent.csv",
    "07_compound_class_heatmap.png",
    "3d_4f_fraction_by_cohort.csv",
    "08_3d_4f_fraction_by_cohort.png",
    "magnetic_screening_element_fraction_summary.csv",
    "09_magnetic_screening_element_fraction.png",
    "dxmag_predicted_moment_summary.csv",
    "10_dxmag_predicted_moment_distribution.png",
)

DXMAG_PREDICTED_MOMENT_YLABEL = "DXMag predicted moment (μB/f.u.)"


@dataclass(frozen=True)
class AnalysisV1FigureReport:
    input_csv: Path
    output_dir: Path
    output_files: tuple[Path, ...]


def owned_analysis_v1_figure_paths(output_dir: str | Path) -> tuple[Path, ...]:
    root = Path(output_dir)
    return tuple(root / filename for filename in ANALYSIS_V1_FIGURE_FILENAMES)


def prepare_analysis_v1_figure_outputs(
    output_dir: str | Path,
    *,
    force: bool = False,
) -> None:
    root = Path(output_dir)
    existing = [
        path
        for path in owned_analysis_v1_figure_paths(root)
        if path.exists()
    ]
    if existing and not force:
        formatted = ", ".join(str(path) for path in existing)
        raise RuntimeError(
            "Analysis v1 figure output already exists; use --force to "
            f"replace owned files: {formatted}"
        )

    root.mkdir(parents=True, exist_ok=True)
    if force:
        for path in existing:
            if path.is_dir():
                raise RuntimeError(
                    "Refusing to replace owned figure path because it is a "
                    f"directory: {path}"
                )
            path.unlink()


def _read_analysis_v1_dataframe(input_csv: str | Path):
    import pandas as pd

    path = Path(input_csv)
    if not path.is_file():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def _crystal_system_percentages(
    rows: list[dict[str, str]],
) -> dict[str, float]:
    from mvpipeline.analysis.plotting import CRYSTAL_SYSTEM_ORDER

    total = len(rows)
    if total == 0:
        raise RuntimeError("Cannot compute percentages for empty cohort.")

    counts = Counter(row["crystal_system"].strip() for row in rows)
    return {
        crystal_system: 100.0 * counts.get(crystal_system, 0) / total
        for crystal_system in CRYSTAL_SYSTEM_ORDER
    }


def _plot_grouped_bars(
    values_by_label: dict[str, dict[str, float]],
    *,
    title: str,
    output_path: Path,
) -> None:
    import matplotlib.pyplot as plt

    from mvpipeline.analysis.plotting import CRYSTAL_SYSTEM_ORDER, save_figure

    labels = list(values_by_label)
    x = list(range(len(CRYSTAL_SYSTEM_ORDER)))
    width = 0.8 / max(len(labels), 1)

    fig, ax = plt.subplots()

    for index, label in enumerate(labels):
        offsets = [
            xi - 0.4 + width / 2 + index * width
            for xi in x
        ]
        heights = [
            values_by_label[label][crystal_system]
            for crystal_system in CRYSTAL_SYSTEM_ORDER
        ]
        ax.bar(offsets, heights, width=width, label=label)

    ax.set_title(title)
    ax.set_ylabel("Share of structures (%)")
    ax.set_xlabel("Crystal system")
    ax.set_xticks(x)
    ax.set_xticklabels(CRYSTAL_SYSTEM_ORDER, rotation=25, ha="right")
    ax.legend(frameon=False)
    ax.set_ylim(bottom=0)

    save_figure(fig, output_path)
    plt.close(fig)


def generate_crystal_system_figures(
    input_csv: str | Path,
    output_dir: str | Path,
) -> tuple[Path, ...]:
    import matplotlib

    matplotlib.use("Agg")

    from mvpipeline.analysis.plotting import (
        BASELINE_PLOT_GROUPS,
        CRYSJEPA_COMPARISON_GROUPS,
        FINETUNING_COMPARISON_GROUPS,
        apply_unified_plot_style,
        build_plot_groups,
        load_unified_analysis_rows,
        validate_unified_analysis_rows,
    )

    input_path = Path(input_csv)
    output_root = Path(output_dir)
    apply_unified_plot_style()
    rows = load_unified_analysis_rows(input_path)
    validate_unified_analysis_rows(
        rows,
        required_columns=("crystal_system", "symmetry_status"),
    )

    missing = [
        row for row in rows
        if not row.get("crystal_system", "").strip()
    ]
    if missing:
        raise RuntimeError(f"Missing crystal_system rows: {len(missing)}")

    bad_symmetry = [
        row for row in rows
        if (row.get("symmetry_status", "").strip() or "") != "ok"
    ]
    if bad_symmetry:
        raise RuntimeError(f"Non-ok symmetry_status rows: {len(bad_symmetry)}")

    grouped_rows = {
        group.label: group_rows
        for group, group_rows in build_plot_groups(rows)
    }

    output_root.mkdir(parents=True, exist_ok=True)

    baseline_values = {
        group.analysis_family: _crystal_system_percentages(
            list(grouped_rows[group.label])
        )
        for group in BASELINE_PLOT_GROUPS
    }
    core_path = output_root / "01_crystal_system_core_baseline.png"
    _plot_grouped_bars(
        baseline_values,
        title="Crystal-system distribution across baseline models",
        output_path=core_path,
    )

    finetune_values = {}
    for group in FINETUNING_COMPARISON_GROUPS:
        finetune_values[group.label] = _crystal_system_percentages(
            list(grouped_rows[group.label])
        )

    finetune_path = output_root / "02_crystal_system_finetuning.png"
    _plot_grouped_bars(
        finetune_values,
        title="Crystal-system distribution: baseline vs fine-tuned cohorts",
        output_path=finetune_path,
    )

    crysjepa_values = {
        group.label: _crystal_system_percentages(
            list(grouped_rows[group.label])
        )
        for group in CRYSJEPA_COMPARISON_GROUPS
    }
    crysjepa_path = output_root / "03_crystal_system_crysjepa.png"
    _plot_grouped_bars(
        crysjepa_values,
        title="Crystal-system distribution: Crys-JEPA Base vs Refined",
        output_path=crysjepa_path,
    )
    return (core_path, finetune_path, crysjepa_path)


STRUCTURAL_METRICS = [
    (
        "density",
        "Density distribution",
        "Density (g cm$^{-3}$)",
        False,
        "04_density_distribution.png",
    ),
    (
        "volume_per_atom",
        "Volume-per-site distribution",
        "Volume per site ($\\AA^3$/site)",
        True,
        "05_volume_per_site_distribution.png",
    ),
    (
        "n_atoms",
        "Sites-per-unit-cell distribution",
        "Sites per unit cell",
        True,
        "06_sites_per_cell_distribution.png",
    ),
]


def structural_label(label: str) -> str:
    return label.replace(" ", "\n", 1)


def _write_structural_summary(groups, output_dir: Path) -> Path:
    import pandas as pd

    rows = []
    for label, group in groups:
        for metric, *_ in STRUCTURAL_METRICS:
            values = pd.to_numeric(
                group[metric],
                errors="coerce",
            ).dropna()

            if values.empty:
                raise RuntimeError(f"No numeric values for {label}: {metric}")

            rows.append(
                {
                    "group": label.replace("\n", " "),
                    "metric": metric,
                    "count": int(values.size),
                    "mean": float(values.mean()),
                    "median": float(values.median()),
                    "q05": float(values.quantile(0.05)),
                    "q25": float(values.quantile(0.25)),
                    "q75": float(values.quantile(0.75)),
                    "q95": float(values.quantile(0.95)),
                    "min": float(values.min()),
                    "max": float(values.max()),
                }
            )

    output_path = output_dir / "structural_distribution_summary.csv"
    pd.DataFrame(rows).to_csv(output_path, index=False)
    return output_path


def _plot_structural_metric(
    groups,
    *,
    metric: str,
    title: str,
    ylabel: str,
    log_y: bool,
    filename: str,
    output_dir: Path,
) -> Path:
    import matplotlib.pyplot as plt
    import pandas as pd

    from mvpipeline.analysis.plotting import save_figure

    labels = []
    values = []

    for label, group in groups:
        numeric = pd.to_numeric(
            group[metric],
            errors="coerce",
        ).dropna()

        if numeric.empty:
            raise RuntimeError(f"No numeric values for {label}: {metric}")

        labels.append(f"{label}\n(n={len(numeric)})")
        values.append(numeric.to_numpy())

    fig, ax = plt.subplots(figsize=(13.5, 6.5))
    fig.patch.set_facecolor("white")

    ax.boxplot(
        values,
        tick_labels=labels,
        patch_artist=False,
        showfliers=True,
        flierprops={
            "marker": ".",
            "markersize": 2.5,
            "alpha": 0.25,
        },
        medianprops={
            "linewidth": 1.6,
        },
    )

    if log_y:
        ax.set_yscale("log")

    ax.set_title(title, pad=12)
    ax.set_ylabel(ylabel)
    ax.grid(
        axis="y",
        linestyle="--",
        linewidth=0.6,
        alpha=0.35,
    )
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", labelsize=9)

    fig.tight_layout()
    output_path = output_dir / filename
    save_figure(fig, output_path)
    plt.close(fig)
    return output_path


def generate_structural_distribution_figures(
    input_csv: str | Path,
    output_dir: str | Path,
) -> tuple[Path, ...]:
    import matplotlib

    matplotlib.use("Agg")
    import pandas as pd

    from mvpipeline.analysis.plotting import (
        STANDARD_PLOT_GROUPS,
        build_plot_groups,
        validate_unified_analysis_rows,
    )

    input_path = Path(input_csv)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    df = _read_analysis_v1_dataframe(input_path)
    validate_unified_analysis_rows(
        df,
        required_columns=("density", "volume_per_atom", "n_atoms"),
    )
    groups = [
        (structural_label(group.label), pd.DataFrame(group_rows))
        for group, group_rows in build_plot_groups(
            df,
            groups=STANDARD_PLOT_GROUPS,
        )
    ]
    outputs = [_write_structural_summary(groups, output_root)]

    for metric, title, ylabel, log_y, filename in STRUCTURAL_METRICS:
        outputs.append(
            _plot_structural_metric(
                groups,
                metric=metric,
                title=title,
                ylabel=ylabel,
                log_y=log_y,
                filename=filename,
                output_dir=output_root,
            )
        )
    return tuple(outputs)


def generate_compound_class_heatmap(
    input_csv: str | Path,
    output_dir: str | Path,
) -> tuple[Path, ...]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    from mvpipeline.analysis.plotting import (
        STANDARD_PLOT_GROUPS,
        build_plot_groups,
        save_figure,
        validate_unified_analysis_rows,
    )

    output_root = Path(output_dir)
    df = _read_analysis_v1_dataframe(input_csv)
    validate_unified_analysis_rows(
        df,
        required_columns=("compound_class",),
    )

    top = df["compound_class"].value_counts().head(10).index.tolist()
    plot_rows = []
    for group, group_rows in build_plot_groups(
        df,
        groups=STANDARD_PLOT_GROUPS,
    ):
        for row in group_rows:
            record = dict(row)
            record["plot_group"] = group.label
            plot_rows.append(record)
    df = pd.DataFrame(plot_rows)
    df["compound_class_plot"] = df["compound_class"].where(
        df["compound_class"].isin(top),
        "Other",
    )
    group_order = [group.label for group in STANDARD_PLOT_GROUPS]

    table = pd.crosstab(
        df["plot_group"],
        df["compound_class_plot"],
        normalize="index",
    ) * 100.0
    columns = top + ["Other"]
    table = table.reindex(index=group_order, columns=columns, fill_value=0.0)

    output_root.mkdir(parents=True, exist_ok=True)
    csv_out = output_root / "compound_class_distribution_percent.csv"
    table.to_csv(csv_out)

    fig, ax = plt.subplots(figsize=(15, 6.8))
    image = ax.imshow(table.values, aspect="auto", vmin=0)

    ax.set_xticks(range(len(columns)))
    ax.set_xticklabels(columns, rotation=40, ha="right")
    ax.set_yticks(range(len(group_order)))
    ax.set_yticklabels(group_order)
    ax.set_title("Compound-class distribution across generated cohorts", pad=12)

    for row_index in range(table.shape[0]):
        for column_index in range(table.shape[1]):
            value = table.iat[row_index, column_index]
            if value >= 2.0:
                ax.text(
                    column_index,
                    row_index,
                    f"{value:.1f}",
                    ha="center",
                    va="center",
                    fontsize=8,
                )

    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("Share of cohort (%)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    png_out = output_root / "07_compound_class_heatmap.png"
    save_figure(fig, png_out)
    plt.close(fig)
    return (csv_out, png_out)


def generate_3d_4f_fraction_figure(
    input_csv: str | Path,
    output_dir: str | Path,
) -> tuple[Path, ...]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    from mvpipeline.analysis.plotting import (
        STANDARD_PLOT_GROUPS,
        bool_series_values,
        build_plot_groups,
        save_figure,
        validate_unified_analysis_rows,
    )

    output_root = Path(output_dir)
    df = _read_analysis_v1_dataframe(input_csv)
    validate_unified_analysis_rows(
        df,
        required_columns=("contains_3d", "contains_4f"),
    )

    rows = []
    for group, group_rows in build_plot_groups(
        df,
        groups=STANDARD_PLOT_GROUPS,
    ):
        rows.append(
            {
                "group": group.label,
                "n": len(group_rows),
                "contains_3d_percent": (
                    100.0 * np.mean(
                        bool_series_values(
                            row["contains_3d"] for row in group_rows
                        )
                    )
                ),
                "contains_4f_percent": (
                    100.0 * np.mean(
                        bool_series_values(
                            row["contains_4f"] for row in group_rows
                        )
                    )
                ),
            }
        )

    summary = pd.DataFrame(rows)
    output_root.mkdir(parents=True, exist_ok=True)
    csv_out = output_root / "3d_4f_fraction_by_cohort.csv"
    summary.to_csv(csv_out, index=False)

    x = np.arange(len(summary))
    width = 0.36
    fig, ax = plt.subplots(figsize=(13.5, 6.5))
    bars3d = ax.bar(
        x - width / 2,
        summary["contains_3d_percent"],
        width,
        label="Contains 3d element",
    )
    bars4f = ax.bar(
        x + width / 2,
        summary["contains_4f_percent"],
        width,
        label="Contains 4f element",
    )

    for bars in (bars3d, bars4f):
        for bar in bars:
            value = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 1.2,
                f"{value:.1f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    ax.set_title("3d- and 4f-containing structures by cohort", pad=12)
    ax.set_ylabel("Share of cohort (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(summary["group"], rotation=30, ha="right")
    ax.set_ylim(0, 110)
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False)
    fig.tight_layout()
    png_out = output_root / "08_3d_4f_fraction_by_cohort.png"
    save_figure(fig, png_out)
    plt.close(fig)
    return (csv_out, png_out)


def generate_magnetic_screening_fraction_figure(
    input_csv: str | Path,
    output_dir: str | Path,
) -> tuple[Path, ...]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    from mvpipeline.analysis.plotting import (
        STANDARD_PLOT_GROUPS,
        build_plot_groups,
        save_figure,
        validate_unified_analysis_rows,
    )

    output_root = Path(output_dir)
    df = _read_analysis_v1_dataframe(input_csv)
    validate_unified_analysis_rows(
        df,
        required_columns=("magnetic_screening_element_fraction",),
    )

    labels = []
    values = []
    summary_rows = []

    for group, group_rows in build_plot_groups(
        df,
        groups=STANDARD_PLOT_GROUPS,
    ):
        group_df = pd.DataFrame(group_rows)
        numeric = pd.to_numeric(
            group_df["magnetic_screening_element_fraction"],
            errors="coerce",
        ).dropna()
        if numeric.empty:
            raise RuntimeError(f"No values for {group.label}")
        labels.append(f"{group.label}\n(n={len(numeric)})")
        values.append(numeric.to_numpy())
        summary_rows.append(
            {
                "group": group.label,
                "n": len(numeric),
                "mean": numeric.mean(),
                "median": numeric.median(),
                "q05": numeric.quantile(0.05),
                "q25": numeric.quantile(0.25),
                "q75": numeric.quantile(0.75),
                "q95": numeric.quantile(0.95),
            }
        )

    output_root.mkdir(parents=True, exist_ok=True)
    summary = pd.DataFrame(summary_rows)
    csv_out = output_root / "magnetic_screening_element_fraction_summary.csv"
    summary.to_csv(csv_out, index=False)

    fig, ax = plt.subplots(figsize=(13.5, 6.5))
    ax.boxplot(
        values,
        tick_labels=labels,
        showfliers=True,
        flierprops={"marker": ".", "markersize": 2.5, "alpha": 0.25},
    )
    ax.set_title("Magnetic-screening element fraction by cohort", pad=12)
    ax.set_ylabel("Atomic fraction of screening elements")
    ax.set_ylim(-0.03, 1.03)
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", labelsize=9)
    fig.tight_layout()
    png_out = output_root / "09_magnetic_screening_element_fraction.png"
    save_figure(fig, png_out)
    plt.close(fig)
    return (csv_out, png_out)


def generate_dxmag_predicted_moment_figure(
    input_csv: str | Path,
    output_dir: str | Path,
) -> tuple[Path, ...]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    from mvpipeline.analysis.plotting import (
        STANDARD_PLOT_GROUPS,
        build_plot_groups,
        save_figure,
        validate_unified_analysis_rows,
    )

    output_root = Path(output_dir)
    png_out = output_root / "10_dxmag_predicted_moment_distribution.png"
    csv_out = output_root / "dxmag_predicted_moment_summary.csv"

    output_root.mkdir(parents=True, exist_ok=True)

    df = _read_analysis_v1_dataframe(input_csv)
    validate_unified_analysis_rows(
        df,
        required_columns=("magnetism_predicted_moment_value",),
    )
    df["moment"] = pd.to_numeric(
        df["magnetism_predicted_moment_value"],
        errors="coerce",
    )

    if df["moment"].isna().any():
        raise RuntimeError("Found NaN in magnetism_predicted_moment_value")

    plot_data = []
    summary_rows = []

    for group, group_rows in build_plot_groups(
        df,
        groups=STANDARD_PLOT_GROUPS,
    ):
        group_df = pd.DataFrame(group_rows)

        if group_df.empty:
            raise RuntimeError(f"Empty group: {group.label}")

        values = group_df["moment"].astype(float)
        plot_data.append(values.tolist())

        summary_rows.append(
            {
                "group": group.label,
                "n": int(values.count()),
                "mean": float(values.mean()),
                "median": float(values.median()),
                "q01": float(values.quantile(0.01)),
                "q05": float(values.quantile(0.05)),
                "q25": float(values.quantile(0.25)),
                "q75": float(values.quantile(0.75)),
                "q95": float(values.quantile(0.95)),
                "q99": float(values.quantile(0.99)),
                "min": float(values.min()),
                "max": float(values.max()),
                "negative_n": int((values < 0).sum()),
                "negative_pct": float(100.0 * (values < 0).mean()),
            }
        )

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(csv_out, index=False)

    fig, ax = plt.subplots(figsize=(14, 7.5))
    ax.boxplot(
        plot_data,
        tick_labels=[group.label for group in STANDARD_PLOT_GROUPS],
        showfliers=False,
        widths=0.6,
        patch_artist=False,
    )

    ax.axhline(0.0, linewidth=1.0, linestyle="--")
    ax.set_ylabel(DXMAG_PREDICTED_MOMENT_YLABEL)
    ax.set_title("DXMag predicted moment distribution across MagGenBench cohorts")
    ax.tick_params(axis="x", rotation=35)

    fig.tight_layout()
    save_figure(fig, png_out)
    plt.close(fig)
    return (csv_out, png_out)


ANALYSIS_V1_FIGURE_GENERATORS = (
    generate_crystal_system_figures,
    generate_structural_distribution_figures,
    generate_compound_class_heatmap,
    generate_3d_4f_fraction_figure,
    generate_magnetic_screening_fraction_figure,
    generate_dxmag_predicted_moment_figure,
)


def generate_analysis_v1_figures(
    *,
    input_csv: str | Path,
    output_dir: str | Path,
    force: bool = False,
) -> AnalysisV1FigureReport:
    input_path = Path(input_csv)
    output_root = Path(output_dir)
    if not input_path.is_file():
        raise FileNotFoundError(input_path)

    prepare_analysis_v1_figure_outputs(output_root, force=force)

    output_files: list[Path] = []
    for generator in ANALYSIS_V1_FIGURE_GENERATORS:
        output_files.extend(generator(input_path, output_root))

    expected = owned_analysis_v1_figure_paths(output_root)
    if tuple(output_files) != expected:
        raise RuntimeError(
            "Analysis v1 figure generator output list differs from "
            "the owned filename manifest."
        )
    missing = [
        path for path in expected
        if not path.is_file()
    ]
    if missing:
        raise RuntimeError(
            f"Analysis v1 figure generation missed files: {missing}"
        )

    return AnalysisV1FigureReport(
        input_csv=input_path,
        output_dir=output_root,
        output_files=expected,
    )
