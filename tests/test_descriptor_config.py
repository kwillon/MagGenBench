from __future__ import annotations

from mvpipeline.descriptors.config import load_descriptor_runtime_config


def test_project_descriptor_v1_runtime_config():
    config = load_descriptor_runtime_config(
        "config/descriptors.yaml",
        project_root=".",
    )

    assert config.schema_version == "v1"
    assert config.reference_pymatgen_version == "2025.6.14"

    assert config.symprec == 0.01
    assert config.angle_tolerance == 5.0

    assert config.local_geometry_method == "MinimumDistanceNN"
    assert config.local_geometry_cutoff == 10.0
    assert config.local_geometry_tolerance == 0.1
    assert config.local_geometry_get_all_sites is False
    assert config.local_geometry_use_weights is False

    assert len(config.magnetic_screening_elements) == 28

    for symbol in ("Fe", "Ce", "Ir"):
        assert symbol in config.magnetic_screening_elements

    for symbol in ("Zn", "Y", "La", "Lu"):
        assert symbol not in config.magnetic_screening_elements
