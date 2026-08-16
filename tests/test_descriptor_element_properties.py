from __future__ import annotations

import math

import pytest
from pymatgen.core import Composition

from mvpipeline.descriptors.element_properties import (
    compute_element_property_descriptors,
)
from mvpipeline.descriptors.records import ELEMENT_PROPERTY_FIELDS


def test_element_property_schema_matches_record_contract():
    result = compute_element_property_descriptors(Composition("Fe2O3"))

    assert len(result) == 36
    assert set(result) == set(ELEMENT_PROPERTY_FIELDS)


def test_fe2o3_atomic_number_statistics_are_composition_weighted():
    result = compute_element_property_descriptors(Composition("Fe2O3"))

    expected_mean = 0.4 * 26.0 + 0.6 * 8.0
    expected_variance = (
        0.4 * (26.0 - expected_mean) ** 2
        + 0.6 * (8.0 - expected_mean) ** 2
    )

    assert result["atomic_number_mean"] == pytest.approx(expected_mean)
    assert result["atomic_number_min"] == pytest.approx(8.0)
    assert result["atomic_number_max"] == pytest.approx(26.0)
    assert result["atomic_number_range"] == pytest.approx(18.0)
    assert result["atomic_number_std"] == pytest.approx(
        math.sqrt(expected_variance)
    )
    assert result["atomic_number_coverage"] == pytest.approx(1.0)


def test_fe2o3_has_complete_coverage_for_v1_properties():
    result = compute_element_property_descriptors(Composition("Fe2O3"))

    coverage_fields = [
        field
        for field in ELEMENT_PROPERTY_FIELDS
        if field.endswith("_coverage")
    ]

    assert len(coverage_fields) == 6
    for field in coverage_fields:
        assert result[field] == pytest.approx(1.0)


def test_incomplete_property_coverage_is_not_renormalized():
    result = compute_element_property_descriptors(Composition("FeHe"))

    for prefix in ("atomic_radius", "electronegativity"):
        assert result[f"{prefix}_coverage"] == pytest.approx(0.5)
        assert result[f"{prefix}_mean"] is None
        assert result[f"{prefix}_min"] is None
        assert result[f"{prefix}_max"] is None
        assert result[f"{prefix}_range"] is None
        assert result[f"{prefix}_std"] is None

    assert result["atomic_number_coverage"] == pytest.approx(1.0)
    assert result["atomic_number_mean"] == pytest.approx(14.0)


def test_empty_composition_is_rejected_for_element_properties():
    class EmptyComposition:
        def get_el_amt_dict(self):
            return {}

    with pytest.raises(
        ValueError,
        match="Composition contains no positive elemental amounts",
    ):
        compute_element_property_descriptors(EmptyComposition())
