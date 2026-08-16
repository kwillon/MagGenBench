from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "runs" / "analysis_v1" / "unified_analysis_v1.csv"
OUTDIR = ROOT / "figures" / "unified_analysis_v1"

GROUPS = [
    ("MatterGen baseline", "baseline_master", "MatterGen"),
    ("MatterGen fine-tuned", "mattergen_finetuned", None),
    ("Con-CDVAE baseline", "baseline_master", "Con-CDVAE"),
    ("Con-CDVAE fine-tuned", "concdvae_finetuned", None),
    ("CrystalFormer baseline", "baseline_master", "CrystalFormer"),
    ("CrystaLLM baseline", "baseline_master", "CrystaLLM"),
    ("Crys-JEPA Base", "crysjepa_base", None),
    ("Crys-JEPA Refined", "crysjepa_refined", None),
]

def main() -> None:
    df = pd.read_csv(INPUT, low_memory=False)
    if len(df) != 10684:
        raise RuntimeError(f"Expected 10684 rows, got {len(df)}")

    labels = []
    values = []
    summary_rows = []

    for label, cohort, family in GROUPS:
        mask = df["analysis_cohort"].eq(cohort)
        if family is not None:
            mask &= df["analysis_family"].eq(family)
        group = df.loc[mask]
        numeric = pd.to_numeric(group["magnetic_screening_element_fraction"], errors="coerce").dropna()
        if numeric.empty:
            raise RuntimeError(f"No values for {label}")
        labels.append(f"{label}\n(n={len(numeric)})")
        values.append(numeric.to_numpy())
        summary_rows.append({
            "group": label,
            "n": len(numeric),
            "mean": numeric.mean(),
            "median": numeric.median(),
            "q05": numeric.quantile(0.05),
            "q25": numeric.quantile(0.25),
            "q75": numeric.quantile(0.75),
            "q95": numeric.quantile(0.95),
        })

    OUTDIR.mkdir(parents=True, exist_ok=True)
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUTDIR / "magnetic_screening_element_fraction_summary.csv", index=False)

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
    fig.savefig(OUTDIR / "09_magnetic_screening_element_fraction.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(summary.round(3).to_string(index=False))
    print("OUTPUT:", OUTDIR / "09_magnetic_screening_element_fraction.png")
    print("PLOT_MAGNETIC_SCREENING_ELEMENT_FRACTION: PASSED")

if __name__ == "__main__":
    main()
