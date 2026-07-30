from __future__ import annotations

from dataclasses import dataclass

from ..schema import MagnetismInput, MagnetismResult, MagnetismStatus
from ..uncertainty import confidence_from_uncertainty_proxy, risk_level_from_confidence


@dataclass(frozen=True)
class FakeMagnetismBackend:
    """Deterministic backend for local tests and pipeline wiring."""

    name: str = "fake"
    model_name: str = "deterministic-fake-v1"
    moment_unit: str = "unknown"
    moment_normalization: str = "unknown"
    baseline_error: float = 0.25

    def predict(self, item: MagnetismInput) -> MagnetismResult:
        try:
            if item.features is not None:
                feature_sum = sum(float(x) for x in item.features)
            else:
                feature_sum = sum(float(v) for v in item.composition.values())

            predicted = round(feature_sum * 0.1, 12)
            uncertainty_proxy = round(abs(predicted) * 0.01, 12)
            confidence = confidence_from_uncertainty_proxy(
                uncertainty_proxy, self.baseline_error
            )

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
            )
        except Exception as exc:
            return MagnetismResult(
                structure_id=item.structure_id,
                status=MagnetismStatus.ERROR,
                error_code="fake_magnetism_error",
                error_message=str(exc),
                backend=self.name,
                model_name=self.model_name,
                moment_unit=self.moment_unit,
                moment_normalization=self.moment_normalization,
            )
