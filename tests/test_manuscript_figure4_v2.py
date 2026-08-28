from __future__ import annotations

from mvpipeline.analysis.manuscript_figure4_v2 import (
    ADAPTATION_PAIRS,
    FIGURE_BASENAME,
)
from mvpipeline.analysis.plotting_v2 import (
    ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
)
from mvpipeline.analysis.projections_v2 import (
    COMPOSITION_SYMMETRY_PCA_FEATURES,
    MAGNETIC_GEOMETRY_PCA_FEATURES,
)


def test_manuscript_figure4_basename():
    assert (
        FIGURE_BASENAME
        == "manuscript_figure4_descriptor_space_v2_preview"
    )


def test_manuscript_figure4_uses_three_adaptation_pairs():
    assert len(ADAPTATION_PAIRS) == 3


def test_manuscript_figure4_adaptation_cohorts_exist():
    cohorts = set(
        ANALYSIS_V2_MAGNETIC_COHORT_ORDER
    )

    for baseline, adapted, _ in ADAPTATION_PAIRS:
        assert baseline in cohorts
        assert adapted in cohorts


def test_manuscript_figure4_pca_spaces_are_distinct():
    assert (
        COMPOSITION_SYMMETRY_PCA_FEATURES
        != MAGNETIC_GEOMETRY_PCA_FEATURES
    )


def test_manuscript_figure4_keeps_fixed_feature_counts():
    assert len(
        COMPOSITION_SYMMETRY_PCA_FEATURES
    ) == 11

    assert len(
        MAGNETIC_GEOMETRY_PCA_FEATURES
    ) == 13
