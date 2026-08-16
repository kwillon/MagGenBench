from __future__ import annotations

import csv
from pathlib import Path

import pytest

from mvpipeline.analysis.cohorts import ProductionAnalysisCohort
from mvpipeline.analysis.unified import UnifiedAnalysisReport
from mvpipeline.reproduction import analysis_v1
from mvpipeline.reproduction.analysis_v1 import (
    MissingArtifactError,
    ProductionInvariants,
    ReproductionError,
    parse_sha256_manifest,
    reproduce_analysis_v1,
    resolve_repository_artifact,
    sha256_file,
    validate_analysis_v1_rows,
)


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def csv_text(rows: list[dict[str, str]]) -> str:
    from io import StringIO

    handle = StringIO()
    writer = csv.DictWriter(
        handle,
        fieldnames=list(rows[0]),
        lineterminator="\r\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()


def write_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    return write_text(path, csv_text(rows))


def digest_text(text: str) -> str:
    return analysis_v1.hashlib.sha256(text.encode("utf-8")).hexdigest()


def manifest_line(digest: str, path: str) -> str:
    return f"{digest}  {path}\n"


def tiny_cohorts() -> tuple[ProductionAnalysisCohort, ...]:
    return (
        ProductionAnalysisCohort(
            analysis_cohort="baseline_master",
            analysis_family=None,
            analysis_state="baseline",
            descriptor_path=Path("inputs/baseline_descriptors.csv"),
            joined_path=None,
        ),
        ProductionAnalysisCohort(
            analysis_cohort="mattergen_finetuned",
            analysis_family="MatterGen",
            analysis_state="fine_tuned",
            descriptor_path=Path("inputs/mattergen_descriptors.csv"),
            joined_path=Path("inputs/mattergen_joined.csv"),
        ),
    )


def tiny_rows(**overrides: str) -> list[dict[str, str]]:
    rows = [
        {
            "sample_uid": "b1",
            "structure_id": "b1",
            "analysis_cohort": "baseline_master",
            "analysis_family": "MatterGen",
            "analysis_state": "baseline",
            "descriptor_v1_status": "ok",
            "energy_status": "ok",
            "magnetism_status": "ok",
        },
        {
            "sample_uid": "m1",
            "structure_id": "m1",
            "analysis_cohort": "mattergen_finetuned",
            "analysis_family": "MatterGen",
            "analysis_state": "fine_tuned",
            "descriptor_v1_status": "ok",
            "energy_status": "ok",
            "magnetism_status": "ok",
        },
    ]
    if overrides:
        rows[-1].update(overrides)
    return rows


def tiny_invariants(rows: list[dict[str, str]]) -> ProductionInvariants:
    return ProductionInvariants(
        row_count=len(rows),
        column_count=len(rows[0]),
        cohort_counts={
            "baseline_master": 1,
            "mattergen_finetuned": 1,
        },
        descriptor_status_counts={"ok": 2},
        energy_status_counts={"ok": 2},
        magnetism_status_counts={"ok": 2},
    )


def write_tiny_inputs(
    repo_root: Path,
    *,
    artifact_root: Path | None = None,
    baseline_text: str = "baseline\n",
    output_digest: str | None = None,
    omit_repo_mattergen_joined: bool = False,
) -> tuple[Path, str]:
    inputs = {
        "inputs/baseline_descriptors.csv": "baseline descriptors\n",
        "inputs/mattergen_descriptors.csv": "mattergen descriptors\n",
        "inputs/mattergen_joined.csv": "mattergen joined\n",
    }
    for rel, text in inputs.items():
        if rel == "inputs/mattergen_joined.csv" and omit_repo_mattergen_joined:
            continue
        write_text(repo_root / rel, text)

    if artifact_root is not None:
        write_text(
            artifact_root / "inputs/mattergen_joined.csv",
            inputs["inputs/mattergen_joined.csv"],
        )

    baseline = write_text(repo_root / "artifacts/baseline_joined.csv", baseline_text)
    rows = tiny_rows()
    expected_output_digest = output_digest or digest_text(csv_text(rows))

    manifest = repo_root / analysis_v1.ANALYSIS_V1_MANIFEST_RELATIVE_PATH
    write_text(
        manifest,
        "".join(
            [
                manifest_line(
                    expected_output_digest,
                    "runs/analysis_v1/unified_analysis_v1.csv",
                ),
                manifest_line(
                    digest_text(inputs["inputs/baseline_descriptors.csv"]),
                    "inputs/baseline_descriptors.csv",
                ),
                manifest_line(
                    digest_text(inputs["inputs/mattergen_descriptors.csv"]),
                    "inputs/mattergen_descriptors.csv",
                ),
                manifest_line(
                    digest_text(inputs["inputs/mattergen_joined.csv"]),
                    "inputs/mattergen_joined.csv",
                ),
                manifest_line(digest_text(baseline_text), "/historic/baseline.csv"),
            ]
        ),
    )
    return baseline, expected_output_digest


def install_fake_unified_builder(monkeypatch, rows: list[dict[str, str]]) -> None:
    def fake_run_unified_analysis(*, cohorts, output_path):
        assert [spec.analysis_cohort for spec in cohorts] == [
            "baseline_master",
            "mattergen_finetuned",
        ]
        output = write_csv(Path(output_path), rows)
        return UnifiedAnalysisReport(
            cohort_count=len(cohorts),
            input_descriptor_rows=len(rows),
            input_joined_rows=len(rows),
            output_rows=len(rows),
            output_path=output,
        )

    monkeypatch.setattr(
        analysis_v1,
        "run_unified_analysis",
        fake_run_unified_analysis,
    )


def test_checksum_manifest_parses_real_supported_syntax(tmp_path) -> None:
    digest = "a" * 64
    manifest = write_text(
        tmp_path / "manifest.txt",
        manifest_line(digest, "runs/analysis_v1/unified_analysis_v1.csv"),
    )

    assert parse_sha256_manifest(manifest)[0].digest == digest
    assert (
        parse_sha256_manifest(manifest)[0].artifact_path
        == "runs/analysis_v1/unified_analysis_v1.csv"
    )


def test_current_analysis_v1_manifest_contract_is_parsed() -> None:
    root = Path(__file__).resolve().parents[1]
    entries = parse_sha256_manifest(
        root / analysis_v1.ANALYSIS_V1_MANIFEST_RELATIVE_PATH
    )

    assert len(entries) == 11
    assert entries[0].artifact_path == "runs/analysis_v1/unified_analysis_v1.csv"
    assert (
        analysis_v1.unified_output_manifest_entry(entries).digest
        == "a559a092755a91ea2c9035a08a61a41b8279a81b8dbe2ba52cb888cb17b4cb6c"
    )
    assert (
        analysis_v1.historical_baseline_manifest_entry(entries).artifact_path
        == "/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench/outputs/full/master_structures_validated_with_energy_magnetism.csv"
    )


def test_checksum_manifest_rejects_unsupported_syntax(tmp_path) -> None:
    manifest = write_text(tmp_path / "manifest.txt", "abc path.csv\n")

    with pytest.raises(ReproductionError, match="Invalid sha256 manifest line"):
        parse_sha256_manifest(manifest)


def test_correct_checksum_passes(tmp_path) -> None:
    path = write_text(tmp_path / "artifact.csv", "hello\n")

    analysis_v1.require_sha256(
        path,
        expected=sha256_file(path),
        label="artifact.csv",
    )


def test_checksum_mismatch_fails_loudly(tmp_path) -> None:
    path = write_text(tmp_path / "artifact.csv", "hello\n")

    with pytest.raises(ReproductionError, match="SHA256 mismatch"):
        analysis_v1.require_sha256(path, expected="0" * 64, label="artifact.csv")


def test_missing_artifact_fails_clearly(tmp_path) -> None:
    with pytest.raises(MissingArtifactError, match="Missing required artifact"):
        resolve_repository_artifact(
            Path("missing.csv"),
            repo_root=tmp_path,
            artifact_root=None,
        )


def test_repo_root_artifact_wins_when_present(tmp_path) -> None:
    repo_file = write_text(tmp_path / "x.csv", "repo\n")
    artifact_root = tmp_path / "artifacts"
    write_text(artifact_root / "x.csv", "artifact\n")

    assert (
        resolve_repository_artifact(
            Path("x.csv"),
            repo_root=tmp_path,
            artifact_root=artifact_root,
        )
        == repo_file
    )


def test_artifact_root_fallback_works(tmp_path) -> None:
    artifact_file = write_text(tmp_path / "artifacts/x.csv", "artifact\n")

    assert (
        resolve_repository_artifact(
            Path("x.csv"),
            repo_root=tmp_path,
            artifact_root=tmp_path / "artifacts",
        )
        == artifact_file
    )


def test_baseline_joined_replaces_historical_absolute_identity(
    tmp_path,
) -> None:
    baseline, _ = write_tiny_inputs(tmp_path)
    entries = parse_sha256_manifest(
        tmp_path / analysis_v1.ANALYSIS_V1_MANIFEST_RELATIVE_PATH
    )

    specs = analysis_v1.resolve_analysis_v1_inputs(
        repo_root=tmp_path,
        artifact_root=None,
        baseline_joined=baseline,
        manifest_entries=entries,
        cohorts=tiny_cohorts(),
    )

    assert specs[0].joined_path == baseline
    assert specs[1].joined_path == tmp_path / "inputs/mattergen_joined.csv"


def test_baseline_joined_must_match_historical_digest(tmp_path) -> None:
    baseline, _ = write_tiny_inputs(tmp_path)
    baseline.write_text("changed\n", encoding="utf-8")
    entries = parse_sha256_manifest(
        tmp_path / analysis_v1.ANALYSIS_V1_MANIFEST_RELATIVE_PATH
    )

    with pytest.raises(ReproductionError, match="SHA256 mismatch"):
        analysis_v1.resolve_analysis_v1_inputs(
            repo_root=tmp_path,
            artifact_root=None,
            baseline_joined=baseline,
            manifest_entries=entries,
            cohorts=tiny_cohorts(),
        )


def test_reproduction_writes_only_requested_output_dir(tmp_path, monkeypatch) -> None:
    rows = tiny_rows()
    baseline, expected_digest = write_tiny_inputs(tmp_path)
    install_fake_unified_builder(monkeypatch, rows)

    result = reproduce_analysis_v1(
        repo_root=tmp_path,
        baseline_joined=baseline,
        output_dir=tmp_path / "out",
        invariants=tiny_invariants(rows),
        cohorts=tiny_cohorts(),
    )

    assert result.output_path == tmp_path / "out/unified_analysis_v1.csv"
    assert result.sha256 == expected_digest
    assert not (tmp_path / "runs/analysis_v1/unified_analysis_v1.csv").exists()


def test_existing_output_fails_without_force(tmp_path) -> None:
    baseline, _ = write_tiny_inputs(tmp_path)
    write_text(tmp_path / "out/unified_analysis_v1.csv", "existing\n")

    with pytest.raises(ReproductionError, match="Output already exists"):
        reproduce_analysis_v1(
            repo_root=tmp_path,
            baseline_joined=baseline,
            output_dir=tmp_path / "out",
            invariants=tiny_invariants(tiny_rows()),
            cohorts=tiny_cohorts(),
        )


def test_force_replaces_only_target_csv(tmp_path, monkeypatch) -> None:
    rows = tiny_rows()
    baseline, _ = write_tiny_inputs(tmp_path)
    write_text(tmp_path / "out/unified_analysis_v1.csv", "existing\n")
    keep = write_text(tmp_path / "out/keep.txt", "keep\n")
    install_fake_unified_builder(monkeypatch, rows)

    reproduce_analysis_v1(
        repo_root=tmp_path,
        baseline_joined=baseline,
        output_dir=tmp_path / "out",
        force=True,
        invariants=tiny_invariants(rows),
        cohorts=tiny_cohorts(),
    )

    assert keep.read_text(encoding="utf-8") == "keep\n"


def test_expected_production_invariants_are_available() -> None:
    assert analysis_v1.PRODUCTION_INVARIANTS.row_count == 10684
    assert analysis_v1.PRODUCTION_INVARIANTS.column_count == 124
    assert dict(analysis_v1.PRODUCTION_INVARIANTS.cohort_counts) == {
        "baseline_master": 4702,
        "mattergen_finetuned": 1376,
        "concdvae_finetuned": 1299,
        "crysjepa_base": 1764,
        "crysjepa_refined": 1543,
    }


def test_row_count_mismatch_fails() -> None:
    rows = tiny_rows()
    invariants = tiny_invariants(rows)

    with pytest.raises(ReproductionError, match="Expected 2 rows"):
        validate_analysis_v1_rows(
            rows[:1],
            invariants=invariants,
            cohorts=tiny_cohorts(),
        )


def test_column_count_mismatch_fails() -> None:
    rows = tiny_rows()
    invariants = ProductionInvariants(
        **{
            **tiny_invariants(rows).__dict__,
            "column_count": 99,
        }
    )

    with pytest.raises(ReproductionError, match="Expected 99 columns"):
        validate_analysis_v1_rows(
            rows,
            invariants=invariants,
            cohorts=tiny_cohorts(),
        )


def test_duplicate_sample_uid_fails() -> None:
    rows = tiny_rows()
    rows[1]["sample_uid"] = "b1"
    rows[1]["structure_id"] = "b1"

    with pytest.raises(ReproductionError, match="Duplicate sample_uid"):
        validate_analysis_v1_rows(
            rows,
            invariants=tiny_invariants(tiny_rows()),
            cohorts=tiny_cohorts(),
        )


def test_sample_uid_structure_id_mismatch_fails() -> None:
    rows = tiny_rows(structure_id="different")

    with pytest.raises(ReproductionError, match="sample_uid/structure_id mismatch"):
        validate_analysis_v1_rows(
            rows,
            invariants=tiny_invariants(tiny_rows()),
            cohorts=tiny_cohorts(),
        )


def test_status_count_mismatch_fails() -> None:
    rows = tiny_rows(energy_status="error")

    with pytest.raises(ReproductionError, match="energy_status counts differ"):
        validate_analysis_v1_rows(
            rows,
            invariants=tiny_invariants(tiny_rows()),
            cohorts=tiny_cohorts(),
        )


def test_analysis_family_state_contract_is_checked() -> None:
    rows = tiny_rows(analysis_family="Con-CDVAE")

    with pytest.raises(ReproductionError, match="Unexpected analysis_family"):
        validate_analysis_v1_rows(
            rows,
            invariants=tiny_invariants(tiny_rows()),
            cohorts=tiny_cohorts(),
        )


def test_output_sha256_mismatch_fails(tmp_path, monkeypatch) -> None:
    rows = tiny_rows()
    baseline, _ = write_tiny_inputs(tmp_path, output_digest="0" * 64)
    install_fake_unified_builder(monkeypatch, rows)

    with pytest.raises(ReproductionError, match="SHA256 mismatch"):
        reproduce_analysis_v1(
            repo_root=tmp_path,
            baseline_joined=baseline,
            output_dir=tmp_path / "out",
            invariants=tiny_invariants(rows),
            cohorts=tiny_cohorts(),
        )


def test_reproduction_does_not_call_other_pipeline_stages(
    tmp_path,
    monkeypatch,
) -> None:
    rows = tiny_rows()
    baseline, _ = write_tiny_inputs(tmp_path)
    install_fake_unified_builder(monkeypatch, rows)

    forbidden_names = [
        "run_validation",
        "run_descriptors",
        "run_annotations",
        "run_chgnet",
        "run_dxmag",
    ]
    for name in forbidden_names:
        assert not hasattr(analysis_v1, name)

    reproduce_analysis_v1(
        repo_root=tmp_path,
        baseline_joined=baseline,
        output_dir=tmp_path / "out",
        invariants=tiny_invariants(rows),
        cohorts=tiny_cohorts(),
    )
