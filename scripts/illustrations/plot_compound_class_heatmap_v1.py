from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "runs" / "analysis_v1" / "unified_analysis_v1.csv"
OUTDIR = ROOT / "figures" / "unified_analysis_v1"

GROUP_ORDER = [
    "MatterGen baseline",
    "MatterGen fine-tuned",
    "Con-CDVAE baseline",
    "Con-CDVAE fine-tuned",
    "CrystalFormer baseline",
    "CrystaLLM baseline",
    "Crys-JEPA Base",
    "Crys-JEPA Refined",
]

def main() -> None:
    df = pd.read_csv(INPUT, low_memory=False)
    if len(df) != 10684:
        raise RuntimeError(f"Expected 10684 rows, got {len(df)}")

    df["plot_group"] = df["analysis_cohort"]
    mask = df["analysis_cohort"].eq("baseline_master")
    df.loc[mask, "plot_group"] = df.loc[mask, "analysis_family"] + " baseline"
    df["plot_group"] = df["plot_group"].replace({
        "mattergen_finetuned": "MatterGen fine-tuned",
        "concdvae_finetuned": "Con-CDVAE fine-tuned",
        "crysjepa_base": "Crys-JEPA Base",
        "crysjepa_refined": "Crys-JEPA Refined",
    })

    top = df["compound_class"].value_counts().head(10).index.tolist()
    df["compound_class_plot"] = df["compound_class"].where(
        df["compound_class"].isin(top),
        "Other",
    )

    table = pd.crosstab(
        df["plot_group"],
        df["compound_class_plot"],
        normalize="index",
    ) * 100.0
    columns = top + ["Other"]
    table = table.reindex(index=GROUP_ORDER, columns=columns, fill_value=0.0)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUTDIR / "compound_class_distribution_percent.csv")

    fig, ax = plt.subplots(figsize=(15, 6.8))
    image = ax.imshow(table.values, aspect="auto", vmin=0)

    ax.set_xticks(range(len(columns)))
    ax.set_xticklabels(columns, rotation=40, ha="right")
    ax.set_yticks(range(len(GROUP_ORDER)))
    ax.set_yticklabels(GROUP_ORDER)
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
    fig.savefig(OUTDIR / "07_compound_class_heatmap.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(table.round(2).to_string())
    print("OUTPUT:", OUTDIR / "07_compound_class_heatmap.png")
    print("PLOT_COMPOUND_CLASS_HEATMAP: PASSED")

if __name__ == "__main__":
    main()
