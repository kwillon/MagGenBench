import matplotlib
matplotlib.use("Agg")

from pathlib import Path
from ast import literal_eval

import pandas as pd
import matplotlib.pyplot as plt
from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


MODEL_CSVS = {
    "Con-CDVAE": "/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench/outputs/concdvae/all_structures.csv",
    "CrystalFormer": "/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench/outputs/crystalformer/all_structures.csv",
    "CrystaLLM": "/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench/outputs/crystallm/all_structures.csv",
    "MatterGen": "/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench/outputs/mattergen/all_structures.csv",
}

OUTDIR = Path("/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench/figures")
OUTDIR.mkdir(exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "font.size": 11,
    "axes.titlesize": 15,
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "axes.linewidth": 0.8,
})

COLORS = {
    "Con-CDVAE": "#4C78A8",
    "CrystalFormer": "#F58518",
    "CrystaLLM": "#E45756",
    "MatterGen": "#54A24B",
}


def apply_paper_style(ax):
    ax.set_facecolor("white")
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def parse_structure_from_value(val):
    if pd.isna(val):
        return None

    s = str(val).strip()
    if not s:
        return None

    # 1) path to .cif
    p = Path(s)
    if p.exists() and p.is_file() and p.suffix.lower() == ".cif":
        try:
            return Structure.from_file(str(p))
        except Exception:
            pass

    # 2) dict-like structure string
    try:
        obj = literal_eval(s)
        if isinstance(obj, dict):
            return Structure.from_dict(obj)
    except Exception:
        pass

    # 3) CIF text
    try:
        if "data_" in s or "_cell_length_a" in s or "loop_" in s:
            return Structure.from_str(s, fmt="cif")
    except Exception:
        pass

    return None


def detect_sg_column(df):
    candidates = [
        "spg",
        "space_group",
        "spacegroup",
        "spacegroup_number",
        "sg",
    ]
    for c in candidates:
        if c in df.columns:
            return c
    return None


def detect_structure_column(df):
    candidates = [
        "cif",
        "relaxed_cif",
        "structure",
        "structure_dict",
        "pmg_structure",
        "filepath",
        "file_path",
        "cif_path",
        "path",
    ]
    for c in candidates:
        if c in df.columns:
            return c
    return None


def get_spacegroups_from_csv(csv_path):
    df = pd.read_csv(csv_path)

    sg_col = detect_sg_column(df)
    if sg_col is not None:
        sg = pd.to_numeric(df[sg_col], errors="coerce").dropna().astype(int)
        sg = sg[(sg >= 1) & (sg <= 230)]
        return sg.tolist()

    struct_col = detect_structure_column(df)
    if struct_col is None:
        raise ValueError(
            f"No space-group column and no structure-like column found in {csv_path}. "
            f"Columns: {list(df.columns)}"
        )

    sgs = []
    for val in df[struct_col]:
        struct = parse_structure_from_value(val)
        if struct is None:
            continue
        try:
            spg = SpacegroupAnalyzer(struct, symprec=0.1).get_space_group_number()
            if 1 <= spg <= 230:
                sgs.append(int(spg))
        except Exception:
            continue

    return sgs


def normalized_distribution(spacegroups):
    counts = pd.Series(spacegroups).value_counts().sort_index()
    full = pd.Series(0.0, index=range(1, 231))
    full.loc[counts.index] = counts.values
    full = full / full.sum()
    return full


def plot_line_distributions(dists):
    fig, ax = plt.subplots(figsize=(11.5, 5.8))
    fig.patch.set_facecolor("white")

    x = list(range(1, 231))
    for model, dist in dists.items():
        ax.step(
            x,
            dist.values,
            where="mid",
            label=model,
            color=COLORS[model],
            linewidth=2.0,
        )

    ax.set_title("Space Group Distribution by Model", pad=12)
    ax.set_xlabel("Space group number")
    ax.set_ylabel("Fraction of structures")
    ax.set_xlim(1, 230)
    apply_paper_style(ax)

    ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
        frameon=False,
        borderaxespad=0.0,
    )

    fig.tight_layout(rect=[0, 0, 0.82, 1])
    fig.savefig(OUTDIR / "spacegroup_distribution_all_models_line.png", bbox_inches="tight")
    plt.close(fig)


def plot_top20_grouped_bars(dists):
    # Top 20 SG by total mass across all models
    total = sum(dists.values())
    top20 = total.sort_values(ascending=False).head(20).index.tolist()

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor("white")

    models = list(dists.keys())
    x = range(len(top20))
    width = 0.18
    offsets = [-1.5, -0.5, 0.5, 1.5]

    for off, model in zip(offsets, models):
        vals = dists[model].loc[top20].values
        bars = ax.bar(
            [i + off * width for i in x],
            vals,
            width=width,
            label=model,
            color=COLORS[model],
            edgecolor="black",
            linewidth=0.35,
        )
        for bar in bars:
            h = bar.get_height()
            if h >= 0.01:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    h + 0.002,
                    f"{h*100:.1f}%",
                    ha="center",
                    va="bottom",
                    fontsize=7,
                    rotation=90,
                )

    ax.set_title("Top 20 Space Groups Across Models", pad=12)
    ax.set_xlabel("Space group number")
    ax.set_ylabel("Fraction of structures")
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(sg) for sg in top20])

    apply_paper_style(ax)
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
        frameon=False,
        borderaxespad=0.0,
    )

    fig.tight_layout(rect=[0, 0, 0.82, 1])
    fig.savefig(OUTDIR / "spacegroup_distribution_top20_grouped.png", bbox_inches="tight")
    plt.close(fig)


def main():
    dists = {}
    for model, csv_path in MODEL_CSVS.items():
        sgs = get_spacegroups_from_csv(csv_path)
        print(f"{model}: parsed {len(sgs)} space-group assignments")
        dists[model] = normalized_distribution(sgs)

    plot_line_distributions(dists)
    plot_top20_grouped_bars(dists)
    print(f"Saved figures to: {OUTDIR.resolve()}")


if __name__ == "__main__":
    main()