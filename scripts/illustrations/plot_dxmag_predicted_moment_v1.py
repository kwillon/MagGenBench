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

PNG_OUT = OUTDIR / "10_dxmag_predicted_moment_distribution.png"
CSV_OUT = OUTDIR / "dxmag_predicted_moment_summary.csv"


def select_group(
    df: pd.DataFrame,
    *,
    cohort: str,
    family: str | None,
) -> pd.DataFrame:
    x = df[df["analysis_cohort"] == cohort].copy()
    if family is not None:
        x = x[x["analysis_family"] == family].copy()
    return x


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT, low_memory=False)
    df["moment"] = pd.to_numeric(
        df["magnetism_predicted_moment_value"],
        errors="coerce",
    )

    if df["moment"].isna().any():
        raise RuntimeError("Found NaN in magnetism_predicted_moment_value")

    plot_data = []
    summary_rows = []

    for label, cohort, family in GROUPS:
        x = select_group(df, cohort=cohort, family=family)

        if x.empty:
            raise RuntimeError(f"Empty group: {label}")

        values = x["moment"].astype(float)

        plot_data.append(values.tolist())

        summary_rows.append(
            {
                "group": label,
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
    summary.to_csv(CSV_OUT, index=False)

    fig, ax = plt.subplots(figsize=(14, 7.5))

    ax.boxplot(
        plot_data,
        labels=[g[0] for g in GROUPS],
        showfliers=False,
        widths=0.6,
        patch_artist=False,
    )

    ax.axhline(0.0, linewidth=1.0, linestyle="--")
    ax.set_ylabel("DXMag predicted moment (μB/f.u.)")
    ax.set_title("DXMag predicted moment distribution across MagGenBench cohorts")
    ax.tick_params(axis="x", rotation=35)

    fig.tight_layout()
    fig.savefig(PNG_OUT, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(summary.round(3).to_string(index=False))
    print("OUTPUT:", PNG_OUT)
    print("OUTPUT:", CSV_OUT)
    print("PLOT_DXMAG_PREDICTED_MOMENT_V1: PASSED")


if __name__ == "__main__":
    main()
