from __future__ import annotations

import math
import random
from typing import Any, Callable, Sequence

from .uncertainty import confidence_from_uncertainty_proxy, risk_level_from_confidence


NoiseGenerator = Callable[[Sequence[float], float, random.Random], Sequence[float]]


def validate_feature_vector(features: Sequence[float]) -> list[float]:
    values = [float(value) for value in features]
    if not values:
        raise ValueError("Feature vector must not be empty")
    if any(not math.isfinite(value) for value in values):
        raise ValueError("Feature vector contains NaN or infinite values")
    return values


def expected_feature_count(model: Any, metadata_count: int | None) -> int | None:
    if metadata_count is not None:
        return metadata_count
    count = getattr(model, "n_features_in_", None)
    if count is None:
        return None
    return int(count)


def validate_feature_count(features: Sequence[float], expected_count: int | None) -> None:
    if expected_count is not None and len(features) != expected_count:
        raise ValueError(
            f"Feature count mismatch: expected {expected_count}, got {len(features)}"
        )


def scalar_prediction(value: Any) -> float:
    if hasattr(value, "item"):
        try:
            scalar = float(value.item())
        except (TypeError, ValueError) as exc:
            raise ValueError("Prediction is not a scalar finite number") from exc
    elif isinstance(value, (list, tuple)):
        current = value
        while isinstance(current, (list, tuple)):
            if len(current) != 1:
                raise ValueError("Prediction must contain exactly one value")
            current = current[0]
        scalar = float(current)
    else:
        try:
            scalar = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Prediction is not a scalar finite number") from exc
    if not math.isfinite(scalar):
        raise ValueError("Prediction is not a scalar finite number")
    return scalar


def predict_scalar(model: Any, features: Sequence[float]) -> float:
    if not hasattr(model, "predict"):
        raise ValueError("Model does not provide predict")
    return scalar_prediction(model.predict([list(features)]))


def default_noise_generator(
    features: Sequence[float], noise_scale: float, rng: random.Random
) -> Sequence[float]:
    return [
        value + rng.gauss(0.0, max(abs(value), 1.0) * noise_scale)
        for value in features
    ]


def uncertainty_proxy_from_feature_noise(
    model: Any,
    features: Sequence[float],
    samples: int,
    noise_scale: float,
    seed: int,
    noise_generator: NoiseGenerator = default_noise_generator,
) -> float:
    if samples <= 0 or noise_scale <= 0:
        return 0.0
    rng = random.Random(seed)
    predictions = [
        predict_scalar(model, noise_generator(features, noise_scale, rng))
        for _ in range(samples)
    ]
    if len(predictions) < 2:
        return 0.0
    mean = sum(predictions) / float(len(predictions))
    variance = sum((value - mean) ** 2 for value in predictions) / float(
        len(predictions)
    )
    return math.sqrt(variance)


__all__ = [
    "confidence_from_uncertainty_proxy",
    "default_noise_generator",
    "expected_feature_count",
    "predict_scalar",
    "risk_level_from_confidence",
    "scalar_prediction",
    "uncertainty_proxy_from_feature_noise",
    "validate_feature_count",
    "validate_feature_vector",
]
