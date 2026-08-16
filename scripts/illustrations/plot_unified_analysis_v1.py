from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "runs" / "analysis_v1" / "unified_analysis_v1.csv"
OUTDIR = ROOT / "figures" / "unified_analysis_v1"

CRYSTAL_SYSTEM_ORDER = [
    "triclinic",
    "monoclinic",
    "orthorhombic",
    "tetragonal",
    "trigonal",
    "hexagonal",
    "cubic",
]

BASELINE_FAMILIES = [
    "MatterGen",
    "Con-CDVAE",
    "CrystalFormer",
    "CrystaLLM",
]

FINETUNE_COHORTS = [
    ("MatterGen baseline", "baseline_master", "MatterGen"),
    ("MatterGen fine-tuned", "mattergen_finetuned", None),
    ("Con-CDVAE baseline", "baseline_master", "Con-CDVAE"),
    ("Con-CDVAE fine-tuned", "concdvae_finetuned", None),
]

CRYSJEPA_COHORTS = [
    ("Crys-JEPA Base", "crysjepa_base"),
    ("Crys-JEPA Refined", "crysjepa_refined"),
]


def apply_paper_style() -> None:
    plt.rcParams.update(
        {
            "figure.figsize": (10, 6),
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "savefig.bbox": "tight",
            "savefig.dpi": 300,
            "font.size": 11,
        }
    )


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def require_ok_input(rows: list[dict[str, str]]) -> None:
    if not rows:
        raise RuntimeError("Unified analysis table is empty.")

    missing = [r for r in rows if not r.get("crystal_system", "").strip()]
    if missing:
        raise RuntimeError(f"Missing crystal_system rows: {len(missing)}")

    bad_symmetry = [
        r for r in rows
        if (r.get("symmetry_status", "").strip() or "") != "ok"
    ]
    if bad_symmetry:
        raise RuntimeError(f"Non-ok symmetry_status rows: {len(bad_symmetry)}")


def crystal_system_percentages(rows: list[dict[str, str]]) -> dict[str, float]:
    total = len(rows)
    if total == 0:
        raise RuntimeError("Cannot compute percentages for empty cohort.")

    counts = Counter(r["crystal_system"].strip() for r in rows)
    return {
        cs: 100.0 * counts.get(cs, 0) / total
        for cs in CRYSTAL_SYSTEM_ORDER
    }


def subset_baseline_family(
    rows: list[dict[str, str]],
    family: str,
) -> list[dict[str, str]]:
    out = [
        r for r in rows
        if r.get("analysis_cohort") == "baseline_master"
        and r.get("analysis_family") == family
    ]
    if not out:
        raise RuntimeError(f"Empty baseline subset for family: {family}")
    return out


def subset_cohort(
    rows: list[dict[str, str]],
    cohort: str,
) -> list[dict[str, str]]:
    out = [r for r in rows if r.get("analysis_cohort") == cohort]
    if not out:
        raise RuntimeError(f"Empty cohort: {cohort}")
    return out


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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path)
    plt.close(fig)


def main() -> None:
    apply_paper_style()
    rows = read_rows(INPUT)
    require_ok_input(rows)

    OUTDIR.mkdir(parents=True, exist_ok=True)

    # 1. Core baselines
    baseline_values = {
        family: crystal_system_percentages(subset_baseline_family(rows, family))
        for family in BASELINE_FAMILIES
    }
    plot_grouped_bars(
        baseline_values,
        title="Crystal-system distribution across baseline models",
        output_path=OUTDIR / "01_crystal_system_core_baseline.png",
    )

    # 2. Fine-tuning comparison
    finetune_values = {}
    for label, cohort, family in FINETUNE_COHORTS:
        if cohort == "baseline_master":
            subset = subset_baseline_family(rows, family)
        else:
            subset = subset_cohort(rows, cohort)
        finetune_values[label] = crystal_system_percentages(subset)

    plot_grouped_bars(
        finetune_values,
        title="Crystal-system distribution: baseline vs fine-tuned cohorts",
        output_path=OUTDIR / "02_crystal_system_finetuning.png",
    )

    # 3. Crys-JEPA comparison
    crysjepa_values = {
        label: crystal_system_percentages(subset_cohort(rows, cohort))
        for label, cohort in CRYSJEPA_COHORTS
    }
    plot_grouped_bars(
        crysjepa_values,
        title="Crystal-system distribution: Crys-JEPA Base vs Refined",
        output_path=OUTDIR / "03_crystal_system_crysjepa.png",
    )

    print("INPUT:", INPUT)
    print("ROWS:", len(rows))
    print("OUTPUT_DIR:", OUTDIR)
    print("FILES:")
    for path in sorted(OUTDIR.glob("*.png")):
        print(" ", path)
    print("PLOT_UNIFIED_ANALYSIS_V1: PASSED")


if __name__ == "__main__":
    main()
