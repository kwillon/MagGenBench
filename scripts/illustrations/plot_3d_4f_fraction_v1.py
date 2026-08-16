from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
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

def as_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin(["true", "1"])

def main() -> None:
    df = pd.read_csv(INPUT, low_memory=False)
    if len(df) != 10684:
        raise RuntimeError(f"Expected 10684 rows, got {len(df)}")

    rows = []
    for label, cohort, family in GROUPS:
        mask = df["analysis_cohort"].eq(cohort)
        if family is not None:
            mask &= df["analysis_family"].eq(family)
        group = df.loc[mask]
        if group.empty:
            raise RuntimeError(f"Empty group: {label}")
        rows.append({
            "group": label,
            "n": len(group),
            "contains_3d_percent": 100.0 * as_bool(group["contains_3d"]).mean(),
            "contains_4f_percent": 100.0 * as_bool(group["contains_4f"]).mean(),
        })

    summary = pd.DataFrame(rows)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUTDIR / "3d_4f_fraction_by_cohort.csv", index=False)

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
    fig.savefig(OUTDIR / "08_3d_4f_fraction_by_cohort.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(summary.round(2).to_string(index=False))
    print("OUTPUT:", OUTDIR / "08_3d_4f_fraction_by_cohort.png")
    print("PLOT_3D_4F_FRACTION: PASSED")

if __name__ == "__main__":
    main()
