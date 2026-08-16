from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from mvpipeline.analysis.plotting import (
    STANDARD_PLOT_GROUPS,
    bool_series_values,
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
        required_columns=("contains_3d", "contains_4f"),
    )

    rows = []
    for group, group_rows in build_plot_groups(df, groups=STANDARD_PLOT_GROUPS):
        rows.append({
            "group": group.label,
            "n": len(group_rows),
            "contains_3d_percent": (
                100.0 * np.mean(
                    bool_series_values(row["contains_3d"] for row in group_rows)
                )
            ),
            "contains_4f_percent": (
                100.0 * np.mean(
                    bool_series_values(row["contains_4f"] for row in group_rows)
                )
            ),
        })

    summary = pd.DataFrame(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_dir / "3d_4f_fraction_by_cohort.csv", index=False)

    x = np.arange(len(summary))
    width = 0.36
    fig, ax = plt.subplots(figsize=(13.5, 6.5))
    bars3d = ax.bar(x - width/2, summary["contains_3d_percent"], width, label="Contains 3d element")
    bars4f = ax.bar(x + width/2, summary["contains_4f_percent"], width, label="Contains 4f element")

    for bars in (bars3d, bars4f):
        for bar in bars:
            value = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, value + 1.2, f"{value:.1f}", ha="center", va="bottom", fontsize=8)

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
    save_figure(fig, output_dir / "08_3d_4f_fraction_by_cohort.png")
    plt.close(fig)

    print(summary.round(2).to_string(index=False))
    print("OUTPUT:", output_dir / "08_3d_4f_fraction_by_cohort.png")
    print("PLOT_3D_4F_FRACTION: PASSED")

if __name__ == "__main__":
    main()
