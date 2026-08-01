from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..config import MagnetismBackendSettings, MagnetismModelMetadata
from ..features import CompositionFeatureProvider, MagpieCompositionFeatureProvider
from ..predictor import (
    NoiseGenerator,
    confidence_from_uncertainty_proxy,
    expected_feature_count,
    predict_scalar,
    risk_level_from_confidence,
    uncertainty_proxy_from_feature_noise,
    validate_feature_count,
    validate_feature_vector,
)
from ..schema import MagnetismInput, MagnetismResult, MagnetismStatus

ModelLoader = Callable[[str], Any]


def _default_model_loader(artifact_path: str) -> Any:
    if not artifact_path:
        raise ValueError("Magnetism sklearn backend requires artifact_path")
    try:
        import joblib
    except ImportError as exc:
        raise ImportError(
            "Magnetism sklearn backend requires optional dependency 'joblib'."
        ) from exc
    return joblib.load(artifact_path)


@dataclass
class SklearnMagnetismBackend:
    settings: MagnetismBackendSettings = field(
        default_factory=lambda: MagnetismBackendSettings(name="sklearn")
    )
    model_loader: ModelLoader = _default_model_loader
    featurizer: Optional[CompositionFeatureProvider] = None
    noise_generator: Optional[NoiseGenerator] = None
    name: str = "sklearn"
    _model: Any = field(default=None, init=False, repr=False)

    @property
    def model_name(self) -> str:
        return self.metadata.model_name or self.settings.model_name

    @property
    def metadata(self) -> MagnetismModelMetadata:
        return self.settings.metadata

    @property
    def moment_unit(self) -> str:
        return self.metadata.moment_unit or "unknown"

    @property
    def moment_normalization(self) -> str:
        return self.metadata.moment_normalization or "unknown"

    def _load_model(self) -> Any:
        if self._model is None:
            self._model = self.model_loader(self.settings.artifact_path)
        return self._model

    def _feature_provider(self) -> CompositionFeatureProvider:
        if self.featurizer is None:
            self.featurizer = MagpieCompositionFeatureProvider()
        return self.featurizer

    def _build_features(self, item: MagnetismInput) -> list[float]:
        if item.features is not None:
            return validate_feature_vector(item.features)
        provider = self._feature_provider()
        composition = getattr(item.structure, "composition", item.composition)
        return validate_feature_vector(provider.featurize(composition))

    def _ensure_feature_order_is_known(self) -> None:
        if self.settings.allow_unsafe_compatibility:
            return
        if not self.metadata.feature_labels:
            raise ValueError(
                "Model metadata does not provide exact feature order; set "
                "allow_unsafe_compatibility only after explicit verification"
            )

    def predict(self, item: MagnetismInput) -> MagnetismResult:
        try:
            model = self._load_model()
        except ImportError as exc:
            return self._error(
                item.structure_id,
                "missing_optional_dependency",
                str(exc),
            )
        except ValueError as exc:
            return self._error(item.structure_id, "model_configuration_error", str(exc))

        try:
            self._ensure_feature_order_is_known()
            features = self._build_features(item)
            count = expected_feature_count(model, self.metadata.feature_count)
            validate_feature_count(features, count)
            predicted = predict_scalar(model, features)
            noise_generator = self.noise_generator
            if noise_generator is None:
                uncertainty_proxy = uncertainty_proxy_from_feature_noise(
                    model=model,
                    features=features,
                    samples=self.settings.uncertainty_samples,
                    noise_scale=self.settings.uncertainty_noise,
                    seed=self.settings.uncertainty_seed,
                )
            else:
                uncertainty_proxy = uncertainty_proxy_from_feature_noise(
                    model=model,
                    features=features,
                    samples=self.settings.uncertainty_samples,
                    noise_scale=self.settings.uncertainty_noise,
                    seed=self.settings.uncertainty_seed,
                    noise_generator=noise_generator,
                )
            confidence = confidence_from_uncertainty_proxy(
                uncertainty_proxy, self.settings.baseline_error
            )
        except ImportError as exc:
            return self._error(
                item.structure_id,
                "missing_optional_dependency",
                str(exc),
            )
        except ValueError as exc:
            return self._error(item.structure_id, "prediction_contract_error", str(exc))

        return MagnetismResult(
            structure_id=item.structure_id,
            status=MagnetismStatus.OK,
            backend=self.name,
            model_name=self.model_name,
            predicted_moment_value=predicted,
            moment_unit=self.moment_unit,
            moment_normalization=self.moment_normalization,
            uncertainty_proxy=uncertainty_proxy,
            confidence_score=confidence,
            risk_level=risk_level_from_confidence(confidence),
            details={
                "artifact_path": self.settings.artifact_path,
                "feature_set": self.metadata.feature_set,
                "feature_count": len(features),
                "model_version": self.metadata.model_version,
                "target_name": self.metadata.target_name,
            },
        )

    def _error(self, structure_id: str, code: str, message: str) -> MagnetismResult:
        return MagnetismResult(
            structure_id=structure_id,
            status=MagnetismStatus.ERROR,
            error_code=code,
            error_message=message,
            backend=self.name,
            model_name=self.model_name,
            moment_unit=self.moment_unit,
            moment_normalization=self.moment_normalization,
        )
