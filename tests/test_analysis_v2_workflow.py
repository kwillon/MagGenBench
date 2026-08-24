from __future__ import annotations

from mvpipeline.analysis.plotting_v2 import (
    ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
)
from mvpipeline.analysis.workflow_figure_v2 import (
    EXPECTED_COHORTS,
    FIGURE_BASENAME,
    PIPELINE_STAGE_GROUPS,
)


def test_workflow_uses_analysis_v2_cohort_contract():
    assert EXPECTED_COHORTS == ANALYSIS_V2_MAGNETIC_COHORT_ORDER


def test_workflow_contains_all_eight_cohorts():
    assert len(EXPECTED_COHORTS) == 8
    assert len(set(EXPECTED_COHORTS)) == 8


def test_workflow_stage_contract_matches_pipeline():
    assert PIPELINE_STAGE_GROUPS == (
        (
            "Structural preparation",
            (
                "01_master",
                "02_validation",
                "03_features",
            ),
        ),
        (
            "Physics-informed enrichment",
            (
                "04_magnetic_screening",
                "05_relaxation",
                "06_energy",
                "07_magnetic_descriptors",
            ),
        ),
        (
            "Harmonized descriptor layer",
            (
                "08_standardized_enrichment",
                "09_descriptor_v2_magnetic",
            ),
        ),
        (
            "Comparative analysis",
            (
                "10_analysis_v2_magnetic",
            ),
        ),
    )


def test_workflow_covers_pipeline_stages_once():
    stages = [
        stage
        for _, group in PIPELINE_STAGE_GROUPS
        for stage in group
    ]

    assert stages == [
        "01_master",
        "02_validation",
        "03_features",
        "04_magnetic_screening",
        "05_relaxation",
        "06_energy",
        "07_magnetic_descriptors",
        "08_standardized_enrichment",
        "09_descriptor_v2_magnetic",
        "10_analysis_v2_magnetic",
    ]


def test_workflow_preview_basename_is_nonconflicting():
    assert FIGURE_BASENAME == "study_workflow_v2_preview"
