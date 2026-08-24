from __future__ import annotations

import math

import pandas as pd
import pytest

from mvpipeline.analysis.energy_magnetism_v2 import (
    ADAPTATION_PAIRS,
    ENERGY_COLUMN,
    ENERGY_MAGNETISM_BASENAMES,
    MOMENT_COLUMN,
    prepare_energy_magnetism_dataframe,
    summarize_energy_magnetism,
)
from mvpipeline.analysis.plotting_v2 import (
    ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
)


def _minimal_dataframe() -> pd.DataFrame:
    rows = []

    for index, cohort in enumerate(ANALYSIS_V2_MAGNETIC_COHORT_ORDER):
        rows.append(
            {
                "structure_id": f"{cohort}_0",
                "sample_uid": f"{cohort}_0",
                "analysis_cohort": cohort,
                "energy_status": "ok",
                "magnetism_status": "ok",
                ENERGY_COLUMN: -8.0 + index * 0.2,
                MOMENT_COLUMN: 0.5 + index * 0.3,
            }
        )
        rows.append(
            {
                "structure_id": f"{cohort}_1",
                "sample_uid": f"{cohort}_1",
                "analysis_cohort": cohort,
                "energy_status": "ok",
                "magnetism_status": "ok",
                ENERGY_COLUMN: -7.5 + index * 0.2,
                MOMENT_COLUMN: 0.8 + index * 0.3,
            }
        )

    return pd.DataFrame(rows)


def test_prepare_energy_magnetism_keeps_all_valid_cohorts():
    df = _minimal_dataframe()

    paired = prepare_energy_magnetism_dataframe(
        df,
        expected_total_rows=len(df),
        expected_paired_rows=len(df),
    )

    assert len(paired) == len(df)
    assert tuple(
        paired["analysis_cohort"].drop_duplicates()
    ) == ANALYSIS_V2_MAGNETIC_COHORT_ORDER


def test_prepare_energy_magnetism_filters_nonfinite_rows():
    df = _minimal_dataframe()
    df.loc[0, ENERGY_COLUMN] = float("nan")
    df.loc[3, MOMENT_COLUMN] = float("inf")

    paired = prepare_energy_magnetism_dataframe(
        df,
        expected_total_rows=len(df),
        expected_paired_rows=len(df) - 2,
    )

    assert len(paired) == len(df) - 2
    assert paired[ENERGY_COLUMN].map(math.isfinite).all()
    assert paired[MOMENT_COLUMN].map(math.isfinite).all()


def test_prepare_energy_magnetism_does_not_clip_negative_moments():
    df = _minimal_dataframe()
    df.loc[0, MOMENT_COLUMN] = -0.1

    paired = prepare_energy_magnetism_dataframe(
        df,
        expected_total_rows=len(df),
        expected_paired_rows=len(df),
    )

    assert paired[MOMENT_COLUMN].min() == pytest.approx(-0.1)


def test_summary_preserves_fixed_cohort_order():
    df = _minimal_dataframe()
    paired = prepare_energy_magnetism_dataframe(
        df,
        expected_total_rows=len(df),
        expected_paired_rows=len(df),
    )

    summary = summarize_energy_magnetism(paired)

    assert tuple(summary["analysis_cohort"]) == ANALYSIS_V2_MAGNETIC_COHORT_ORDER
    assert (summary["n"] == 2).all()


def test_energy_magnetism_figure_contracts():
    assert ENERGY_MAGNETISM_BASENAMES == (
        "09_energy_moment_landscape_v2",
        "10_energy_moment_adaptation_v2",
    )

    assert tuple(pair[:2] for pair in ADAPTATION_PAIRS) == (
        ("mattergen_baseline", "mattergen_finetuned"),
        ("concdvae_baseline", "concdvae_finetuned"),
        ("crysjepa_base", "crysjepa_refined"),
    )
