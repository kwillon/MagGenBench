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
    png_out = output_dir / "10_dxmag_predicted_moment_distribution.png"
    csv_out = output_dir / "dxmag_predicted_moment_summary.csv"

    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path, low_memory=False)
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

    for group, group_rows in build_plot_groups(df, groups=STANDARD_PLOT_GROUPS):
        x = pd.DataFrame(group_rows)

        if x.empty:
            raise RuntimeError(f"Empty group: {group.label}")

        values = x["moment"].astype(float)

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
    ax.set_ylabel("DXMag predicted moment (μB/f.u.)")
    ax.set_title("DXMag predicted moment distribution across MagGenBench cohorts")
    ax.tick_params(axis="x", rotation=35)

    fig.tight_layout()
    save_figure(fig, png_out)
    plt.close(fig)

    print(summary.round(3).to_string(index=False))
    print("OUTPUT:", png_out)
    print("OUTPUT:", csv_out)
    print("PLOT_DXMAG_PREDICTED_MOMENT_V1: PASSED")


if __name__ == "__main__":
    main()
