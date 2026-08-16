from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from mvpipeline.analysis.plotting import (
    STANDARD_PLOT_GROUPS,
    build_plot_groups,
    repository_root_from_script,
    save_figure,
    unified_analysis_figure_dir,
    unified_analysis_v1_path,
    validate_unified_analysis_rows,
)

METRICS = [
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


def write_summary(groups, output_dir) -> None:
    rows = []

    for label, group in groups:
        for metric, *_ in METRICS:
            values = pd.to_numeric(
                group[metric],
                errors="coerce",
            ).dropna()

            if values.empty:
                raise RuntimeError(
                    f"No numeric values for {label}: {metric}"
                )

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

    pd.DataFrame(rows).to_csv(
        output_dir / "structural_distribution_summary.csv",
        index=False,
    )


def plot_metric(
    groups,
    *,
    metric: str,
    title: str,
    ylabel: str,
    log_y: bool,
    filename: str,
    output_dir,
) -> None:
    labels = []
    values = []

    for label, group in groups:
        numeric = pd.to_numeric(
            group[metric],
            errors="coerce",
        ).dropna()

        if numeric.empty:
            raise RuntimeError(
                f"No numeric values for {label}: {metric}"
            )

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
    save_figure(fig, output_dir / filename)
    plt.close(fig)


def main() -> None:
    root = repository_root_from_script(__file__)
    input_path = unified_analysis_v1_path(root)
    output_dir = unified_analysis_figure_dir(root)

    if not input_path.is_file():
        raise FileNotFoundError(input_path)

    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path, low_memory=False)
    validate_unified_analysis_rows(
        df,
        required_columns=("density", "volume_per_atom", "n_atoms"),
    )
    groups = [
        (structural_label(group.label), pd.DataFrame(group_rows))
        for group, group_rows in build_plot_groups(df, groups=STANDARD_PLOT_GROUPS)
    ]
    write_summary(groups, output_dir)

    for metric, title, ylabel, log_y, filename in METRICS:
        plot_metric(
            groups,
            metric=metric,
            title=title,
            ylabel=ylabel,
            log_y=log_y,
            filename=filename,
            output_dir=output_dir,
        )

    print("INPUT:", input_path)
    print("ROWS:", len(df))
    print("OUTPUT_DIR:", output_dir)
    print(
        "OUTPUT:",
        output_dir / "structural_distribution_summary.csv",
    )

    for _, _, _, _, filename in METRICS:
        print("OUTPUT:", output_dir / filename)

    print("PLOT_STRUCTURAL_DISTRIBUTIONS_V1: PASSED")


if __name__ == "__main__":
    main()
