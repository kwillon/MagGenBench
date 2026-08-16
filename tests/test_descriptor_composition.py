from __future__ import annotations

import math

import pytest
from pymatgen.core import Composition

from mvpipeline.descriptors.composition import compute_composition_descriptors


def test_fe2o3_composition_descriptors():
    result = compute_composition_descriptors(
        Composition("Fe2O3"),
        magnetic_screening_elements={"Fe"},
    )

    assert result["n_elements"] == 2
    assert result["min_element_fraction"] == pytest.approx(0.4)
    assert result["max_element_fraction"] == pytest.approx(0.6)
    assert result["composition_entropy"] == pytest.approx(
        -(0.4 * math.log(0.4) + 0.6 * math.log(0.6))
    )
    assert result["transition_metal_fraction"] == pytest.approx(0.4)
    assert result["d_block_fraction"] == pytest.approx(0.4)
    assert result["f_block_fraction"] == pytest.approx(0.0)
    assert result["lanthanide_fraction"] == pytest.approx(0.0)
    assert result["actinide_fraction"] == pytest.approx(0.0)
    assert result["magnetic_screening_element_fraction"] == pytest.approx(0.4)


def test_periodic_categories_preserve_pymatgen_overlap():
    result = compute_composition_descriptors(
        Composition({"La": 1, "Ce": 1, "Lu": 1}),
        magnetic_screening_elements={"La", "Ce"},
    )

    assert result["n_elements"] == 3
    assert result["transition_metal_fraction"] == pytest.approx(1 / 3)
    assert result["d_block_fraction"] == pytest.approx(1 / 3)
    assert result["f_block_fraction"] == pytest.approx(2 / 3)
    assert result["lanthanide_fraction"] == pytest.approx(1.0)
    assert result["actinide_fraction"] == pytest.approx(0.0)
    assert result["magnetic_screening_element_fraction"] == pytest.approx(2 / 3)


def test_single_element_entropy_is_zero():
    result = compute_composition_descriptors(
        Composition("Fe"),
        magnetic_screening_elements={"Fe"},
    )

    assert result["composition_entropy"] == pytest.approx(0.0)
    assert result["min_element_fraction"] == pytest.approx(1.0)
    assert result["max_element_fraction"] == pytest.approx(1.0)


def test_empty_composition_is_rejected():
    class EmptyComposition:
        def get_el_amt_dict(self):
            return {}

    with pytest.raises(
        ValueError,
        match="Composition contains no positive elemental amounts",
    ):
        compute_composition_descriptors(
            EmptyComposition(),
            magnetic_screening_elements=set(),
        )
