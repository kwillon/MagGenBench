from __future__ import annotations

import math
from pathlib import Path

import pytest

from mvpipeline.descriptors.batch_v2 import (
    extract_magnetic_descriptor_v2_rows,
)
from mvpipeline.descriptors.config_v2 import (
    load_magnetic_descriptor_v2_runtime_config,
)
from mvpipeline.descriptors.extractor_v2 import extract_magnetic_descriptor_v2
from mvpipeline.descriptors.magnetic_composition import (
    compute_magnetic_composition_descriptors,
)
from mvpipeline.descriptors.schema_v2 import (
    MAGNETIC_DESCRIPTOR_V2_SCIENTIFIC_FIELDS,
    DescriptorV2Status,
    MagneticDescriptorInput,
)


REPO_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_SCIENTIFIC_FIELDS = (
    "transition_3d_fraction",
    "selected_4d_5d_fraction",
    "configured_lanthanide_fraction",
    "n_transition_3d_species",
    "n_selected_4d_5d_species",
    "n_configured_lanthanide_species",
    "contains_3d_and_configured_lanthanide",
    "magnetic_site_nearest_neighbor_distance_min",
    "magnetic_site_nearest_neighbor_distance_mean",
    "magnetic_site_nearest_neighbor_distance_std",
    "magnetic_site_nearest_magnetic_neighbor_distance_min",
    "magnetic_site_nearest_magnetic_neighbor_distance_mean",
    "magnetic_site_nearest_magnetic_neighbor_distance_std",
    "magnetic_site_coordination_mean",
    "magnetic_site_coordination_std",
    "magnetic_site_magnetic_coordination_mean",
    "magnetic_site_magnetic_coordination_std",
    "magnetic_site_magnetic_neighbor_fraction_mean",
    "magnetic_site_magnetic_neighbor_fraction_std",
    "n_symmetry_unique_sites",
    "symmetry_unique_site_fraction",
    "n_symmetry_unique_magnetic_sites",
    "symmetry_unique_magnetic_site_fraction",
    "site_multiplicity_entropy",
)


@pytest.fixture()
def config():
    return load_magnetic_descriptor_v2_runtime_config(
        REPO_ROOT / "config/descriptors_v2_magnetic.yaml",
        project_root=REPO_ROOT,
    )


def test_descriptor_v2_scientific_schema_is_exact():
    assert MAGNETIC_DESCRIPTOR_V2_SCIENTIFIC_FIELDS == EXPECTED_SCIENTIFIC_FIELDS


def test_magnetic_composition_categories_use_project_config(config):
    from pymatgen.core import Composition

    assert "Fe" in config.magnetic_elements.transition_3d
    assert "Mo" in config.magnetic_elements.selected_4d_5d
    assert "Nd" in config.magnetic_elements.lanthanides

    values = compute_magnetic_composition_descriptors(
        Composition("Fe2MoNdO4"),
        config.magnetic_elements,
    )

    assert values["transition_3d_fraction"] == pytest.approx(2 / 8)
    assert values["selected_4d_5d_fraction"] == pytest.approx(1 / 8)
    assert values["configured_lanthanide_fraction"] == pytest.approx(1 / 8)
    assert values["n_transition_3d_species"] == 1
    assert values["n_selected_4d_5d_species"] == 1
    assert values["n_configured_lanthanide_species"] == 1
    assert values["contains_3d_and_configured_lanthanide"] is True


def test_fractional_occupancies_and_magnetic_site_membership(config):
    from pymatgen.core import Lattice, Structure
    from mvpipeline.descriptors.magnetic_sites import configured_magnetic_site_indices

    structure = Structure(
        Lattice.cubic(5.0),
        [{"Fe": 0.25, "Al": 0.5}, {"Nd": 0.5}, "O"],
        [[0, 0, 0], [0.25, 0.25, 0.25], [0.5, 0.5, 0.5]],
    )
    values = compute_magnetic_composition_descriptors(structure.composition, config.magnetic_elements)
    assert values["transition_3d_fraction"] == pytest.approx(0.25 / 2.25)
    assert values["configured_lanthanide_fraction"] == pytest.approx(0.5 / 2.25)
    assert configured_magnetic_site_indices(structure, config.configured_magnetic_elements) == [0, 1]


def test_nonmagnetic_structure_is_ok_with_not_applicable_geometry(config):
    from pymatgen.core import Lattice, Structure

    structure = Structure(
        Lattice.cubic(4.0),
        ["Na", "Cl"],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
    )

    result = extract_magnetic_descriptor_v2(
        MagneticDescriptorInput(
            sample_uid="nonmag",
            structure_id="nonmag",
            structure=structure,
        ),
        magnetic_elements=config.magnetic_elements,
        configured_magnetic_elements=config.configured_magnetic_elements,
    )

    assert result.status == DescriptorV2Status.OK
    assert result.values["transition_3d_fraction"] == 0.0
    assert result.values["selected_4d_5d_fraction"] == 0.0
    assert result.values["configured_lanthanide_fraction"] == 0.0
    assert result.values["n_transition_3d_species"] == 0
    assert result.values["n_selected_4d_5d_species"] == 0
    assert result.values["n_configured_lanthanide_species"] == 0
    assert result.values["magnetic_geometry_status"] == "not_applicable"
    assert result.values["magnetic_site_coordination_mean"] is None
    assert result.values["n_symmetry_unique_magnetic_sites"] == 0
    assert result.values["symmetry_unique_magnetic_site_fraction"] is None


def test_periodic_magnetic_self_image_is_valid_neighbor(config):
    from pymatgen.core import Lattice, Structure

    structure = Structure(Lattice.cubic(3.0), ["Fe"], [[0, 0, 0]])

    result = extract_magnetic_descriptor_v2(
        MagneticDescriptorInput(
            sample_uid="fe",
            structure_id="fe",
            structure=structure,
        ),
        magnetic_elements=config.magnetic_elements,
        configured_magnetic_elements=config.configured_magnetic_elements,
    )

    assert result.status == DescriptorV2Status.OK
    assert result.values[
        "magnetic_site_nearest_magnetic_neighbor_distance_min"
    ] == pytest.approx(3.0)
    assert result.values["magnetic_site_nearest_neighbor_distance_min"] == (
        pytest.approx(3.0)
    )


def test_magnetic_coordination_uses_minimum_distance_shell(config):
    from pymatgen.core import Lattice, Structure

    structure = Structure(
        Lattice.cubic(4.0),
        ["Fe", "O"],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
    )

    result = extract_magnetic_descriptor_v2(
        MagneticDescriptorInput(
            sample_uid="feo",
            structure_id="feo",
            structure=structure,
        ),
        magnetic_elements=config.magnetic_elements,
        configured_magnetic_elements=config.configured_magnetic_elements,
    )

    assert result.status == DescriptorV2Status.OK
    assert result.values["magnetic_geometry_status"] == "ok"
    assert result.values["magnetic_site_coordination_mean"] > 0
    assert result.values["magnetic_site_magnetic_coordination_mean"] >= 0
    assert 0 <= result.values[
        "magnetic_site_magnetic_neighbor_fraction_mean"
    ] <= 1


def test_magnetic_symmetry_for_simple_high_symmetry_structure(config):
    from pymatgen.core import Lattice, Structure

    structure = Structure(Lattice.cubic(3.0), ["Fe"], [[0, 0, 0]])

    result = extract_magnetic_descriptor_v2(
        MagneticDescriptorInput(
            sample_uid="sym",
            structure_id="sym",
            structure=structure,
        ),
        magnetic_elements=config.magnetic_elements,
        configured_magnetic_elements=config.configured_magnetic_elements,
    )

    assert result.values["magnetic_symmetry_status"] == "ok"
    assert result.values["n_symmetry_unique_sites"] == 1
    assert result.values["symmetry_unique_site_fraction"] == pytest.approx(1.0)
    assert result.values["n_symmetry_unique_magnetic_sites"] == 1
    assert result.values[
        "symmetry_unique_magnetic_site_fraction"
    ] == pytest.approx(1.0)
    assert result.values["site_multiplicity_entropy"] == pytest.approx(0.0)


def test_descriptor_v2_batch_is_row_preserving_with_parse_error(tmp_path, config):
    from pymatgen.core import Lattice, Structure

    magnetic_cif = tmp_path / "fe.cif"
    nonmagnetic_cif = tmp_path / "nacl.cif"
    missing_cif = tmp_path / "missing.cif"

    magnetic_cif.write_text(
        Structure(Lattice.cubic(3.0), ["Fe"], [[0, 0, 0]]).to(fmt="cif"),
        encoding="utf-8",
    )
    nonmagnetic_cif.write_text(
        Structure(
            Lattice.cubic(4.0),
            ["Na", "Cl"],
            [[0, 0, 0], [0.5, 0.5, 0.5]],
        ).to(fmt="cif"),
        encoding="utf-8",
    )

    rows = [
        {
            "sample_uid": "mag",
            "structure_id": "mag",
            "analysis_cohort": "test",
            "analysis_family": "test",
            "analysis_state": "test",
            "model_name": "test",
            "model_short": "t",
            "formula_reduced": "Fe",
            "formula_full_canonical": "Fe1",
            "cif_path": str(magnetic_cif),
        },
        {
            "sample_uid": "nonmag",
            "structure_id": "nonmag",
            "analysis_cohort": "test",
            "analysis_family": "test",
            "analysis_state": "test",
            "model_name": "test",
            "model_short": "t",
            "formula_reduced": "NaCl",
            "formula_full_canonical": "Na1 Cl1",
            "cif_path": str(nonmagnetic_cif),
        },
        {
            "sample_uid": "bad",
            "structure_id": "bad",
            "analysis_cohort": "test",
            "analysis_family": "test",
            "analysis_state": "test",
            "model_name": "test",
            "model_short": "t",
            "formula_reduced": "Fe",
            "formula_full_canonical": "Fe1",
            "cif_path": str(missing_cif),
        },
    ]

    output = extract_magnetic_descriptor_v2_rows(
        rows,
        config=config,
        repo_root=tmp_path,
    )

    assert [row["structure_id"] for row in output] == ["mag", "nonmag", "bad"]
    assert [row["descriptor_v2_status"] for row in output] == [
        "ok",
        "ok",
        "error",
    ]
    assert output[1]["magnetic_geometry_status"] == "not_applicable"
    assert output[2]["descriptor_v2_error_code"] == "cif_parse_error"
    assert output[2]["magnetic_geometry_status"] == "not_computed"
