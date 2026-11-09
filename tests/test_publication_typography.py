"""Typography guards: correct glyphs and frozen geometry, never Figure 1."""
from pathlib import Path
import pytest
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pymupdf as fitz
from mvpipeline.analysis.typography import (
    apply_ebrima_typography, correct_text, ebrima_font_path,
    prepare_figure_typography, restyle_pdf_typography,
)


def test_figure1_cannot_be_a_restyling_target(tmp_path):
    with pytest.raises(ValueError,match='read-only'):
        restyle_pdf_typography(tmp_path/'fig01_pipeline.pdf',tmp_path/'changed.pdf')


def test_missing_ebrima_raises_instead_of_falling_back(monkeypatch,tmp_path):
    monkeypatch.setenv('MAGGENBENCH_EBRIMA_FONT',str(tmp_path/'absent.ttf'))
    with pytest.raises(RuntimeError,match='no fallback'):
        ebrima_font_path()


def test_scientific_hyphens_and_negative_values_are_preserved():
    assert correct_text('Fine-tuned / Refined')=='Fine-tuned / Refined'
    assert correct_text('3d-containing')=='3d-containing'
    assert correct_text('S1 Pareto-efficient')=='S1 Pareto-efficient'
    assert correct_text('-25.325')=='−25.325'
    assert correct_text('3d atomic-\ncontent yield')=='3d atomic-content\nyield'
    assert correct_text('Unique formula–space-group pairs')=='Unique formula–space group pairs'


def test_matplotlib_exports_regular_embedded_ebrima(tmp_path):
    apply_ebrima_typography()
    fig,ax=plt.subplots()
    ax.bar([0,1],[.25,.75],color=['#4F6745','#61838F'])
    ax.set_title('A  Example',fontweight='bold')
    ax.set_xlabel('Min-max normalized score')
    prepare_figure_typography(fig)
    assert ax.title.get_fontweight()=='normal'
    assert ax.title.get_fontsize()>ax.xaxis.label.get_fontsize()>ax.get_xticklabels()[0].get_fontsize()
    path=tmp_path/'test.pdf';fig.savefig(path);plt.close(fig)
    doc=fitz.open(path)
    assert all('Ebrima' in f[3] and 'Bold' not in f[3] for f in doc[0].get_fonts())
    assert all(doc.extract_font(f[0])[3] for f in doc[0].get_fonts())
    assert 'Min–max' in doc[0].get_text()


def test_text_replacement_preserves_vectors_images_and_numbers(tmp_path):
    fig,ax=plt.subplots()
    ax.plot([0,1],[.25,.75],color='#4F6745')
    ax.set_title('Min-max normalized score')
    source=tmp_path/'fig08_example.pdf';fig.savefig(source);plt.close(fig)
    result=restyle_pdf_typography(source,tmp_path/'result.pdf')
    assert result['graphics_unchanged'] and result['images_unchanged']
    assert result['numeric_tokens_unchanged'] and result['embedded']
    assert not result['outside_page']
