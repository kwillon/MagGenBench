from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mvpipeline.analysis.typography import prepare_figure_typography
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm


ROOT = Path(__file__).resolve().parents[2]
INPUT_CSV = ROOT / "tables" / "figure_sources" / "fig06_compound_classes.csv"
OUTPUT_DIR = ROOT / "reproduced" / "figure6"
OUTPUT_PDF = OUTPUT_DIR / "fig06_diversity_adaptation_palette_preview.pdf"
OUTPUT_PNG = OUTPUT_DIR / "fig06_diversity_adaptation_palette_preview.png"
OUTPUT_SVG = OUTPUT_DIR / "fig06_diversity_adaptation_palette_preview.svg"

ORIGINAL_CLASS_ORDER = [
    "intermetallic",
    "oxide",
    "metal",
    "chalcogenide",
    "salt/ionic compound",
    "halide",
    "boride",
    "pnictide",
    "silicide",
    "oxyhalide",
    "other",
]

ORIGINAL_MODEL_ORDER = [
    "mattergen_baseline",
    "mattergen_finetuned",
    "concdvae_baseline",
    "concdvae_finetuned",
    "crystalformer_baseline",
    "crystalformer_finetuned",
    "crystallm_baseline",
    "crystallm_finetuned",
    "crysjepa_base",
    "crysjepa_refined",
]

SEQ_COLORS = [
    "#F7F4E8",
    "#D6C16E",
    "#9AA48C",
    "#5E6B57",
    "#34432E",
]

DIV_COLORS = [
    "#AC473D",
    "#DC8A65",
    "#F7F4E8",
    "#9AA48C",
    "#34432E",
]

MODEL_LABELS = {
    "mattergen_baseline": "MatterGen Base",
    "mattergen_finetuned": "MatterGen Fine-tuned",
    "concdvae_baseline": "Con-CDVAE Base",
    "concdvae_finetuned": "Con-CDVAE Fine-tuned",
    "crysjepa_base": "Crys-JEPA Base",
    "crysjepa_refined": "Crys-JEPA Refined",
    "crystalformer_baseline": "CrystalFormer Base",
    "crystalformer_finetuned": "CrystalFormer Fine-tuned",
    "crystallm_baseline": "CrystaLLM Base",
    "crystallm_finetuned": "CrystaLLM FT",
}

ADAPTATION_PAIRS = [
    ("MatterGen", "mattergen_baseline", "mattergen_finetuned"),
    ("Con-CDVAE", "concdvae_baseline", "concdvae_finetuned"),
    ("CrystalFormer", "crystalformer_baseline", "crystalformer_finetuned"),
    ("CrystaLLM", "crystallm_baseline", "crystallm_finetuned"),
    ("Crys-JEPA", "crysjepa_base", "crysjepa_refined"),
]


def _cmap(name: str, colors: list[str]) -> LinearSegmentedColormap:
    cmap = LinearSegmentedColormap.from_list(name, colors)
    cmap.set_bad("#D9D9D2")
    return cmap


def _annotate(ax, values: np.ndarray, image, signed: bool = False) -> None:
    for row, column in np.ndindex(values.shape):
        value = values[row, column]
        if np.isnan(value):
            continue
        r, g, b, _ = image.cmap(image.norm(value))
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        color = "#FFFFFF" if luminance < 0.52 else "#273027"
        text = f"{value:+.1f}" if signed else f"{value:.1f}"
        ax.text(column, row, text, ha="center", va="center", fontsize=7.2, color=color)


def _aggregate_original_categories(table: pd.DataFrame) -> pd.DataFrame:
    """Reproduce the 11-column grouping used by the publication Figure 6."""
    selected = [
        "intermetallic",
        "oxide",
        "metal",
        "chalcogenide",
        "salt/ionic compound",
        "halide",
        "boride",
        "pnictide",
        "silicide",
        "oxyhalide",
    ]
    missing = sorted(set(selected).difference(table.columns))
    if missing:
        raise RuntimeError(f"Missing source classes: {missing}")

    aggregated = table.loc[:, selected].copy()
    other_columns = [column for column in table.columns if column not in selected]
    aggregated["other"] = table.loc[:, other_columns].sum(axis=1, min_count=1)
    return aggregated.loc[:, ORIGINAL_CLASS_ORDER]


def main() -> None:
    table = pd.read_csv(INPUT_CSV).set_index("analysis_cohort")
    table = table.astype(float)
    distribution = _aggregate_original_categories(
        table.reindex(ORIGINAL_MODEL_ORDER)
    )
    class_order = ORIGINAL_CLASS_ORDER
    if distribution.shape != (10, 11):
        raise RuntimeError(
            f"Expected the original 10x11 panel-A matrix, got {distribution.shape}"
        )

    # Keep panel A on its actual percentage scale, independent of the observed maximum.
    distribution_values = distribution.to_numpy(dtype=float)
    distribution_masked = np.ma.masked_invalid(distribution_values)

    adaptation_rows = []
    for label, baseline, adapted in ADAPTATION_PAIRS:
        adaptation_rows.append(
            (label, distribution.loc[adapted] - distribution.loc[baseline])
        )
    adaptation = pd.DataFrame({label: values for label, values in adaptation_rows}).T[class_order]
    adaptation_values = adaptation.to_numpy(dtype=float)
    if adaptation.shape != (5, 11):
        raise RuntimeError(
            f"Expected the original 5x11 panel-B matrix, got {adaptation.shape}"
        )
    symmetric_limit = float(np.nanmax(np.abs(adaptation_values)))
    if symmetric_limit == 0:
        symmetric_limit = 1.0

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(13.8, 7.03),
        gridspec_kw={"height_ratios": [2.65, 1.35]},
        constrained_layout=True,
    )
    fig.patch.set_facecolor("white")

    seq = _cmap("fig06_art_nouveau_sequential", SEQ_COLORS)
    image_a = axes[0].imshow(
        distribution_masked,
        aspect="auto",
        vmin=0.0,
        vmax=100.0,
        cmap=seq,
    )
    axes[0].set_title("Compound-class distribution", pad=8)
    axes[0].set_yticks(
        range(len(ORIGINAL_MODEL_ORDER)),
        [MODEL_LABELS[x] for x in ORIGINAL_MODEL_ORDER],
    )
    axes[0].set_xticks(range(len(class_order)), [])
    axes[0].tick_params(axis="x", bottom=False)
    _annotate(axes[0], distribution_values, image_a)
    axes[0].text(-0.055, 1.06, "A", transform=axes[0].transAxes, fontsize=12, fontweight="bold", va="top")
    cbar_a = fig.colorbar(image_a, ax=axes[0], pad=0.012, fraction=0.022)
    cbar_a.set_label("Share within cohort (%)")
    cbar_a.set_ticks([0, 25, 50, 75, 100])

    div = _cmap("fig06_art_nouveau_diverging", DIV_COLORS)
    image_b = axes[1].imshow(
        np.ma.masked_invalid(adaptation_values),
        aspect="auto",
        norm=TwoSlopeNorm(vmin=-symmetric_limit, vcenter=0.0, vmax=symmetric_limit),
        cmap=div,
    )
    axes[1].set_title("Adaptation-associated changes", pad=8)
    axes[1].set_yticks(range(len(adaptation.index)), adaptation.index)
    axes[1].set_xticks(range(len(class_order)), class_order, rotation=36, ha="right", rotation_mode="anchor")
    axes[1].tick_params(axis="x", pad=4)
    _annotate(axes[1], adaptation_values, image_b, signed=True)
    axes[1].text(-0.055, 1.08, "B", transform=axes[1].transAxes, fontsize=12, fontweight="bold", va="top")
    cbar_b = fig.colorbar(image_b, ax=axes[1], pad=0.012, fraction=0.022)
    cbar_b.set_label("Fine-tuned/Refined minus Base (pp)")
    cbar_b.set_ticks(np.linspace(-symmetric_limit, symmetric_limit, 5))

    for ax in axes:
        ax.set_facecolor("white")
        ax.tick_params(axis="both", labelsize=8)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    prepare_figure_typography(fig)
    fig.savefig(OUTPUT_PDF, facecolor="white")
    fig.savefig(OUTPUT_PNG, dpi=220, facecolor="white")
    fig.savefig(OUTPUT_SVG, facecolor="white")
    plt.close(fig)

    assert np.allclose(distribution.sum(axis=1).to_numpy(), 100.0, atol=1e-8)
    assert np.allclose(adaptation.sum(axis=1).to_numpy(), 0.0, atol=1e-8)
    assert np.isclose(float(image_b.norm(0.0)), 0.5)
    print(f"input: {INPUT_CSV}")
    print(f"distribution_shape: {distribution.shape}")
    print(f"adaptation_shape: {adaptation.shape}")
    print(f"panel_a_range: 0.0..100.0")
    print(f"panel_b_range: {-symmetric_limit}..{symmetric_limit}")
    print(f"panel_b_zero_norm: {image_b.norm(0.0):.3f}")
    print(f"pdf: {OUTPUT_PDF}")
    print(f"png: {OUTPUT_PNG}")
    print(f"svg: {OUTPUT_SVG}")


if __name__ == "__main__":
    main()
