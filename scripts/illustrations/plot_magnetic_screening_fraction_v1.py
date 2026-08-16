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

def main() -> None:
    root = repository_root_from_script(__file__)
    input_path = unified_analysis_v1_path(root)
    output_dir = unified_analysis_figure_dir(root)

    df = pd.read_csv(input_path, low_memory=False)
    validate_unified_analysis_rows(
        df,
        required_columns=("magnetic_screening_element_fraction",),
    )

    labels = []
    values = []
    summary_rows = []

    for group, group_rows in build_plot_groups(df, groups=STANDARD_PLOT_GROUPS):
        group_df = pd.DataFrame(group_rows)
        numeric = pd.to_numeric(group_df["magnetic_screening_element_fraction"], errors="coerce").dropna()
        if numeric.empty:
            raise RuntimeError(f"No values for {group.label}")
        labels.append(f"{group.label}\n(n={len(numeric)})")
        values.append(numeric.to_numpy())
        summary_rows.append({
            "group": group.label,
            "n": len(numeric),
            "mean": numeric.mean(),
            "median": numeric.median(),
            "q05": numeric.quantile(0.05),
            "q25": numeric.quantile(0.25),
            "q75": numeric.quantile(0.75),
            "q95": numeric.quantile(0.95),
        })

    output_dir.mkdir(parents=True, exist_ok=True)
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(output_dir / "magnetic_screening_element_fraction_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(13.5, 6.5))
    ax.boxplot(values, tick_labels=labels, showfliers=True, flierprops={"marker": ".", "markersize": 2.5, "alpha": 0.25})
    ax.set_title("Magnetic-screening element fraction by cohort", pad=12)
    ax.set_ylabel("Atomic fraction of screening elements")
    ax.set_ylim(-0.03, 1.03)
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", labelsize=9)
    fig.tight_layout()
    save_figure(fig, output_dir / "09_magnetic_screening_element_fraction.png")
    plt.close(fig)

    print(summary.round(3).to_string(index=False))
    print("OUTPUT:", output_dir / "09_magnetic_screening_element_fraction.png")
    print("PLOT_MAGNETIC_SCREENING_ELEMENT_FRACTION: PASSED")

if __name__ == "__main__":
    main()
