from __future__ import annotations

import hashlib
from pathlib import Path

from mvpipeline.magnetism.config import load_magnetism_config


EXPECTED_ARTIFACT_SHA256 = (
    "a76d22393b4f7a2a32e9d57191ea88788a0e5596f262ee0048cc2a9a0facb936"
)
EXPECTED_LABELS_SHA256 = (
    "8fdff659a05332499424f1f81e4817dd332cc60f2c8bd04b5b9620b66fd88344"
)


def test_dxmag_runtime_metadata_is_complete_and_safe() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    config = load_magnetism_config(
        repo_root / "config" / "magnetism.yaml"
    )

    # The production model profile is documented but not enabled by default.
    assert config.backend.name == "fake"

    settings = config.sklearn
    metadata = settings.metadata

    assert settings.name == "sklearn"
    assert settings.model_name == "dxmag-lightgbm-composition"
    assert settings.artifact_path == (
        "models/magnetism/magmom_model_dxmag.pkl"
    )
    assert settings.baseline_error == 0.25174292069227294
    assert settings.allow_unsafe_compatibility is False

    assert metadata.model_name == "dxmag-lightgbm-composition"
    assert metadata.model_version == (
        "donor-1b29ec689054ef51fe739607d63fa0f57e6f6bb8"
    )
    assert metadata.artifact_sha256 == EXPECTED_ARTIFACT_SHA256
    assert metadata.feature_set == "composition_magpie"
    assert metadata.feature_count == 132
    assert len(metadata.feature_labels) == 132

    labels_hash = hashlib.sha256(
        "\n".join(metadata.feature_labels).encode("utf-8")
    ).hexdigest()

    assert labels_hash == EXPECTED_LABELS_SHA256

    assert metadata.target_name == (
        "median total magnetization "
        "(DXMag total magnetization (muB/f.u.))"
    )
    assert metadata.moment_unit == "muB"
    assert metadata.moment_normalization == "per_formula_unit"
    assert metadata.matminer_version == "0.8.0"
    assert metadata.sklearn_version == (
        "runtime-1.7.2; training-version-unpinned"
    )
