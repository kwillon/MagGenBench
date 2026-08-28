from __future__ import annotations

from mvpipeline.analysis.compound_classes_v2 import (
    ADAPTATION_PAIRS as COMPOUND_ADAPTATION_PAIRS,
    COMPOUND_CLASS_BASENAMES,
    EXPECTED_ANALYSIS_V2_ROWS as COMPOUND_EXPECTED_ROWS,
    OTHER_CLASS_LABEL,
    TOP_N_COMPOUND_CLASSES,
)
from mvpipeline.analysis.diversity_figures_v2 import (
    ADAPTATION_PAIRS as DIVERSITY_ADAPTATION_PAIRS,
    EXPECTED_ANALYSIS_V2_ROWS as DIVERSITY_EXPECTED_ROWS,
    FIGURE_BASENAME as DIVERSITY_STANDALONE_BASENAME,
)
from mvpipeline.analysis.manuscript_figure6_v2 import (
    FIGURE_BASENAME,
)


def test_manuscript_figure6_basename():
    assert (
        FIGURE_BASENAME
        == "manuscript_figure6_diversity_adaptation_v2_preview"
    )


def test_manuscript_figure6_row_contracts_match():
    assert (
        COMPOUND_EXPECTED_ROWS
        == DIVERSITY_EXPECTED_ROWS
        == 10684
    )


def test_manuscript_figure6_compound_class_contract():
    assert (
        TOP_N_COMPOUND_CLASSES
        == 10
    )
    assert (
        OTHER_CLASS_LABEL
        == "Other"
    )


def test_manuscript_figure6_adaptation_pairs_match():
    compound_pairs = tuple(
        (baseline, adapted)
        for _, baseline, adapted
        in COMPOUND_ADAPTATION_PAIRS
    )

    diversity_pairs = tuple(
        (baseline, adapted)
        for _, baseline, adapted
        in DIVERSITY_ADAPTATION_PAIRS
    )

    assert (
        compound_pairs
        == diversity_pairs
    )


def test_manuscript_figure6_keeps_standalone_outputs():
    assert (
        COMPOUND_CLASS_BASENAMES
        == (
            "11_compound_class_heatmap_v2",
            "12_compound_class_adaptation_shifts_v2",
        )
    )

    assert (
        DIVERSITY_STANDALONE_BASENAME
        == "14_chemical_uniqueness_v2"
    )

    assert (
        FIGURE_BASENAME
        not in COMPOUND_CLASS_BASENAMES
    )
    assert (
        FIGURE_BASENAME
        != DIVERSITY_STANDALONE_BASENAME
    )
