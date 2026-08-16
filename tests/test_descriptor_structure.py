from __future__ import annotations

import pytest
from pymatgen.core import Lattice, Structure

from mvpipeline.descriptors.structure import (
    compute_symmetry_descriptors,
    compute_unit_cell_descriptors,
)


def cubic_fe_structure() -> Structure:
    return Structure(
        Lattice.cubic(3.0),
        ["Fe"],
        [[0.0, 0.0, 0.0]],
    )


def test_unit_cell_descriptors_for_cubic_structure():
    structure = cubic_fe_structure()

    result = compute_unit_cell_descriptors(structure)

    assert result["n_atoms"] == 1
    assert result["lattice_a"] == pytest.approx(3.0)
    assert result["lattice_b"] == pytest.approx(3.0)
    assert result["lattice_c"] == pytest.approx(3.0)
    assert result["lattice_alpha"] == pytest.approx(90.0)
    assert result["lattice_beta"] == pytest.approx(90.0)
    assert result["lattice_gamma"] == pytest.approx(90.0)
    assert result["cell_volume"] == pytest.approx(27.0)
    assert result["volume_per_atom"] == pytest.approx(27.0)
    assert result["density"] == pytest.approx(float(structure.density))
    assert result["min_lattice_length"] == pytest.approx(3.0)
    assert result["max_lattice_length"] == pytest.approx(3.0)
    assert result["lattice_length_ratio"] == pytest.approx(1.0)


def test_symmetry_descriptors_for_cubic_structure():
    result = compute_symmetry_descriptors(cubic_fe_structure())

    assert result == {
        "spacegroup_number": 221,
        "spacegroup_symbol": "Pm-3m",
        "crystal_system": "cubic",
        "point_group_symbol": "m-3m",
        "symmetry_status": "ok",
    }


def test_symmetry_failure_is_row_safe():
    result = compute_symmetry_descriptors(object())

    assert result == {
        "spacegroup_number": None,
        "spacegroup_symbol": None,
        "crystal_system": None,
        "point_group_symbol": None,
        "symmetry_status": "error",
    }


def test_empty_structure_is_rejected():
    class EmptyStructure:
        def __len__(self):
            return 0

    with pytest.raises(
        ValueError,
        match="Structure contains no crystallographic sites",
    ):
        compute_unit_cell_descriptors(EmptyStructure())
