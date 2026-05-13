from pathlib import Path

import pandas as pd # type: ignore
import matplotlib.pyplot as plt # type: ignore


ROOT = Path("/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench")

INPUT_CSV = ROOT / "tables" / "master_structures.downsampled.with_status.classes.clean_v2.fixed_paths.csv"
FIG_DIR = ROOT / "figures" / "composition"
FIG_DIR.mkdir(parents=True, exist_ok=True)


MODEL_LABELS = {
    "cdvae": "Con-CDVAE",
    "concdvae": "Con-CDVAE",
    "mg": "MatterGen",
    "mattergen": "MatterGen",
    "cf": "CrystalFormer",
    "crystalformer": "CrystalFormer",
    "cllm": "CrystalLLM",
    "crystalllm": "CrystalLLM",
    "crystallm": "CrystalLLM",
}


def set_stats_paper_style():
    plt.rcParams.update({
        "figure.dpi": 150,
        "savefig.dpi": 600,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "axes.linewidth": 0.9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    })


def normalize_model(x):
    x = str(x).strip().lower()
    return MODEL_LABELS.get(x, x)


def collapse_small_classes(series, min_fraction=0.025, other_label="Other"):
    """
    Collapse tiny classes into Other for readable pie charts.
    """
    total = series.sum()

    if total == 0:
        return series

    large = series[series / total >= min_fraction]
    small = series[series / total < min_fraction]

    if len(small) > 0:
        large.loc[other_label] = small.sum()

    return large.sort_values(ascending=False)


def save_fig(fig, name):
    png = FIG_DIR / f"{name}.png"
    pdf = FIG_DIR / f"{name}.pdf"
    svg = FIG_DIR / f"{name}.svg"

    fig.savefig(png, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(svg, bbox_inches="tight")

    print(f"Saved: {png}")
    print(f"Saved: {pdf}")
    print(f"Saved: {svg}")


def plot_overall_bar(df):
    counts = df["compound_class"].value_counts().sort_values(ascending=True)

    fig_h = max(4.5, 0.38 * len(counts))
    fig, ax = plt.subplots(figsize=(7.2, fig_h))

    ax.barh(counts.index, counts.values)

    ax.set_xlabel("Number of generated structures")
    ax.set_ylabel("")
    ax.set_title("Distribution of generated compounds by chemical class")

    total = counts.sum()

    for i, value in enumerate(counts.values):
        pct = 100 * value / total if total else 0
        ax.text(
            value,
            i,
            f" {value} ({pct:.1f}%)",
            va="center",
            fontsize=8,
        )

    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()

    save_fig(fig, "compound_class_distribution_overall_bar")
    plt.close(fig)


def plot_overall_pie(df):
    counts = df["compound_class"].value_counts()
    counts = collapse_small_classes(counts, min_fraction=0.025)

    fig, ax = plt.subplots(figsize=(6.4, 6.0))

    wedges, texts, autotexts = ax.pie(
        counts.values,
        labels=counts.index,
        autopct=lambda p: f"{p:.1f}%" if p >= 3 else "",
        startangle=90,
        counterclock=False,
        wedgeprops={"linewidth": 0.8, "edgecolor": "white"},
        textprops={"fontsize": 8},
    )

    ax.set_title("Chemical class distribution of generated structures")
    ax.axis("equal")

    fig.tight_layout()

    save_fig(fig, "compound_class_distribution_overall_pie")
    plt.close(fig)


def plot_by_model_stacked_bar(df):
    if "model_short" in df.columns:
        model_col = "model_short"
    elif "model_name" in df.columns:
        model_col = "model_name"
    else:
        print("No model column found; skipping by-model plot.")
        return

    data = df.copy()
    data["model_label"] = data[model_col].map(normalize_model)

    tab = pd.crosstab(data["model_label"], data["compound_class"])

    # Keep classes ordered by total abundance.
    tab = tab[tab.sum(axis=0).sort_values(ascending=False).index]

    # Convert to percent per model.
    tab_pct = tab.div(tab.sum(axis=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(8.2, 4.8))

    bottom = None

    for col in tab_pct.columns:
        values = tab_pct[col].values
        ax.bar(
            tab_pct.index,
            values,
            bottom=bottom,
            label=col,
        )
        if bottom is None:
            bottom = values
        else:
            bottom = bottom + values

    ax.set_ylabel("Share within model (%)")
    ax.set_xlabel("")
    ax.set_title("Chemical class distribution by generative model")
    ax.set_ylim(0, 100)

    ax.legend(
        title="Compound class",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        frameon=False,
    )

    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()

    save_fig(fig, "compound_class_distribution_by_model_stacked_percent")
    plt.close(fig)


def plot_validated_vs_rejected(df):
    if "status" not in df.columns:
        print("No status column found; skipping validated/rejected plot.")
        return

    data = df[df["status"].isin(["validated", "rejected"])].copy()

    if data.empty:
        print("No validated/rejected rows found; skipping status plot.")
        return

    tab = pd.crosstab(data["compound_class"], data["status"])

    for col in ["validated", "rejected"]:
        if col not in tab.columns:
            tab[col] = 0

    tab["total"] = tab["validated"] + tab["rejected"]
    tab = tab.sort_values("total", ascending=True)

    fig_h = max(4.5, 0.42 * len(tab))
    fig, ax = plt.subplots(figsize=(7.2, fig_h))

    ax.barh(tab.index, tab["validated"], label="Validated")
    ax.barh(tab.index, tab["rejected"], left=tab["validated"], label="Rejected")

    ax.set_xlabel("Number of structures")
    ax.set_ylabel("")
    ax.set_title("Validated and rejected structures by chemical class")
    ax.legend(frameon=False)

    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()

    save_fig(fig, "compound_class_validated_vs_rejected")
    plt.close(fig)


def plot_by_model_and_status(df):
    if "status" not in df.columns:
        return

    if "model_short" in df.columns:
        model_col = "model_short"
    elif "model_name" in df.columns:
        model_col = "model_name"
    else:
        return

    data = df.copy()
    data["model_label"] = data[model_col].map(normalize_model)

    for status in ["validated", "rejected"]:
        sub = data[data["status"] == status]

        if sub.empty:
            continue

        tab = pd.crosstab(sub["model_label"], sub["compound_class"])
        tab = tab[tab.sum(axis=0).sort_values(ascending=False).index]
        tab_pct = tab.div(tab.sum(axis=1), axis=0) * 100

        fig, ax = plt.subplots(figsize=(8.2, 4.8))

        bottom = None

        for col in tab_pct.columns:
            values = tab_pct[col].values
            ax.bar(
                tab_pct.index,
                values,
                bottom=bottom,
                label=col,
            )
            if bottom is None:
                bottom = values
            else:
                bottom = bottom + values

        ax.set_ylabel("Share within model (%)")
        ax.set_xlabel("")
        ax.set_ylim(0, 100)
        ax.set_title(f"Chemical class distribution by model: {status}")

        ax.legend(
            title="Compound class",
            bbox_to_anchor=(1.02, 1),
            loc="upper left",
            frameon=False,
        )

        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()

        save_fig(fig, f"compound_class_by_model_{status}_stacked_percent")
        plt.close(fig)


def main():
    set_stats_paper_style()

    df = pd.read_csv(INPUT_CSV, low_memory=False)

    if "compound_class" not in df.columns:
        raise ValueError("Column compound_class was not found. Run add_compound_class.py first.")

    df["compound_class"] = df["compound_class"].fillna("unknown").astype(str)

    print("Input:")
    print(INPUT_CSV)
    print(f"Rows: {len(df)}")

    print("\nCompound class counts:")
    print(df["compound_class"].value_counts())

    plot_overall_bar(df)
    plot_overall_pie(df)
    plot_by_model_stacked_bar(df)
    plot_validated_vs_rejected(df)
    plot_by_model_and_status(df)

    print("\nDone.")
    print(f"Figures saved to: {FIG_DIR}")


if __name__ == "__main__":
    main()