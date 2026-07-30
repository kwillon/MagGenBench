from __future__ import annotations


def confidence_from_uncertainty_proxy(
    uncertainty_proxy: float, baseline_error: float
) -> float:
    denom = float(baseline_error) + 1e-8
    if denom <= 0:
        denom = 1e-8
    return 1.0 / (1.0 + (float(uncertainty_proxy) / denom))


def risk_level_from_confidence(confidence_score: float) -> str:
    if confidence_score >= 0.7:
        return "low"
    if confidence_score >= 0.4:
        return "medium"
    return "high"
