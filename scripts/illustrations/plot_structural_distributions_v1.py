from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "runs" / "analysis_v1" / "unified_analysis_v1.csv"
OUTDIR = ROOT / "figures" / "unified_analysis_v1"

GROUPS = [
    ("MatterGen\nbaseline", "baseline_master", "MatterGen"),
    ("MatterGen\nfine-tuned", "mattergen_finetuned", None),
    ("Con-CDVAE\nbaseline", "baseline_master", "Con-CDVAE"),
    ("Con-CDVAE\nfine-tuned", "concdvae_finetuned", None),
    ("CrystalFormer\nbaseline", "baseline_master", "CrystalFormer"),
    ("CrystaLLM\nbaseline", "baseline_master", "CrystaLLM"),
    ("Crys-JEPA\nBase", "crysjepa_base", None),
    ("Crys-JEPA\nRefined", "crysjepa_refined", None),
]

METRICS = [
    (
        "density",
        "Density distribution",
        "Density (g cm$^{-3}$)",
        False,
        "04_density_distribution.png",
    ),
    (
        "volume_per_atom",
        "Volume-per-site distribution",
        "Volume per site ($\\AA^3$/site)",
        True,
        "05_volume_per_site_distribution.png",
    ),
    (
        "n_atoms",
        "Sites-per-unit-cell distribution",
        "Sites per unit cell",
        True,
        "06_sites_per_cell_distribution.png",
    ),
]


def subset(
    df: pd.DataFrame,
    cohort: str,
    family: str | None,
) -> pd.DataFrame:
    mask = df["analysis_cohort"].eq(cohort)
    if family is not None:
        mask &= df["analysis_family"].eq(family)

    out = df.loc[mask].copy()
    if out.empty:
        raise RuntimeError(
            f"Empty group: cohort={cohort!r}, family={family!r}"
        )
    return out


def prepare_groups(df: pd.DataFrame):
    prepared = []

    for label, cohort, family in GROUPS:
        group = subset(df, cohort, family)
        prepared.append((label, group))

    return prepared


def write_summary(groups) -> None:
    rows = []

    for label, group in groups:
        for metric, *_ in METRICS:
            values = pd.to_numeric(
                group[metric],
                errors="coerce",
            ).dropna()

            if values.empty:
                raise RuntimeError(
                    f"No numeric values for {label}: {metric}"
                )

            rows.append(
                {
                    "group": label.replace("\n", " "),
                    "metric": metric,
                    "count": int(values.size),
                    "mean": float(values.mean()),
                    "median": float(values.median()),
                    "q05": float(values.quantile(0.05)),
                    "q25": float(values.quantile(0.25)),
                    "q75": float(values.quantile(0.75)),
                    "q95": float(values.quantile(0.95)),
                    "min": float(values.min()),
                    "max": float(values.max()),
                }
            )

    pd.DataFrame(rows).to_csv(
        OUTDIR / "structural_distribution_summary.csv",
        index=False,
    )


def plot_metric(
    groups,
    *,
    metric: str,
    title: str,
    ylabel: str,
    log_y: bool,
    filename: str,
) -> None:
    labels = []
    values = []

    for label, group in groups:
        numeric = pd.to_numeric(
            group[metric],
            errors="coerce",
        ).dropna()

        if numeric.empty:
            raise RuntimeError(
                f"No numeric values for {label}: {metric}"
            )

        labels.append(f"{label}\n(n={len(numeric)})")
        values.append(numeric.to_numpy())

    fig, ax = plt.subplots(figsize=(13.5, 6.5))
    fig.patch.set_facecolor("white")

    ax.boxplot(
        values,
        tick_labels=labels,
        patch_artist=False,
        showfliers=True,
        flierprops={
            "marker": ".",
            "markersize": 2.5,
            "alpha": 0.25,
        },
        medianprops={
            "linewidth": 1.6,
        },
    )

    if log_y:
        ax.set_yscale("log")

    ax.set_title(title, pad=12)
    ax.set_ylabel(ylabel)
    ax.grid(
        axis="y",
        linestyle="--",
        linewidth=0.6,
        alpha=0.35,
    )
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", labelsize=9)

    fig.tight_layout()
    fig.savefig(
        OUTDIR / filename,
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)


def main() -> None:
    if not INPUT.is_file():
        raise FileNotFoundError(INPUT)

    OUTDIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT, low_memory=False)

    required = {
        "analysis_cohort",
        "analysis_family",
        "density",
        "volume_per_atom",
        "n_atoms",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise RuntimeError(
            f"Missing required columns: {missing}"
        )

    if len(df) != 10684:
        raise RuntimeError(
            f"Expected 10684 unified rows, got {len(df)}"
        )

    groups = prepare_groups(df)
    write_summary(groups)

    for metric, title, ylabel, log_y, filename in METRICS:
        plot_metric(
            groups,
            metric=metric,
            title=title,
            ylabel=ylabel,
            log_y=log_y,
            filename=filename,
        )

    print("INPUT:", INPUT)
    print("ROWS:", len(df))
    print("OUTPUT_DIR:", OUTDIR)
    print(
        "OUTPUT:",
        OUTDIR / "structural_distribution_summary.csv",
    )

    for _, _, _, _, filename in METRICS:
        print("OUTPUT:", OUTDIR / filename)

    print("PLOT_STRUCTURAL_DISTRIBUTIONS_V1: PASSED")


if __name__ == "__main__":
    main()
