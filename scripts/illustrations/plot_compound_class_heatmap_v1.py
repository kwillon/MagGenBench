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
        required_columns=("compound_class",),
    )

    top = df["compound_class"].value_counts().head(10).index.tolist()
    plot_rows = []
    for group, group_rows in build_plot_groups(df, groups=STANDARD_PLOT_GROUPS):
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

    output_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(output_dir / "compound_class_distribution_percent.csv")

    fig, ax = plt.subplots(figsize=(15, 6.8))
    image = ax.imshow(table.values, aspect="auto", vmin=0)

    ax.set_xticks(range(len(columns)))
    ax.set_xticklabels(columns, rotation=40, ha="right")
    ax.set_yticks(range(len(group_order)))
    ax.set_yticklabels(group_order)
    ax.set_title("Compound-class distribution across generated cohorts", pad=12)

    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            value = table.iat[i, j]
            if value >= 2.0:
                ax.text(j, i, f"{value:.1f}", ha="center", va="center", fontsize=8)

    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("Share of cohort (%)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    save_figure(fig, output_dir / "07_compound_class_heatmap.png")
    plt.close(fig)

    print(table.round(2).to_string())
    print("OUTPUT:", output_dir / "07_compound_class_heatmap.png")
    print("PLOT_COMPOUND_CLASS_HEATMAP: PASSED")

if __name__ == "__main__":
    main()
