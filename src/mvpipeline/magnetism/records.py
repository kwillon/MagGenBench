from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

from .schema import MagnetismResult


MAGNETISM_RECORD_FIELDS = [
    "structure_id",
    "status",
    "error_code",
    "error_message",
    "backend",
    "model_name",
    "predicted_moment_value",
    "moment_unit",
    "moment_normalization",
    "uncertainty_proxy",
    "confidence_score",
    "risk_level",
    "details",
]


def magnetic_result_to_record(result: MagnetismResult) -> Dict[str, Any]:
    record = asdict(result)
    record["status"] = result.status.value
    return record
