from __future__ import annotations

from pathlib import Path

from mvpipeline.analysis import plotting_v2


EXPECTED_COHORT_ORDER = (
    "mattergen_baseline",
    "mattergen_finetuned",
    "concdvae_baseline",
    "concdvae_finetuned",
    "crystalformer_baseline",
    "crystallm_baseline",
    "crysjepa_base",
    "crysjepa_refined",
)


def test_analysis_v2_publication_palette_and_order_are_explicit():
    assert plotting_v2.ANALYSIS_V2_MAGNETIC_COHORT_ORDER == EXPECTED_COHORT_ORDER
    assert plotting_v2.ANALYSIS_V2_MAGNETIC_COHORT_COLORS == {
        "mattergen_baseline": "#9AA48C",
        "mattergen_finetuned": "#4F6745",
        "concdvae_baseline": "#DCAD5B",
        "concdvae_finetuned": "#BA5F19",
        "crystalformer_baseline": "#DC8A65",
        "crystallm_baseline": "#AC473D",
        "crysjepa_base": "#829DA6",
        "crysjepa_refined": "#304862",
    }
    assert plotting_v2.ANALYSIS_V2_DARK_TEXT == "#23324F"
    assert plotting_v2.ANALYSIS_V2_WARM_NEUTRAL == "#524534"
    assert plotting_v2.ANALYSIS_V2_OVERVIEW_CREAM == "#F0E2C5"


def test_analysis_v2_export_paths_use_generated_reproduced_area(tmp_path):
    assert plotting_v2.ANALYSIS_V2_OUTPUT_DIR == Path(
        "reproduced/analysis_v2_magnetic"
    )
    assert plotting_v2.ANALYSIS_V2_AUDIT_OUTPUT_DIR == Path(
        "reproduced/analysis_v2_magnetic/audit"
    )
    assert plotting_v2.ANALYSIS_V2_FIGURE_OUTPUT_DIR == Path(
        "reproduced/analysis_v2_magnetic/figures"
    )

    paths = plotting_v2.analysis_v2_export_paths(tmp_path, "preview")

    assert paths.png == tmp_path / "preview.png"
    assert paths.pdf == tmp_path / "preview.pdf"
    assert paths.svg == tmp_path / "preview.svg"


def test_analysis_v2_figure_scripts_are_thin_wrappers():
    root = Path(__file__).resolve().parents[1]

    audit = (
        root / "scripts/analysis/audit_analysis_v2_magnetic_figures.py"
    ).read_text(encoding="utf-8")
    preview = (
        root / "scripts/illustrations/plot_analysis_v2_magnetic_preview.py"
    ).read_text(encoding="utf-8")

    assert "audit_analysis_v2_magnetic_inputs" in audit
    assert "generate_analysis_v2_magnetic_preview_figure" in preview
    assert "pd.read_csv" not in audit
    assert "plt.subplots" not in preview
