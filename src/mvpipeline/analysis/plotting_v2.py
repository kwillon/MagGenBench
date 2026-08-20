from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ANALYSIS_V2_MAGNETIC_COHORT_ORDER = (
    "mattergen_baseline",
    "mattergen_finetuned",
    "concdvae_baseline",
    "concdvae_finetuned",
    "crystalformer_baseline",
    "crystallm_baseline",
    "crysjepa_base",
    "crysjepa_refined",
)

ANALYSIS_V2_MAGNETIC_COHORT_LABELS = {
    "mattergen_baseline": "MatterGen\nBase",
    "mattergen_finetuned": "MatterGen\nFT",
    "concdvae_baseline": "Con-CDVAE\nBase",
    "concdvae_finetuned": "Con-CDVAE\nFT",
    "crystalformer_baseline": "CrystalFormer\nBase",
    "crystallm_baseline": "CrystaLLM\nBase",
    "crysjepa_base": "Crys-JEPA\nBase",
    "crysjepa_refined": "Crys-JEPA\nRef.",
}

ANALYSIS_V2_MAGNETIC_COHORT_COLORS = {
    "mattergen_baseline": "#9AA48C",
    "mattergen_finetuned": "#4F6745",
    "concdvae_baseline": "#DCAD5B",
    "concdvae_finetuned": "#BA5F19",
    "crystalformer_baseline": "#DC8A65",
    "crystallm_baseline": "#AC473D",
    "crysjepa_base": "#829DA6",
    "crysjepa_refined": "#304862",
}

ANALYSIS_V2_DARK_TEXT = "#23324F"
ANALYSIS_V2_WARM_NEUTRAL = "#524534"
ANALYSIS_V2_OVERVIEW_CREAM = "#F0E2C5"
ANALYSIS_V2_OUTPUT_DIR = Path("reproduced/analysis_v2_magnetic")
ANALYSIS_V2_AUDIT_OUTPUT_DIR = ANALYSIS_V2_OUTPUT_DIR / "audit"
ANALYSIS_V2_FIGURE_OUTPUT_DIR = ANALYSIS_V2_OUTPUT_DIR / "figures"

ANALYSIS_V2_PREVIEW_BASENAME = "magnetic_domain_overview_v2_preview"
ANALYSIS_V2_STANDALONE_BASENAMES = (
    "01_cohort_sizes_v2",
    "02_transition_3d_fraction_v2",
    "03_configured_lanthanide_fraction_v2",
    "04_magnetic_neighbor_fraction_v2",
)
ANALYSIS_V2_PCA_BASENAMES = (
    "05_pca_composition_symmetry_v2",
    "06_pca_magnetic_geometry_v2",
    "07_pca_adaptation_shifts_v2",
    "08_pca_loadings_v2",
)


@dataclass(frozen=True)
class FigureExportPaths:
    png: Path
    pdf: Path
    svg: Path


def apply_analysis_v2_publication_style() -> None:
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "text.color": ANALYSIS_V2_DARK_TEXT,
            "axes.labelcolor": ANALYSIS_V2_DARK_TEXT,
            "xtick.color": ANALYSIS_V2_DARK_TEXT,
            "ytick.color": ANALYSIS_V2_DARK_TEXT,
            "axes.edgecolor": ANALYSIS_V2_DARK_TEXT,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "grid.color": "#D5D5D5",
            "grid.linewidth": 0.45,
            "grid.alpha": 0.55,
            "axes.linewidth": 0.8,
            "font.size": 9.5,
            "axes.labelsize": 10,
            "axes.titlesize": 10,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "figure.dpi": 160,
            "savefig.dpi": 450,
            "savefig.bbox": "tight",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "axes.prop_cycle": plt.cycler(
                color=[
                    ANALYSIS_V2_MAGNETIC_COHORT_COLORS[key]
                    for key in ANALYSIS_V2_MAGNETIC_COHORT_ORDER
                ]
            ),
        }
    )


def analysis_v2_export_paths(
    output_dir: str | Path,
    basename: str,
) -> FigureExportPaths:
    root = Path(output_dir)
    return FigureExportPaths(
        png=root / f"{basename}.png",
        pdf=root / f"{basename}.pdf",
        svg=root / f"{basename}.svg",
    )


def save_analysis_v2_figure_bundle(
    fig: object,
    output_dir: str | Path,
    basename: str,
) -> FigureExportPaths:
    paths = analysis_v2_export_paths(output_dir, basename)
    paths.png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(paths.png, dpi=450, bbox_inches="tight")
    fig.savefig(paths.pdf, bbox_inches="tight")
    fig.savefig(paths.svg, bbox_inches="tight")
    return paths
