import pytest

from mvpipeline.magnetism import (
    MagnetismResult,
    MagnetismStatus,
    confidence_from_uncertainty_proxy,
    risk_level_from_confidence,
)
from mvpipeline.magnetism.records import (
    MAGNETISM_RECORD_FIELDS,
    magnetic_result_to_record,
)


def test_magnetic_result_contract_defaults_units_and_normalization_to_unknown():
    result = MagnetismResult(
        structure_id="m1",
        status=MagnetismStatus.OK,
        predicted_moment_value=1.25,
    )
    record = magnetic_result_to_record(result)

    assert record["structure_id"] == "m1"
    assert record["status"] == "ok"
    assert record["moment_unit"] == "unknown"
    assert record["moment_normalization"] == "unknown"
    assert "uncertainty_proxy" in MAGNETISM_RECORD_FIELDS
    assert "error_code" in record
    assert "error_message" in record


def test_uncertainty_proxy_confidence_and_risk_are_explicit():
    confidence = confidence_from_uncertainty_proxy(
        uncertainty_proxy=0.25,
        baseline_error=0.25,
    )

    assert confidence == pytest.approx(0.50000001)
    assert risk_level_from_confidence(confidence) == "medium"
