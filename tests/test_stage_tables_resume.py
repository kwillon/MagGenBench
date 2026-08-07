from __future__ import annotations

import pytest

from mvpipeline.io.stage_tables import (
    merge_stage_records_for_resume,
    merge_stage_records_incremental,
)


IDS = ["s1", "s2", "s3"]


def test_incremental_merge_allows_partial_checkpoint():
    result = merge_stage_records_incremental(
        structure_ids=IDS,
        previous_records=[
            {"structure_id": "s1", "status": "ok"},
        ],
        new_records=[
            {"structure_id": "s2", "status": "ok"},
        ],
    )

    assert [row["structure_id"] for row in result] == [
        "s1",
        "s2",
    ]


def test_incremental_merge_replaces_failed_record():
    result = merge_stage_records_incremental(
        structure_ids=IDS,
        previous_records=[
            {
                "structure_id": "s1",
                "status": "error",
                "value": "old",
            },
        ],
        new_records=[
            {
                "structure_id": "s1",
                "status": "ok",
                "value": "new",
            },
        ],
    )

    assert result == [
        {
            "structure_id": "s1",
            "status": "ok",
            "value": "new",
        }
    ]


def test_incremental_merge_preserves_manifest_order():
    result = merge_stage_records_incremental(
        structure_ids=IDS,
        previous_records=[
            {"structure_id": "s2", "status": "ok"},
            {"structure_id": "s1", "status": "ok"},
        ],
        new_records=[],
    )

    assert [row["structure_id"] for row in result] == [
        "s1",
        "s2",
    ]


def test_incremental_merge_rejects_unknown_id():
    with pytest.raises(
        ValueError,
        match="Unexpected structure_id",
    ):
        merge_stage_records_incremental(
            structure_ids=IDS,
            previous_records=[
                {
                    "structure_id": "foreign",
                    "status": "ok",
                },
            ],
            new_records=[],
        )


def test_incremental_merge_rejects_duplicate_id():
    with pytest.raises(
        ValueError,
        match="Duplicate structure_id",
    ):
        merge_stage_records_incremental(
            structure_ids=IDS,
            previous_records=[
                {"structure_id": "s1", "status": "ok"},
                {"structure_id": "s1", "status": "ok"},
            ],
            new_records=[],
        )


def test_incremental_merge_rejects_replacing_success():
    with pytest.raises(
        ValueError,
        match="already successful",
    ):
        merge_stage_records_incremental(
            structure_ids=IDS,
            previous_records=[
                {"structure_id": "s1", "status": "ok"},
            ],
            new_records=[
                {"structure_id": "s1", "status": "ok"},
            ],
        )


def test_final_resume_merge_requires_every_expected_id():
    with pytest.raises(
        ValueError,
        match="No final result available",
    ):
        merge_stage_records_for_resume(
            structure_ids=IDS,
            previous_records=[
                {"structure_id": "s1", "status": "ok"},
            ],
            new_records=[
                {"structure_id": "s2", "status": "ok"},
            ],
        )


def test_final_resume_merge_replaces_failure_and_is_complete():
    result = merge_stage_records_for_resume(
        structure_ids=IDS,
        previous_records=[
            {"structure_id": "s1", "status": "ok"},
            {"structure_id": "s2", "status": "error"},
        ],
        new_records=[
            {"structure_id": "s2", "status": "ok"},
            {"structure_id": "s3", "status": "ok"},
        ],
    )

    assert [row["structure_id"] for row in result] == IDS
    assert all(row["status"] == "ok" for row in result)
