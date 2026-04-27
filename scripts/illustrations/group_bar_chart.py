import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# -----------------------------
# Input data
# -----------------------------
data = [
    {
        "model": "Con-CDVAE",
        "validity_percent": 93.26315789473684,
        "magnetic_percent": 71.50112866817155,
        "novelty_percent": 100.0,
        "duplicate_percent": 0.05263157894736842,
    },
    {
        "model": "MatterGen",
        "validity_percent": 87.21052631578947,
        "magnetic_percent": 95.17199758599879,
        "novelty_percent": 97.40494870247435,
        "duplicate_percent": 4.842105263157895,
    },
    {
        "model": "CrystalFormer",
        "validity_percent": 54.73684210526316,
        "magnetic_percent": 62.01923076923077,
        "novelty_percent": 96.25,
        "duplicate_percent": 15.105263157894736,
    },
    {
        "model": "CrystaLLM",
        "validity_percent": 4.736842105263158,
        "magnetic_percent": 100.0,
        "novelty_percent": 100.0,
        "duplicate_percent": 54.21052631578947,
    },
]

df = pd.DataFrame(data)

# Optional: sort by validity
df = df.sort_values("validity_percent", ascending=False).reset_index(drop=True)


# -----------------------------
# Plot settings
# -----------------------------
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "font.size": 11,
    "axes.titlesize": 16,
    "axes.labelsize": 12,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "legend.fontsize": 10,
    "axes.linewidth": 0.8,
})

# Paper-like muted colors
colors = {
    "Validity %": "#4C78A8",
    "Magnetic %": "#F58518",
    "Novelty %": "#54A24B",
    "Duplicate %": "#E45756",
}


def add_value_labels(ax, bars, decimals=1, y_offset=1.2):
    """Add value labels above bars."""
    for bar in bars:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            h + y_offset,
            f"{h:.{decimals}f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )


# -----------------------------
# Grouped bar chart
# -----------------------------
fig, ax = plt.subplots(figsize=(11, 5.8))
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

x = np.arange(len(df))
width = 0.18

bars1 = ax.bar(
    x - 1.5 * width,
    df["validity_percent"],
    width,
    label="Validity %",
    color=colors["Validity %"],
    edgecolor="black",
    linewidth=0.4,
)

bars2 = ax.bar(
    x - 0.5 * width,
    df["magnetic_percent"],
    width,
    label="Magnetic %",
    color=colors["Magnetic %"],
    edgecolor="black",
    linewidth=0.4,
)

bars3 = ax.bar(
    x + 0.5 * width,
    df["novelty_percent"],
    width,
    label="Novelty %",
    color=colors["Novelty %"],
    edgecolor="black",
    linewidth=0.4,
)

bars4 = ax.bar(
    x + 1.5 * width,
    df["duplicate_percent"],
    width,
    label="Duplicate %",
    color=colors["Duplicate %"],
    edgecolor="black",
    linewidth=0.4,
)

# Labels above bars
add_value_labels(ax, bars1, decimals=1)
add_value_labels(ax, bars2, decimals=1)
add_value_labels(ax, bars3, decimals=1)
add_value_labels(ax, bars4, decimals=1)

# Axes / title
ax.set_title("Comparison of Main Ratios Across Generative Models", pad=14)
ax.set_ylabel("Percent")
ax.set_xticks(x)
ax.set_xticklabels(df["model"])
ax.set_ylim(0, 112)

# Grid: only horizontal, light
ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)
ax.set_axisbelow(True)

# Cleaner top/right spines
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# Legend OUTSIDE the axes so it never overlaps the plot
legend = ax.legend(
    loc="upper left",
    bbox_to_anchor=(1.01, 1.0),
    frameon=False,
    borderaxespad=0.0,
)

# Leave room on the right for legend
plt.tight_layout(rect=[0, 0, 0.82, 1])

# Save
plt.savefig("grouped_main_ratios_paper.png", bbox_inches="tight")
plt.show()