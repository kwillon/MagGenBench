from __future__ import annotations

from collections import Counter

import matplotlib.pyplot as plt

from mvpipeline.analysis.plotting import (
    BASELINE_PLOT_GROUPS,
    CRYSTAL_SYSTEM_ORDER,
    CRYSJEPA_COMPARISON_GROUPS,
    FINETUNING_COMPARISON_GROUPS,
    apply_unified_plot_style,
    build_plot_groups,
    load_unified_analysis_rows,
    repository_root_from_script,
    save_figure,
    unified_analysis_figure_dir,
    unified_analysis_v1_path,
    validate_unified_analysis_rows,
)


def crystal_system_percentages(rows: list[dict[str, str]]) -> dict[str, float]:
    total = len(rows)
    if total == 0:
        raise RuntimeError("Cannot compute percentages for empty cohort.")

    counts = Counter(r["crystal_system"].strip() for r in rows)
    return {
        cs: 100.0 * counts.get(cs, 0) / total
        for cs in CRYSTAL_SYSTEM_ORDER
    }


def plot_grouped_bars(
    values_by_label: dict[str, dict[str, float]],
    *,
    title: str,
    output_path: Path,
) -> None:
    labels = list(values_by_label)
    x = list(range(len(CRYSTAL_SYSTEM_ORDER)))
    width = 0.8 / max(len(labels), 1)

    fig, ax = plt.subplots()

    for i, label in enumerate(labels):
        offsets = [xi - 0.4 + width / 2 + i * width for xi in x]
        heights = [values_by_label[label][cs] for cs in CRYSTAL_SYSTEM_ORDER]
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


def main() -> None:
    root = repository_root_from_script(__file__)
    input_path = unified_analysis_v1_path(root)
    output_dir = unified_analysis_figure_dir(root)

    apply_unified_plot_style()
    rows = load_unified_analysis_rows(input_path)
    validate_unified_analysis_rows(
        rows,
        required_columns=("crystal_system", "symmetry_status"),
    )

    missing = [r for r in rows if not r.get("crystal_system", "").strip()]
    if missing:
        raise RuntimeError(f"Missing crystal_system rows: {len(missing)}")

    bad_symmetry = [
        r for r in rows
        if (r.get("symmetry_status", "").strip() or "") != "ok"
    ]
    if bad_symmetry:
        raise RuntimeError(f"Non-ok symmetry_status rows: {len(bad_symmetry)}")

    grouped_rows = {
        group.label: group_rows
        for group, group_rows in build_plot_groups(rows)
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Core baselines
    baseline_values = {
        group.analysis_family: crystal_system_percentages(
            list(grouped_rows[group.label])
        )
        for group in BASELINE_PLOT_GROUPS
    }
    plot_grouped_bars(
        baseline_values,
        title="Crystal-system distribution across baseline models",
        output_path=output_dir / "01_crystal_system_core_baseline.png",
    )

    # 2. Fine-tuning comparison
    finetune_values = {}
    for group in FINETUNING_COMPARISON_GROUPS:
        finetune_values[group.label] = crystal_system_percentages(
            list(grouped_rows[group.label])
        )

    plot_grouped_bars(
        finetune_values,
        title="Crystal-system distribution: baseline vs fine-tuned cohorts",
        output_path=output_dir / "02_crystal_system_finetuning.png",
    )

    # 3. Crys-JEPA comparison
    crysjepa_values = {
        group.label: crystal_system_percentages(
            list(grouped_rows[group.label])
        )
        for group in CRYSJEPA_COMPARISON_GROUPS
    }
    plot_grouped_bars(
        crysjepa_values,
        title="Crystal-system distribution: Crys-JEPA Base vs Refined",
        output_path=output_dir / "03_crystal_system_crysjepa.png",
    )

    print("INPUT:", input_path)
    print("ROWS:", len(rows))
    print("OUTPUT_DIR:", output_dir)
    print("FILES:")
    for path in sorted(output_dir.glob("*.png")):
        print(" ", path)
    print("PLOT_UNIFIED_ANALYSIS_V1: PASSED")


if __name__ == "__main__":
    main()
