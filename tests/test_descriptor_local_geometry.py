from __future__ import annotations

import pytest
from pymatgen.core import Lattice, Structure

from mvpipeline.descriptors.local_geometry import (
    compute_local_geometry_descriptors,
)
from mvpipeline.descriptors.records import LOCAL_GEOMETRY_FIELDS


def cubic_fe_structure() -> Structure:
    return Structure(
        Lattice.cubic(3.0),
        ["Fe"],
        [[0.0, 0.0, 0.0]],
    )


def test_local_geometry_schema_matches_record_contract():
    result = compute_local_geometry_descriptors(cubic_fe_structure())

    assert list(result) == LOCAL_GEOMETRY_FIELDS


def test_simple_cubic_periodic_neighbors():
    result = compute_local_geometry_descriptors(cubic_fe_structure())

    assert result["nearest_neighbor_min"] == pytest.approx(3.0)
    assert result["nearest_neighbor_mean"] == pytest.approx(3.0)
    assert result["nearest_neighbor_std"] == pytest.approx(0.0)

    assert result["coordination_mean"] == pytest.approx(6.0)
    assert result["coordination_min"] == pytest.approx(6.0)
    assert result["coordination_max"] == pytest.approx(6.0)
    assert result["coordination_std"] == pytest.approx(0.0)

    assert result["local_geometry_status"] == "ok"


def test_invalid_structure_is_row_safe():
    result = compute_local_geometry_descriptors(object())

    assert result == {
        "nearest_neighbor_min": None,
        "nearest_neighbor_mean": None,
        "nearest_neighbor_std": None,
        "coordination_mean": None,
        "coordination_min": None,
        "coordination_max": None,
        "coordination_std": None,
        "local_geometry_status": "error",
    }


def test_nonpositive_cutoff_is_row_safe():
    result = compute_local_geometry_descriptors(
        cubic_fe_structure(),
        cutoff=0.0,
    )

    assert result["local_geometry_status"] == "error"
    assert result["nearest_neighbor_mean"] is None
    assert result["coordination_mean"] is None
