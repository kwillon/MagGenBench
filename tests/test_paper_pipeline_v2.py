from __future__ import annotations

from mvpipeline.analysis.plotting_v2 import (
    ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
)
from mvpipeline.analysis.paper_pipeline_figure_v2 import (
    EXPECTED_COHORTS,
    FIGURE_BASENAME,
)


def test_paper_pipeline_uses_analysis_v2_cohort_contract():
    assert EXPECTED_COHORTS == ANALYSIS_V2_MAGNETIC_COHORT_ORDER


def test_paper_pipeline_contains_all_eight_cohorts():
    assert len(EXPECTED_COHORTS) == 8
    assert len(set(EXPECTED_COHORTS)) == 8


def test_paper_pipeline_preview_basename():
    assert FIGURE_BASENAME == "paper_pipeline_v2_preview"
