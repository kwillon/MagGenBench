from __future__ import annotations

import csv

import numpy as np
import pytest

from mvpipeline.analysis.validation_figures_v2 import (
    EXPECTED_STATUS_SOURCE,
    FIGURE_BASENAME,
    MODEL_ORDER,
    REJECTION_REASON_ORDER,
    ValidationRecord,
    build_validation_tables,
    read_ragged_validation_records,
)


def _records() -> list[ValidationRecord]:
    reasons = (
        "duplicate",
        "charge_imbalance",
        "cif_parse_error",
        "physically_impossible_distance",
    )

    records = []

    for model, reason in zip(MODEL_ORDER, reasons):
        records.append(
            ValidationRecord(
                model_name=model,
                model_short="test",
                status="validated",
                status_source=EXPECTED_STATUS_SOURCE,
                rejection_reason="",
                row_width=105,
            )
        )
        records.append(
            ValidationRecord(
                model_name=model,
                model_short="test",
                status="rejected",
                status_source=EXPECTED_STATUS_SOURCE,
                rejection_reason=reason,
                row_width=110,
            )
        )

    return records


def test_ragged_reader_uses_stable_left_and_right_columns(tmp_path):
    path = tmp_path / "validation.csv"

    header = [
        "sample_uid",
        "model_name",
        "model_short",
        "payload",
        "status",
        "status_source",
        "rejection_reason",
    ]

    rows = [
        [
            "a",
            "MatterGen",
            "mg",
            "payload",
            "validated",
            EXPECTED_STATUS_SOURCE,
            "",
        ],
        [
            "b",
            "Con-CDVAE",
            "cdvae",
            "payload",
            "extra-middle-field",
            "another-extra-field",
            "rejected",
            EXPECTED_STATUS_SOURCE,
            "charge_imbalance",
        ],
    ]

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)

    records = read_ragged_validation_records(path)

    assert len(records) == 2

    assert records[0].model_name == "MatterGen"
    assert records[0].status == "validated"
    assert records[0].rejection_reason == ""

    assert records[1].model_name == "Con-CDVAE"
    assert records[1].status == "rejected"
    assert records[1].rejection_reason == "charge_imbalance"
    assert records[1].row_width > len(header)


def test_validation_summary_counts_and_percentages():
    records = _records()

    model_summary, rejection_summary = build_validation_tables(
        records,
        expected_total_rows=len(records),
        expected_rows_per_model=2,
    )

    assert tuple(model_summary.index) == MODEL_ORDER

    assert np.allclose(
        model_summary["validated_percent"].to_numpy(dtype=float),
        50.0,
    )
    assert np.allclose(
        model_summary["rejected_percent"].to_numpy(dtype=float),
        50.0,
    )

    assert tuple(rejection_summary.index) == MODEL_ORDER
    assert tuple(rejection_summary.columns) == REJECTION_REASON_ORDER


def test_rejection_profiles_sum_to_100():
    _, rejection_summary = build_validation_tables(
        _records(),
        expected_total_rows=8,
        expected_rows_per_model=2,
    )

    assert np.allclose(
        rejection_summary.sum(axis=1).to_numpy(dtype=float),
        100.0,
    )


def test_validated_record_cannot_have_rejection_reason():
    records = _records()
    records[0] = ValidationRecord(
        model_name=records[0].model_name,
        model_short=records[0].model_short,
        status="validated",
        status_source=EXPECTED_STATUS_SOURCE,
        rejection_reason="duplicate",
        row_width=records[0].row_width,
    )

    with pytest.raises(
        RuntimeError,
        match="Validated structure has non-empty rejection reason",
    ):
        build_validation_tables(
            records,
            expected_total_rows=8,
            expected_rows_per_model=2,
        )


def test_rejected_record_requires_known_reason():
    records = _records()
    records[1] = ValidationRecord(
        model_name=records[1].model_name,
        model_short=records[1].model_short,
        status="rejected",
        status_source=EXPECTED_STATUS_SOURCE,
        rejection_reason="unknown_reason",
        row_width=records[1].row_width,
    )

    with pytest.raises(RuntimeError, match="Unexpected rejection reason"):
        build_validation_tables(
            records,
            expected_total_rows=8,
            expected_rows_per_model=2,
        )


def test_validation_figure_contract():
    assert FIGURE_BASENAME == "13_structural_validation_rejection_v2"
    assert REJECTION_REASON_ORDER == (
        "duplicate",
        "charge_imbalance",
        "cif_parse_error",
        "physically_impossible_distance",
        "unrealistic_density",
    )
