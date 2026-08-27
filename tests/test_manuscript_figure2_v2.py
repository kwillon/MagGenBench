from __future__ import annotations

import pandas as pd

from mvpipeline.analysis.manuscript_figure2_v2 import (
    FIGURE_BASENAME,
    build_analysis_cohort_counts,
)
from mvpipeline.analysis.plotting_v2 import (
    ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
)
from mvpipeline.analysis.validation_figures_v2 import (
    EXPECTED_ROWS_PER_MODEL,
    EXPECTED_TOTAL_ROWS,
    MODEL_ORDER,
    REJECTION_REASON_ORDER,
)


def test_manuscript_figure2_basename():
    assert (
        FIGURE_BASENAME
        == "manuscript_figure2_structural_overview_v2_preview"
    )


def test_analysis_count_contract_uses_all_eight_cohorts():
    assert len(
        ANALYSIS_V2_MAGNETIC_COHORT_ORDER
    ) == 8


def test_validation_scope_is_four_baseline_models():
    assert MODEL_ORDER == (
        "MatterGen",
        "Con-CDVAE",
        "CrystalFormer",
        "CrystaLLM",
    )
    assert EXPECTED_ROWS_PER_MODEL == 2000
    assert EXPECTED_TOTAL_ROWS == 8000


def test_rejection_profile_has_five_reason_classes():
    assert len(REJECTION_REASON_ORDER) == 5


def test_build_analysis_cohort_counts_preserves_order():
    rows = []

    for index, cohort in enumerate(
        ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
        start=1,
    ):
        rows.extend(
            {"analysis_cohort": cohort}
            for _ in range(index)
        )

    df = pd.DataFrame(rows)

    counts = build_analysis_cohort_counts(
        df
    )

    assert tuple(
        counts.index
    ) == ANALYSIS_V2_MAGNETIC_COHORT_ORDER

    assert counts.tolist() == list(
        range(
            1,
            len(
                ANALYSIS_V2_MAGNETIC_COHORT_ORDER
            )
            + 1,
        )
    )
