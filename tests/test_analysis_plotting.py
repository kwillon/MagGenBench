from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from mvpipeline.analysis.cohorts import (
    COMPARATOR_ANALYSIS_COHORTS,
    CORE_BASELINE_FAMILIES,
    EXPECTED_PRODUCTION_ROWS,
)
from mvpipeline.analysis.plotting import (
    STANDARD_PLOT_GROUPS,
    bool_series_values,
    build_plot_groups,
    numeric_values,
    plot_group_for_row,
    validate_unified_analysis_rows,
)


MIGRATED_PLOT_SCRIPTS = (
    "plot_structural_distributions_v1.py",
    "plot_compound_class_heatmap_v1.py",
    "plot_3d_4f_fraction_v1.py",
    "plot_magnetic_screening_fraction_v1.py",
    "plot_dxmag_predicted_moment_v1.py",
)


def _row(
    uid: str,
    cohort: str,
    family: str,
    **overrides: str,
) -> dict[str, str]:
    row = {
        "sample_uid": uid,
        "analysis_cohort": cohort,
        "analysis_family": family,
        "crystal_system": "cubic",
    }
    row.update(overrides)
    return row


def _standard_rows() -> list[dict[str, str]]:
    return [
        _row("mg-b", "baseline_master", "MatterGen"),
        _row("mg-ft", "mattergen_finetuned", "MatterGen"),
        _row("cd-b", "baseline_master", "Con-CDVAE"),
        _row("cd-ft", "concdvae_finetuned", "Con-CDVAE"),
        _row("cf-b", "baseline_master", "CrystalFormer"),
        _row("cl-b", "baseline_master", "CrystaLLM"),
        _row("cj-b", "crysjepa_base", "Crys-JEPA"),
        _row("cj-r", "crysjepa_refined", "Crys-JEPA"),
    ]


def test_canonical_eight_display_groups_and_order_are_exact() -> None:
    assert [group.label for group in STANDARD_PLOT_GROUPS] == [
        "MatterGen baseline",
        "MatterGen fine-tuned",
        "Con-CDVAE baseline",
        "Con-CDVAE fine-tuned",
        "CrystalFormer baseline",
        "CrystaLLM baseline",
        "Crys-JEPA Base",
        "Crys-JEPA Refined",
    ]
    assert [
        (group.analysis_cohort, group.analysis_family)
        for group in STANDARD_PLOT_GROUPS
    ] == [
        ("baseline_master", "MatterGen"),
        ("mattergen_finetuned", "MatterGen"),
        ("baseline_master", "Con-CDVAE"),
        ("concdvae_finetuned", "Con-CDVAE"),
        ("baseline_master", "CrystalFormer"),
        ("baseline_master", "CrystaLLM"),
        ("crysjepa_base", "Crys-JEPA"),
        ("crysjepa_refined", "Crys-JEPA"),
    ]


def test_baseline_master_splits_into_core_baseline_families() -> None:
    rows = pd.DataFrame(_standard_rows())

    groups = build_plot_groups(rows)

    grouped_uids = {
        group.label: [row["sample_uid"] for row in group_rows]
        for group, group_rows in groups
    }
    assert grouped_uids["MatterGen baseline"] == ["mg-b"]
    assert grouped_uids["Con-CDVAE baseline"] == ["cd-b"]
    assert grouped_uids["CrystalFormer baseline"] == ["cf-b"]
    assert grouped_uids["CrystaLLM baseline"] == ["cl-b"]


def test_fine_tuned_and_crysjepa_labels_are_exact() -> None:
    rows = _standard_rows()

    labels = [
        plot_group_for_row(row).label
        for row in rows
    ]

    assert "MatterGen fine-tuned" in labels
    assert "Con-CDVAE fine-tuned" in labels
    assert "Crys-JEPA Base" in labels
    assert "Crys-JEPA Refined" in labels


def test_crysjepa_is_not_core_baseline_family() -> None:
    assert CORE_BASELINE_FAMILIES == (
        "MatterGen",
        "Con-CDVAE",
        "CrystalFormer",
        "CrystaLLM",
    )
    assert "Crys-JEPA" not in CORE_BASELINE_FAMILIES
    assert COMPARATOR_ANALYSIS_COHORTS == (
        "crysjepa_base",
        "crysjepa_refined",
    )


def test_expected_row_guard_uses_production_count() -> None:
    assert EXPECTED_PRODUCTION_ROWS == 10684

    with pytest.raises(RuntimeError, match="Expected 10684"):
        validate_unified_analysis_rows(
            pd.DataFrame(_standard_rows()),
            expected_count=EXPECTED_PRODUCTION_ROWS,
        )


def test_missing_required_columns_fail_clearly() -> None:
    rows = pd.DataFrame(
        [
            {
                "sample_uid": "x",
                "analysis_cohort": "baseline_master",
                "analysis_family": "MatterGen",
            }
        ]
    )

    with pytest.raises(RuntimeError, match="missing required columns"):
        validate_unified_analysis_rows(
            rows,
            required_columns=("crystal_system",),
            expected_count=None,
        )


def test_unknown_cohort_or_family_fails_loudly() -> None:
    with pytest.raises(RuntimeError, match="Unknown baseline"):
        plot_group_for_row(
            _row("bad-family", "baseline_master", "Crys-JEPA")
        )

    with pytest.raises(RuntimeError, match="Unknown analysis_cohort"):
        plot_group_for_row(
            _row("bad-cohort", "new_model", "New Model")
        )


@pytest.mark.parametrize(
    ("cohort", "wrong_family"),
    [
        ("mattergen_finetuned", "Con-CDVAE"),
        ("concdvae_finetuned", "MatterGen"),
        ("crysjepa_base", "MatterGen"),
        ("crysjepa_refined", "MatterGen"),
    ],
)
def test_non_baseline_wrong_family_fails_loudly(
    cohort: str,
    wrong_family: str,
) -> None:
    with pytest.raises(RuntimeError, match="Unexpected analysis_family"):
        plot_group_for_row(_row("bad-family", cohort, wrong_family))


def test_every_standard_row_maps_to_exactly_one_canonical_group() -> None:
    for row in _standard_rows():
        group = plot_group_for_row(row)
        matches = [
            candidate
            for candidate in STANDARD_PLOT_GROUPS
            if candidate.analysis_cohort == group.analysis_cohort
            and candidate.analysis_family == group.analysis_family
        ]
        assert matches == [group]


def test_group_construction_does_not_silently_drop_bad_rows() -> None:
    rows = pd.DataFrame(
        [
            *_standard_rows(),
            _row("bad-family", "mattergen_finetuned", "Con-CDVAE"),
        ]
    )

    with pytest.raises(RuntimeError, match="Unexpected analysis_family"):
        build_plot_groups(rows)


def test_group_construction_preserves_rows_and_sample_uids() -> None:
    rows = pd.DataFrame(_standard_rows())

    grouped = build_plot_groups(rows)
    flattened = [
        row["sample_uid"]
        for _, group_rows in grouped
        for row in group_rows
    ]

    assert len(flattened) == len(rows)
    assert flattened == [
        "mg-b",
        "mg-ft",
        "cd-b",
        "cd-ft",
        "cf-b",
        "cl-b",
        "cj-b",
        "cj-r",
    ]


def test_boolean_helper_matches_current_plotting_semantics() -> None:
    assert bool_series_values(
        ["true", "True", " TRUE ", "1", "false", "0", "", None]
    ) == [True, True, True, True, False, False, False, False]


def test_numeric_helper_preserves_negative_floating_point_values() -> None:
    assert numeric_values(["-1.25", "0", "2.5"]) == [-1.25, 0.0, 2.5]


def test_migrated_plot_scripts_use_canonical_grouping() -> None:
    root = Path(__file__).resolve().parents[1]
    scripts_dir = root / "scripts" / "illustrations"

    for filename in MIGRATED_PLOT_SCRIPTS:
        source = (scripts_dir / filename).read_text(encoding="utf-8")
        assert "STANDARD_PLOT_GROUPS" in source
        assert "build_plot_groups" in source
        assert "\nGROUPS =" not in source
        assert "\nGROUP_ORDER =" not in source
        assert "Expected 10684" not in source
        assert 'Path(__file__).resolve().parents[2]' not in source
