from __future__ import annotations

import csv

import pytest

from mvpipeline.analysis.unified import (
    AnalysisCohortSpec,
    DOWNSTREAM_FIELDS,
    build_cohort_analysis_rows,
    run_unified_analysis,
)
from mvpipeline.descriptors.records import DESCRIPTOR_RECORD_FIELDS, IDENTITY_FIELDS


def _descriptor(uid: str, **overrides: str) -> dict[str, str]:
    row = {field: "" for field in DESCRIPTOR_RECORD_FIELDS}
    row.update(
        {
            "sample_uid": uid,
            "structure_id": uid,
            "model_name": "MatterGen",
            "model_short": "mattergen",
            "run_uid": "run-1",
            "source_sample_id": uid,
            "cif_path": f"samples/{uid}.cif",
            "descriptor_schema_version": "v1",
            "descriptor_v1_source": "cif_recomputed",
            "descriptor_v1_status": "ok",
        }
    )
    row.update(overrides)
    return row


def _joined(uid: str, **overrides: str) -> dict[str, str]:
    row = {field: "" for field in [*IDENTITY_FIELDS, *DOWNSTREAM_FIELDS]}
    row.update(
        {
            "sample_uid": uid,
            "structure_id": uid,
            "model_name": "MatterGen",
            "model_short": "mattergen",
            "run_uid": "run-1",
            "source_sample_id": uid,
            "cif_path": f"/old/location/{uid}.cif",
            "energy_status": "ok",
            "magnetism_status": "ok",
        }
    )
    row.update(overrides)
    return row


def _write_csv(path, rows: list[dict[str, str]]) -> None:
    fieldnames = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_build_preserves_descriptor_order_and_labels() -> None:
    descriptors = [_descriptor("b"), _descriptor("a")]
    joined = [_joined("a"), _joined("b")]

    rows = build_cohort_analysis_rows(
        descriptors,
        joined,
        analysis_cohort="mattergen_baseline",
        analysis_family="MatterGen",
        analysis_state="baseline",
    )

    assert [row["sample_uid"] for row in rows] == ["b", "a"]
    assert rows[0]["analysis_cohort"] == "mattergen_baseline"
    assert rows[0]["analysis_family"] == "MatterGen"
    assert rows[0]["analysis_state"] == "baseline"
    assert rows[0]["cif_path"] == "samples/b.cif"


def test_uid_set_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="UID sets differ"):
        build_cohort_analysis_rows(
            [_descriptor("a")],
            [_joined("b")],
            analysis_cohort="test",
            analysis_family="Test",
            analysis_state="baseline",
        )


def test_duplicate_uid_is_rejected() -> None:
    with pytest.raises(ValueError, match="Duplicate sample_uid"):
        build_cohort_analysis_rows(
            [_descriptor("a"), _descriptor("a")],
            [_joined("a")],
            analysis_cohort="test",
            analysis_family="Test",
            analysis_state="baseline",
        )


def test_provenance_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="provenance mismatch"):
        build_cohort_analysis_rows(
            [_descriptor("a")],
            [_joined("a", model_name="Different")],
            analysis_cohort="test",
            analysis_family="Test",
            analysis_state="baseline",
        )


def test_partial_descriptor_and_energy_error_are_retained() -> None:
    rows = build_cohort_analysis_rows(
        [_descriptor("a", descriptor_v1_status="partial")],
        [_joined("a", energy_status="error", energy_error_code="model_output_error")],
        analysis_cohort="test",
        analysis_family="Test",
        analysis_state="refined",
    )

    assert len(rows) == 1
    assert rows[0]["descriptor_v1_status"] == "partial"
    assert rows[0]["energy_status"] == "error"
    assert rows[0]["energy_error_code"] == "model_output_error"
    assert rows[0]["magnetism_status"] == "ok"


def test_run_rejects_uid_overlap_across_cohorts(tmp_path) -> None:
    d1 = tmp_path / "d1.csv"
    j1 = tmp_path / "j1.csv"
    d2 = tmp_path / "d2.csv"
    j2 = tmp_path / "j2.csv"
    out = tmp_path / "out.csv"

    _write_csv(d1, [_descriptor("shared")])
    _write_csv(j1, [_joined("shared")])
    _write_csv(d2, [_descriptor("shared")])
    _write_csv(j2, [_joined("shared")])

    specs = [
        AnalysisCohortSpec("c1", "F1", "baseline", d1, j1),
        AnalysisCohortSpec("c2", "F2", "fine_tuned", d2, j2),
    ]

    with pytest.raises(ValueError, match="overlap across cohorts"):
        run_unified_analysis(cohorts=specs, output_path=out)


def test_mixed_baseline_resolves_family_from_model_name() -> None:
    models = [
        ("mg", "MatterGen", "mattergen"),
        ("cd", "Con-CDVAE", "concdvae"),
        ("cf", "CrystalFormer", "crystalformer"),
        ("cl", "CrystaLLM", "crystalllm"),
    ]
    descriptors = [
        _descriptor(uid, model_name=model_name, model_short=model_short)
        for uid, model_name, model_short in models
    ]
    joined = [
        _joined(uid, model_name=model_name, model_short=model_short)
        for uid, model_name, model_short in reversed(models)
    ]

    rows = build_cohort_analysis_rows(
        descriptors,
        joined,
        analysis_cohort="baseline",
        analysis_family=None,
        analysis_state="baseline",
    )

    assert [row["sample_uid"] for row in rows] == ["mg", "cd", "cf", "cl"]
    assert [row["analysis_family"] for row in rows] == [
        "MatterGen",
        "Con-CDVAE",
        "CrystalFormer",
        "CrystaLLM",
    ]
