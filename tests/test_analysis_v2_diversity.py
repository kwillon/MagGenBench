from __future__ import annotations

import numpy as np
import pandas as pd

from mvpipeline.analysis.diversity_figures_v2 import (
    ADAPTATION_DELTA_CSV,
    ADAPTATION_PAIRS,
    FIGURE_BASENAME,
    FORMULA_COLUMN,
    SPACE_GROUP_COLUMN,
    SUMMARY_CSV,
    build_diversity_tables,
)
from mvpipeline.analysis.plotting_v2 import (
    ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
)


def _synthetic_dataframe() -> pd.DataFrame:
    values = {
        "mattergen_baseline": [
            ("A", 1),
            ("A", 2),
            ("B", 1),
            ("C", 1),
        ],
        "mattergen_finetuned": [
            ("A", 1),
            ("A", 1),
            ("A", 2),
            ("B", 1),
        ],
        "concdvae_baseline": [
            ("A", 1),
            ("B", 1),
            ("C", 1),
            ("D", 1),
        ],
        "concdvae_finetuned": [
            ("A", 1),
            ("A", 2),
            ("B", 1),
            ("B", 1),
        ],
        "crystalformer_baseline": [
            ("A", 1),
            ("A", 1),
            ("B", 1),
            ("C", 1),
        ],
        "crystallm_baseline": [
            ("A", 1),
            ("A", 1),
            ("A", 1),
            ("B", 1),
        ],
        "crysjepa_base": [
            ("A", 1),
            ("B", 1),
            ("C", 1),
            ("D", 1),
        ],
        "crysjepa_refined": [
            ("A", 1),
            ("A", 1),
            ("B", 1),
            ("B", 1),
        ],
    }

    rows = []

    for cohort in ANALYSIS_V2_MAGNETIC_COHORT_ORDER:
        for formula, space_group in values[cohort]:
            rows.append(
                {
                    "analysis_cohort": cohort,
                    FORMULA_COLUMN: formula,
                    SPACE_GROUP_COLUMN: space_group,
                }
            )

    return pd.DataFrame(rows)


def test_diversity_summary_uses_fixed_cohort_order():
    summary, _ = build_diversity_tables(_synthetic_dataframe())

    assert tuple(summary.index) == ANALYSIS_V2_MAGNETIC_COHORT_ORDER


def test_formula_uniqueness_is_computed_within_each_cohort():
    summary, _ = build_diversity_tables(_synthetic_dataframe())

    assert np.isclose(
        summary.loc[
            "mattergen_baseline",
            "unique_formula_percent",
        ],
        75.0,
    )

    assert np.isclose(
        summary.loc[
            "mattergen_finetuned",
            "unique_formula_percent",
        ],
        50.0,
    )

    assert np.isclose(
        summary.loc[
            "concdvae_baseline",
            "unique_formula_percent",
        ],
        100.0,
    )


def test_formula_spacegroup_uniqueness_is_computed_separately():
    summary, _ = build_diversity_tables(_synthetic_dataframe())

    assert np.isclose(
        summary.loc[
            "mattergen_baseline",
            "unique_formula_sg_percent",
        ],
        100.0,
    )

    assert np.isclose(
        summary.loc[
            "mattergen_finetuned",
            "unique_formula_sg_percent",
        ],
        75.0,
    )


def test_formula_spacegroup_uniqueness_is_not_below_formula_uniqueness():
    summary, _ = build_diversity_tables(_synthetic_dataframe())

    assert np.all(
        summary["unique_formula_sg_percent"].to_numpy(dtype=float)
        >= summary["unique_formula_percent"].to_numpy(dtype=float)
    )


def test_adaptation_deltas_are_adapted_minus_baseline():
    summary, delta = build_diversity_tables(_synthetic_dataframe())

    for label, baseline, adapted in ADAPTATION_PAIRS:
        expected_formula = (
            summary.loc[adapted, "unique_formula_percent"]
            - summary.loc[baseline, "unique_formula_percent"]
        )
        expected_formula_sg = (
            summary.loc[adapted, "unique_formula_sg_percent"]
            - summary.loc[baseline, "unique_formula_sg_percent"]
        )

        assert np.isclose(
            delta.loc[label, "unique_formula_delta_pp"],
            expected_formula,
        )
        assert np.isclose(
            delta.loc[label, "unique_formula_sg_delta_pp"],
            expected_formula_sg,
        )


def test_diversity_output_contracts():
    assert FIGURE_BASENAME == "14_chemical_uniqueness_v2"
    assert SUMMARY_CSV == "chemical_uniqueness_summary_v2.csv"
    assert (
        ADAPTATION_DELTA_CSV
        == "chemical_uniqueness_adaptation_delta_pp_v2.csv"
    )
