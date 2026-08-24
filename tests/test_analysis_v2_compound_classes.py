from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mvpipeline.analysis.compound_classes_v2 import (
    ADAPTATION_PAIRS,
    COMPOUND_CLASS_BASENAMES,
    COMPOUND_CLASS_COLUMN,
    OTHER_CLASS_LABEL,
    build_compound_class_tables,
)
from mvpipeline.analysis.plotting_v2 import (
    ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
)


def _synthetic_dataframe() -> pd.DataFrame:
    classes_by_cohort = {
        "mattergen_baseline": ["oxide", "oxide", "intermetallic", "halide"],
        "mattergen_finetuned": [
            "intermetallic",
            "intermetallic",
            "boride",
            "boride",
        ],
        "concdvae_baseline": [
            "oxide",
            "chalcogenide",
            "chalcogenide",
            "halide",
        ],
        "concdvae_finetuned": [
            "boride",
            "boride",
            "intermetallic",
            "silicide",
        ],
        "crystalformer_baseline": [
            "metal",
            "metal",
            "oxide",
            "intermetallic",
        ],
        "crystallm_baseline": [
            "oxide",
            "oxide",
            "oxide",
            "halide",
        ],
        "crysjepa_base": [
            "oxide",
            "chalcogenide",
            "halide",
            "intermetallic",
        ],
        "crysjepa_refined": [
            "intermetallic",
            "intermetallic",
            "metal",
            "metal",
        ],
    }

    rows = []
    for cohort in ANALYSIS_V2_MAGNETIC_COHORT_ORDER:
        for index, compound_class in enumerate(classes_by_cohort[cohort]):
            uid = f"{cohort}_{index}"
            rows.append(
                {
                    "structure_id": uid,
                    "sample_uid": uid,
                    "analysis_cohort": cohort,
                    COMPOUND_CLASS_COLUMN: compound_class,
                }
            )

    return pd.DataFrame(rows)


def test_compound_class_distribution_rows_sum_to_100():
    df = _synthetic_dataframe()

    _, distribution, _ = build_compound_class_tables(
        df,
        top_n=4,
        expected_total_rows=len(df),
    )

    assert tuple(distribution.index) == ANALYSIS_V2_MAGNETIC_COHORT_ORDER
    assert np.allclose(
        distribution.sum(axis=1).to_numpy(dtype=float),
        100.0,
    )


def test_compound_class_uses_global_top_n_plus_other():
    df = _synthetic_dataframe()

    class_order, distribution, _ = build_compound_class_tables(
        df,
        top_n=3,
        expected_total_rows=len(df),
    )

    expected_top = (
        df[COMPOUND_CLASS_COLUMN]
        .value_counts()
        .head(3)
        .index
        .tolist()
    )

    assert class_order == tuple(expected_top + [OTHER_CLASS_LABEL])
    assert tuple(distribution.columns) == class_order


def test_compound_class_adaptation_delta_is_adapted_minus_baseline():
    df = _synthetic_dataframe()

    class_order, distribution, delta = build_compound_class_tables(
        df,
        top_n=4,
        expected_total_rows=len(df),
    )

    for label, baseline, adapted in ADAPTATION_PAIRS:
        expected = (
            distribution.loc[adapted]
            - distribution.loc[baseline]
        )
        assert np.allclose(
            delta.loc[label, list(class_order)].to_numpy(dtype=float),
            expected.loc[list(class_order)].to_numpy(dtype=float),
        )


def test_compound_class_adaptation_delta_rows_sum_to_zero():
    df = _synthetic_dataframe()

    _, _, delta = build_compound_class_tables(
        df,
        top_n=4,
        expected_total_rows=len(df),
    )

    assert np.allclose(
        delta.sum(axis=1).to_numpy(dtype=float),
        0.0,
    )


def test_missing_compound_class_fails_clearly():
    df = _synthetic_dataframe()
    df.loc[0, COMPOUND_CLASS_COLUMN] = None

    with pytest.raises(RuntimeError, match="missing values"):
        build_compound_class_tables(
            df,
            top_n=4,
            expected_total_rows=len(df),
        )


def test_compound_class_figure_contracts():
    assert COMPOUND_CLASS_BASENAMES == (
        "11_compound_class_heatmap_v2",
        "12_compound_class_adaptation_shifts_v2",
    )
