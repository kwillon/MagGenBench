from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Tuple


def _string_tuple(values: Sequence[Any]) -> Tuple[str, ...]:
    return tuple(str(value) for value in values)


@dataclass(frozen=True)
class MagnetismModelMetadata:
    model_name: str = ""
    model_version: str = ""
    artifact_path: str = ""
    artifact_sha256: str = ""
    feature_set: str = "composition_magpie"
    feature_labels: Tuple[str, ...] = field(default_factory=tuple)
    feature_count: Optional[int] = None
    target_name: str = ""
    moment_unit: str = "unknown"
    moment_normalization: str = "unknown"
    sklearn_version: str = ""
    matminer_version: str = ""

    def __post_init__(self) -> None:
        if self.artifact_path and Path(self.artifact_path).is_absolute():
            raise ValueError("Magnetism model artifact_path must be relative")
        if self.feature_count is not None and self.feature_count < 0:
            raise ValueError("feature_count must be non-negative")


@dataclass(frozen=True)
class MagnetismBackendSettings:
    name: str = "fake"
    model_name: str = "deterministic-fake-v1"
    artifact_path: str = ""
    baseline_error: float = 0.25
    uncertainty_samples: int = 12
    uncertainty_noise: float = 1e-4
    uncertainty_seed: int = 42
    allow_unsafe_compatibility: bool = False
    metadata: MagnetismModelMetadata = MagnetismModelMetadata()

    def __post_init__(self) -> None:
        if self.artifact_path and Path(self.artifact_path).is_absolute():
            raise ValueError("Magnetism artifact_path must be relative")
        if self.baseline_error <= 0:
            raise ValueError("baseline_error must be positive")
        if self.uncertainty_samples < 0:
            raise ValueError("uncertainty_samples must be non-negative")
        if self.uncertainty_noise < 0:
            raise ValueError("uncertainty_noise must be non-negative")


@dataclass(frozen=True)
class MagneticElementGroups:
    transition_3d: Tuple[str, ...] = field(default_factory=tuple)
    selected_4d_5d: Tuple[str, ...] = field(default_factory=tuple)
    lanthanides: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def all_elements(self) -> frozenset[str]:
        return frozenset(self.transition_3d + self.selected_4d_5d + self.lanthanides)


@dataclass(frozen=True)
class MagnetismScreeningRules:
    require_magnetic_element: bool = True
    reject_classes: Tuple[str, ...] = field(default_factory=tuple)
    low_priority_classes: Tuple[str, ...] = field(default_factory=tuple)
    high_priority_classes: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MagnetismConfig:
    backend: MagnetismBackendSettings = MagnetismBackendSettings()
    sklearn: MagnetismBackendSettings = MagnetismBackendSettings(
        name="sklearn",
        model_name="magm-donor-compatible",
        artifact_path="models/magnetism/magmom_model_dxmag.pkl",
        metadata=MagnetismModelMetadata(
            model_name="magm-donor-compatible",
            artifact_path="models/magnetism/magmom_model_dxmag.pkl",
            feature_set="composition_magpie",
            moment_unit="unknown",
            moment_normalization="unknown",
        ),
    )
    magnetic_elements: MagneticElementGroups = MagneticElementGroups()
    screening_rules: MagnetismScreeningRules = MagnetismScreeningRules()


def metadata_from_mapping(data: Mapping[str, Any]) -> MagnetismModelMetadata:
    labels: Sequence[str] = data.get("feature_labels", ()) or ()
    feature_count = data.get("feature_count")
    if feature_count in ("", None):
        parsed_feature_count: Optional[int] = None
    else:
        parsed_feature_count = int(feature_count)
    return MagnetismModelMetadata(
        model_name=str(data.get("model_name", "")),
        model_version=str(data.get("model_version", "")),
        artifact_path=str(data.get("artifact_path", "")),
        artifact_sha256=str(data.get("artifact_sha256", "")),
        feature_set=str(data.get("feature_set", "composition_magpie")),
        feature_labels=tuple(str(label) for label in labels),
        feature_count=parsed_feature_count,
        target_name=str(data.get("target_name", "")),
        moment_unit=str(data.get("moment_unit", "unknown")),
        moment_normalization=str(data.get("moment_normalization", "unknown")),
        sklearn_version=str(data.get("sklearn_version", "")),
        matminer_version=str(data.get("matminer_version", "")),
    )


def backend_settings_from_mapping(
    data: Mapping[str, Any], defaults: Optional[MagnetismBackendSettings] = None
) -> MagnetismBackendSettings:
    base = defaults or MagnetismBackendSettings()
    metadata_data = data.get("metadata", {}) or {}
    metadata = metadata_from_mapping(metadata_data) if metadata_data else base.metadata
    return MagnetismBackendSettings(
        name=str(data.get("name", base.name)),
        model_name=str(data.get("model_name", base.model_name)),
        artifact_path=str(data.get("artifact_path", base.artifact_path)),
        baseline_error=float(data.get("baseline_error", base.baseline_error)),
        uncertainty_samples=int(
            data.get("uncertainty_samples", base.uncertainty_samples)
        ),
        uncertainty_noise=float(data.get("uncertainty_noise", base.uncertainty_noise)),
        uncertainty_seed=int(data.get("uncertainty_seed", base.uncertainty_seed)),
        allow_unsafe_compatibility=bool(
            data.get("allow_unsafe_compatibility", base.allow_unsafe_compatibility)
        ),
        metadata=metadata,
    )


def magnetic_element_groups_from_mapping(
    data: Mapping[str, Any],
) -> MagneticElementGroups:
    return MagneticElementGroups(
        transition_3d=_string_tuple(data.get("transition_3d", ()) or ()),
        selected_4d_5d=_string_tuple(data.get("selected_4d_5d", ()) or ()),
        lanthanides=_string_tuple(data.get("lanthanides", ()) or ()),
    )


def screening_rules_from_mapping(data: Mapping[str, Any]) -> MagnetismScreeningRules:
    return MagnetismScreeningRules(
        require_magnetic_element=bool(data.get("require_magnetic_element", True)),
        reject_classes=_string_tuple(data.get("reject_classes", ()) or ()),
        low_priority_classes=_string_tuple(data.get("low_priority_classes", ()) or ()),
        high_priority_classes=_string_tuple(
            data.get("high_priority_classes", ()) or ()
        ),
    )


def magnetism_config_from_mapping(data: Mapping[str, Any]) -> MagnetismConfig:
    magnetism = data.get("magnetism", data) or {}
    prediction = magnetism.get("prediction", magnetism) or {}
    default_cfg = MagnetismConfig()
    return MagnetismConfig(
        backend=backend_settings_from_mapping(
            prediction.get("backend", {}) or {}, default_cfg.backend
        ),
        sklearn=backend_settings_from_mapping(
            prediction.get("sklearn", {}) or {}, default_cfg.sklearn
        ),
        magnetic_elements=magnetic_element_groups_from_mapping(
            magnetism.get("magnetic_elements", {}) or {}
        ),
        screening_rules=screening_rules_from_mapping(
            magnetism.get("screening_rules", {}) or {}
        ),
    )


def load_magnetism_config(path: str | Path) -> MagnetismConfig:
    """Load magnetism config from YAML.

    PyYAML is imported only when this function is called.
    """

    import yaml

    with Path(path).open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return magnetism_config_from_mapping(data)
