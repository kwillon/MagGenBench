from __future__ import annotations

import pandas as pd

from mvpipeline.analysis.manuscript_figure2_v2 import (
    BASELINE_DISPLAY_ORDER,
    CRYSJEPA_BASE_VALIDATION_INPUT,
    FIGURE_BASENAME,
    _extend_with_crysjepa_base,
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


def test_validation_scope_preserves_core_four_and_displays_five_base_sets():
    assert MODEL_ORDER == (
        "MatterGen",
        "Con-CDVAE",
        "CrystalFormer",
        "CrystaLLM",
    )
    assert BASELINE_DISPLAY_ORDER == (
        "MatterGen",
        "Con-CDVAE",
        "CrystalFormer",
        "CrystaLLM",
        "Crys-JEPA",
    )
    assert EXPECTED_ROWS_PER_MODEL == 2000
    assert EXPECTED_TOTAL_ROWS == 8000
    assert CRYSJEPA_BASE_VALIDATION_INPUT.name == (
        "crysjepa_base_with_classes.csv"
    )


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


def test_crysjepa_base_extension_matches_frozen_validation_artifact():
    import pandas as pd

    validation_summary = pd.DataFrame(
        {
            "n_total": [2000] * 4,
            "n_validated": [1657, 1864, 1083, 98],
            "n_rejected": [343, 136, 917, 1902],
            "validated_percent": [82.85, 93.20, 54.15, 4.90],
            "rejected_percent": [17.15, 6.80, 45.85, 95.10],
        },
        index=MODEL_ORDER,
    )

    rejection_summary = pd.DataFrame(
        0.0,
        index=MODEL_ORDER,
        columns=REJECTION_REASON_ORDER,
    )

    extended_summary, extended_rejection = _extend_with_crysjepa_base(
        validation_summary,
        rejection_summary,
    )

    assert tuple(extended_summary.index) == BASELINE_DISPLAY_ORDER
    assert int(extended_summary.loc["Crys-JEPA", "n_total"]) == 2000
    assert int(extended_summary.loc["Crys-JEPA", "n_validated"]) == 1764
    assert int(extended_summary.loc["Crys-JEPA", "n_rejected"]) == 236
    assert extended_summary.loc[
        "Crys-JEPA", "validated_percent"
    ] == 88.2

    assert tuple(extended_rejection.index) == BASELINE_DISPLAY_ORDER
    assert abs(
        float(extended_rejection.loc["Crys-JEPA"].sum()) - 100.0
    ) < 1e-8

    assert round(
        float(
            extended_rejection.loc[
                "Crys-JEPA", "charge_imbalance"
            ]
        ),
        1,
    ) == 65.3

    assert round(
        float(
            extended_rejection.loc[
                "Crys-JEPA",
                "physically_impossible_distance",
            ]
        ),
        1,
    ) == 32.6

    assert round(
        float(
            extended_rejection.loc[
                "Crys-JEPA", "duplicate"
            ]
        ),
        1,
    ) == 2.1
