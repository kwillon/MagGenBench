from __future__ import annotations

from pathlib import Path

from mvpipeline.analysis.cohorts import (
    COMPARATOR_ANALYSIS_COHORTS,
    CORE_BASELINE_FAMILIES,
    EXPECTED_PRODUCTION_COHORT_COUNTS,
    EXPECTED_PRODUCTION_DESCRIPTOR_STATUS_COUNTS,
    EXPECTED_PRODUCTION_ENERGY_STATUS_COUNTS,
    EXPECTED_PRODUCTION_MAGNETISM_STATUS_COUNTS,
    EXPECTED_PRODUCTION_ROWS,
    PRODUCTION_ANALYSIS_COHORT_ORDER,
    PRODUCTION_ANALYSIS_COHORTS,
    production_analysis_cohort_specs,
)


def test_production_cohort_keys_and_order_are_exact() -> None:
    keys = tuple(
        cohort.analysis_cohort
        for cohort in PRODUCTION_ANALYSIS_COHORTS
    )

    assert keys == (
        "baseline_master",
        "mattergen_finetuned",
        "concdvae_finetuned",
        "crysjepa_base",
        "crysjepa_refined",
    )
    assert keys == PRODUCTION_ANALYSIS_COHORT_ORDER


def test_production_family_and_state_values_are_exact() -> None:
    values = {
        cohort.analysis_cohort: (
            cohort.analysis_family,
            cohort.analysis_state,
        )
        for cohort in PRODUCTION_ANALYSIS_COHORTS
    }

    assert values == {
        "baseline_master": (None, "baseline"),
        "mattergen_finetuned": ("MatterGen", "fine_tuned"),
        "concdvae_finetuned": ("Con-CDVAE", "fine_tuned"),
        "crysjepa_base": ("Crys-JEPA", "base"),
        "crysjepa_refined": ("Crys-JEPA", "refined"),
    }


def test_expected_production_counts_are_exact() -> None:
    assert EXPECTED_PRODUCTION_ROWS == 10684
    assert dict(EXPECTED_PRODUCTION_COHORT_COUNTS) == {
        "baseline_master": 4702,
        "mattergen_finetuned": 1376,
        "concdvae_finetuned": 1299,
        "crysjepa_base": 1764,
        "crysjepa_refined": 1543,
    }
    assert sum(EXPECTED_PRODUCTION_COHORT_COUNTS.values()) == 10684
    assert dict(EXPECTED_PRODUCTION_DESCRIPTOR_STATUS_COUNTS) == {
        "ok": 10681,
        "partial": 3,
    }
    assert dict(EXPECTED_PRODUCTION_ENERGY_STATUS_COUNTS) == {
        "ok": 10680,
        "error": 4,
    }
    assert dict(EXPECTED_PRODUCTION_MAGNETISM_STATUS_COUNTS) == {
        "ok": 10684,
    }


def test_core_baseline_families_exclude_crysjepa() -> None:
    assert CORE_BASELINE_FAMILIES == (
        "MatterGen",
        "Con-CDVAE",
        "CrystalFormer",
        "CrystaLLM",
    )
    assert "Crys-JEPA" not in CORE_BASELINE_FAMILIES


def test_crysjepa_is_comparator_analysis_cohort_only() -> None:
    assert COMPARATOR_ANALYSIS_COHORTS == (
        "crysjepa_base",
        "crysjepa_refined",
    )

    comparator_families = {
        cohort.analysis_family
        for cohort in PRODUCTION_ANALYSIS_COHORTS
        if cohort.analysis_cohort in COMPARATOR_ANALYSIS_COHORTS
    }
    assert comparator_families == {"Crys-JEPA"}


def test_production_analysis_specs_use_supplied_baseline_join() -> None:
    baseline_joined = Path("custom/baseline_joined.csv")

    specs = production_analysis_cohort_specs(
        baseline_joined_path=baseline_joined,
    )

    assert [
        spec.analysis_cohort
        for spec in specs
    ] == list(PRODUCTION_ANALYSIS_COHORT_ORDER)
    assert specs[0].joined_path == baseline_joined
    assert specs[0].descriptor_path == Path(
        "runs/descriptor_v1_full/"
        "baseline_master_descriptors_v1.csv"
    )
    assert specs[1].joined_path == Path(
        "tables/04_magnetic_screening/"
        "phase5b_mattergen_finetuned_joined.csv"
    )
