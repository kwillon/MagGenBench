from __future__ import annotations

from mvpipeline.analysis.paper_pipeline_figure_v3 import (
    EXPECTED_COHORTS,
    FIGURE_BASENAME,
    MODEL_GROUPS,
    PROVISIONAL_VARIANTS,
    PARALLEL_BRANCHES,
    REFERENCE_BRANCHES,
    WORKFLOW_CONTENT_LABELS,
    run_paper_pipeline_figure_v3,
)
from mvpipeline.analysis.plotting_v2 import ANALYSIS_V2_MAGNETIC_COHORT_ORDER


def test_paper_pipeline_v3_uses_analysis_v2_cohort_contract():
    assert EXPECTED_COHORTS == ANALYSIS_V2_MAGNETIC_COHORT_ORDER


def test_paper_pipeline_v3_preview_basename():
    assert FIGURE_BASENAME == "paper_pipeline_v3_preview"


def test_paper_pipeline_v3_displays_current_model_variants():
    groups = {model: tuple(label for label, _ in variants)
              for model, variants in MODEL_GROUPS}
    assert groups == {
        "MatterGen": ("Base", "Fine-tuned"),
        "Con-CDVAE": ("Base", "Fine-tuned"),
        "CrystalFormer": ("Base", "Fine-tuned*"),
        "CrystaLLM": ("Base", "Fine-tuned*"),
        "Crys-JEPA": ("Base", "Refined"),
    }
    assert set(PROVISIONAL_VARIANTS) == {
        "crystalformer_finetuned",
        "crystallm_finetuned",
    }


def test_paper_pipeline_v3_content_contract():
    required = {
        "Generated structures / native outputs", "CIF harmonization",
        "Structural quality control", "Retained structures for downstream analysis",
        "CHGNet energy", "Predicted energy per atom", "DXMag magnetic moment",
        "Composition-based predicted moment", "Magnetic composition",
        "Local magnetic geometry", "Symmetry", "Descriptor construction",
        "kNN distances", "Cmag-NM scoring", "Selected candidates",
        "DFT calculations", "DFT validation", "Reference-space enrichment",
        "Energy-magnetism landscape",
    }
    assert required.issubset(set(WORKFLOW_CONTENT_LABELS))
    assert REFERENCE_BRANCHES == ("MAGNDATA", "AFM", "FM", "FiM", "NM")


def test_paper_pipeline_v3_uses_cautious_scientific_wording():
    labels = set(WORKFLOW_CONTENT_LABELS)
    assert "Predicted energy per atom" in labels
    assert "Composition-based predicted moment" in labels
    assert "Magnetic-reference contrast" in labels
    assert "Formation energy" not in labels
    assert "Stability" not in labels
    assert "Magnetic-order prediction" not in labels
    assert "Likelihood" not in labels


def test_property_and_descriptor_cards_are_parallel_siblings():
    assert PARALLEL_BRANCHES["Property prediction"] == (
        "CHGNet energy",
        "DXMag magnetic moment",
    )
    assert PARALLEL_BRANCHES["Magnetic descriptors"] == (
        "Composition",
        "Local magnetic geometry",
        "Symmetry",
    )


def test_paper_pipeline_v3_generates_png_pdf_svg(tmp_path):
    report = run_paper_pipeline_figure_v3(figure_dir=tmp_path)
    paths = report.figure_paths
    for path in (paths.png, paths.pdf, paths.svg):
        assert path.is_file()
        assert path.stat().st_size > 0
    assert paths.png.name == "paper_pipeline_v3_preview.png"
    assert paths.pdf.name == "paper_pipeline_v3_preview.pdf"
    assert paths.svg.name == "paper_pipeline_v3_preview.svg"

    svg_text = paths.svg.read_text(encoding="utf-8")
    for label in (
        "MAGNDATA", "Materials Project", "CHGNet",
        "DXMag magnetic", "Reference-space screening",
        "Candidate-level DFT validation", "Selected candidates",
        "DFT calculations", "DFT validation", "Reference-space",
    ):
        assert label in svg_text
    assert "formation energy" not in svg_text.lower()
    assert "likelihood" not in svg_text.lower()
    assert "Analysis v2" not in svg_text
    assert "Descriptor v2" not in svg_text
