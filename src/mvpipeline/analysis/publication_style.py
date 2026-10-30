"""Presentation helpers scoped to the manuscript figures (no data transforms)."""
from .plotting_v2 import apply_analysis_v2_publication_style

GENERATOR_COLORS = {
    "MatterGen": "#7D9279", "Con-CDVAE": "#DDAA4F",
    "CrystalFormer": "#DB8764", "CrystaLLM": "#A94F4B",
    "Crys-JEPA": "#738BA1",
}
GENERATOR_PREFIXES = dict(zip(
    ("mattergen", "concdvae", "crystalformer", "crystallm", "crysjepa"),
    GENERATOR_COLORS,
))
ADAPTED_HATCH = "///"


def cohort_color(cohort):
    return GENERATOR_COLORS[GENERATOR_PREFIXES[cohort.split("_")[0]]]


def is_adapted(cohort):
    return cohort.endswith(("_finetuned", "_refined"))


def apply_publication_style():
    import matplotlib.pyplot as plt

    apply_analysis_v2_publication_style()
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 11,
        "axes.labelsize": 11, "axes.titlesize": 12,
        "xtick.labelsize": 10, "ytick.labelsize": 10,
        "legend.fontsize": 10, "legend.title_fontsize": 11,
        "hatch.linewidth": 0.6,
    })
