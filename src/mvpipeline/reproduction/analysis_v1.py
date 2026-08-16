from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from mvpipeline.analysis.cohorts import (
    CORE_BASELINE_FAMILIES,
    EXPECTED_PRODUCTION_COHORT_COUNTS,
    EXPECTED_PRODUCTION_DESCRIPTOR_STATUS_COUNTS,
    EXPECTED_PRODUCTION_ENERGY_STATUS_COUNTS,
    EXPECTED_PRODUCTION_MAGNETISM_STATUS_COUNTS,
    EXPECTED_PRODUCTION_ROWS,
    PRODUCTION_ANALYSIS_COHORTS,
    ProductionAnalysisCohort,
)
from mvpipeline.analysis.unified import (
    UNIFIED_ANALYSIS_FIELDS,
    AnalysisCohortSpec,
    run_unified_analysis,
)
from mvpipeline.io.stage_tables import read_stage_csv


ANALYSIS_V1_MANIFEST_RELATIVE_PATH = Path(
    "runs/analysis_v1/final_sha256.txt"
)
UNIFIED_ANALYSIS_V1_RELATIVE_PATH = Path(
    "runs/analysis_v1/unified_analysis_v1.csv"
)
DEFAULT_ANALYSIS_V1_OUTPUT_DIR = Path("reproduced/analysis_v1")
UNIFIED_ANALYSIS_V1_FILENAME = "unified_analysis_v1.csv"
HEX_DIGITS = frozenset("0123456789abcdef")


class ReproductionError(RuntimeError):
    """Raised when a frozen reproduction contract is not satisfied."""


class MissingArtifactError(ReproductionError):
    """Raised when a required reproduction artifact cannot be resolved."""


@dataclass(frozen=True)
class Sha256ManifestEntry:
    digest: str
    artifact_path: str

    @property
    def logical_path(self) -> Path:
        return Path(self.artifact_path)


@dataclass(frozen=True)
class ProductionInvariants:
    row_count: int
    column_count: int
    cohort_counts: Mapping[str, int]
    descriptor_status_counts: Mapping[str, int]
    energy_status_counts: Mapping[str, int]
    magnetism_status_counts: Mapping[str, int]


@dataclass(frozen=True)
class ReproductionResult:
    output_path: Path
    row_count: int
    column_count: int
    sha256: str
    figure_output_dir: Path
    figure_files: tuple[Path, ...]


PRODUCTION_INVARIANTS = ProductionInvariants(
    row_count=EXPECTED_PRODUCTION_ROWS,
    column_count=len(UNIFIED_ANALYSIS_FIELDS),
    cohort_counts=EXPECTED_PRODUCTION_COHORT_COUNTS,
    descriptor_status_counts=EXPECTED_PRODUCTION_DESCRIPTOR_STATUS_COUNTS,
    energy_status_counts=EXPECTED_PRODUCTION_ENERGY_STATUS_COUNTS,
    magnetism_status_counts=EXPECTED_PRODUCTION_MAGNETISM_STATUS_COUNTS,
)


def parse_sha256_manifest(path: str | Path) -> list[Sha256ManifestEntry]:
    entries: list[Sha256ManifestEntry] = []
    manifest_path = Path(path)

    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.rstrip("\n")
            if line.endswith("\r"):
                line = line[:-1]
            if not line:
                continue
            if len(line) < 67 or line[64:66] != "  ":
                raise ReproductionError(
                    f"Invalid sha256 manifest line {line_number}: {raw_line!r}"
                )
            digest = line[:64]
            artifact_path = line[66:]
            if (
                len(digest) != 64
                or any(char not in HEX_DIGITS for char in digest)
                or not artifact_path
            ):
                raise ReproductionError(
                    f"Invalid sha256 manifest line {line_number}: {raw_line!r}"
                )
            entries.append(
                Sha256ManifestEntry(
                    digest=digest,
                    artifact_path=artifact_path,
                )
            )

    if not entries:
        raise ReproductionError(f"Empty sha256 manifest: {manifest_path}")
    return entries


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha256(path: str | Path, *, expected: str, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise ReproductionError(
            f"SHA256 mismatch for {label}: expected={expected}, actual={actual}"
        )


def _is_historical_absolute_path(path: str) -> bool:
    return path.startswith("/") or (len(path) >= 3 and path[1:3] == ":\\")


def _manifest_by_path(
    entries: Sequence[Sha256ManifestEntry],
) -> dict[str, Sha256ManifestEntry]:
    by_path: dict[str, Sha256ManifestEntry] = {}
    for entry in entries:
        if entry.artifact_path in by_path:
            raise ReproductionError(
                f"Duplicate path in sha256 manifest: {entry.artifact_path}"
            )
        by_path[entry.artifact_path] = entry
    return by_path


def _manifest_entry_for(
    manifest: Mapping[str, Sha256ManifestEntry],
    logical_path: Path,
) -> Sha256ManifestEntry:
    key = logical_path.as_posix()
    try:
        return manifest[key]
    except KeyError as exc:
        raise ReproductionError(
            f"Missing sha256 manifest entry for required artifact: {key}"
        ) from exc


def unified_output_manifest_entry(
    entries: Sequence[Sha256ManifestEntry],
) -> Sha256ManifestEntry:
    manifest = _manifest_by_path(entries)
    return _manifest_entry_for(manifest, UNIFIED_ANALYSIS_V1_RELATIVE_PATH)


def historical_baseline_manifest_entry(
    entries: Sequence[Sha256ManifestEntry],
) -> Sha256ManifestEntry:
    candidates = [
        entry
        for entry in entries
        if _is_historical_absolute_path(entry.artifact_path)
    ]
    if len(candidates) != 1:
        raise ReproductionError(
            "Expected exactly one historical absolute baseline joined "
            f"artifact in sha256 manifest, found {len(candidates)}"
        )
    return candidates[0]


def resolve_repository_artifact(
    logical_path: Path,
    *,
    repo_root: Path,
    artifact_root: Path | None,
) -> Path:
    repo_path = repo_root / logical_path
    if repo_path.is_file():
        return repo_path

    if artifact_root is not None:
        artifact_path = artifact_root / logical_path
        if artifact_path.is_file():
            return artifact_path

    message = f"Missing required artifact: {logical_path.as_posix()}"
    if artifact_root is not None:
        message += (
            f" (checked {repo_path} and {artifact_root / logical_path})"
        )
    else:
        message += f" (checked {repo_path}; no --artifact-root supplied)"
    raise MissingArtifactError(message)


def resolve_analysis_v1_inputs(
    *,
    repo_root: Path,
    artifact_root: Path | None,
    baseline_joined: Path,
    manifest_entries: Sequence[Sha256ManifestEntry],
    cohorts: Sequence[ProductionAnalysisCohort] = PRODUCTION_ANALYSIS_COHORTS,
) -> list[AnalysisCohortSpec]:
    manifest = _manifest_by_path(manifest_entries)
    baseline_entry = historical_baseline_manifest_entry(manifest_entries)

    if not baseline_joined.is_file():
        raise MissingArtifactError(
            f"Missing supplied baseline joined artifact: {baseline_joined}"
        )
    require_sha256(
        baseline_joined,
        expected=baseline_entry.digest,
        label=baseline_entry.artifact_path,
    )

    specs: list[AnalysisCohortSpec] = []
    for cohort in cohorts:
        descriptor_entry = _manifest_entry_for(
            manifest,
            cohort.descriptor_path,
        )
        descriptor_path = resolve_repository_artifact(
            cohort.descriptor_path,
            repo_root=repo_root,
            artifact_root=artifact_root,
        )
        require_sha256(
            descriptor_path,
            expected=descriptor_entry.digest,
            label=cohort.descriptor_path.as_posix(),
        )

        if cohort.joined_path is None:
            joined_path = baseline_joined
        else:
            joined_entry = _manifest_entry_for(manifest, cohort.joined_path)
            joined_path = resolve_repository_artifact(
                cohort.joined_path,
                repo_root=repo_root,
                artifact_root=artifact_root,
            )
            require_sha256(
                joined_path,
                expected=joined_entry.digest,
                label=cohort.joined_path.as_posix(),
            )

        specs.append(
            AnalysisCohortSpec(
                analysis_cohort=cohort.analysis_cohort,
                analysis_family=cohort.analysis_family,
                analysis_state=cohort.analysis_state,
                descriptor_path=descriptor_path,
                joined_path=joined_path,
            )
        )

    return specs


def _require_counter(
    rows: Sequence[Mapping[str, str]],
    field: str,
    expected: Mapping[str, int],
) -> None:
    actual = dict(Counter(row.get(field, "") for row in rows))
    if actual != dict(expected):
        raise ReproductionError(
            f"{field} counts differ: expected={dict(expected)}, actual={actual}"
        )


def validate_analysis_v1_rows(
    rows: Sequence[Mapping[str, str]],
    *,
    invariants: ProductionInvariants = PRODUCTION_INVARIANTS,
    cohorts: Sequence[ProductionAnalysisCohort] = PRODUCTION_ANALYSIS_COHORTS,
) -> None:
    if len(rows) != invariants.row_count:
        raise ReproductionError(
            f"Expected {invariants.row_count} rows, got {len(rows)}"
        )
    if not rows:
        raise ReproductionError("Reproduced unified analysis is empty")
    if len(rows[0]) != invariants.column_count:
        raise ReproductionError(
            f"Expected {invariants.column_count} columns, got {len(rows[0])}"
        )

    sample_uids: set[str] = set()
    cohort_states = {
        cohort.analysis_cohort: cohort.analysis_state
        for cohort in cohorts
    }
    non_baseline_families = {
        cohort.analysis_cohort: cohort.analysis_family
        for cohort in cohorts
        if cohort.analysis_family is not None
    }

    for row in rows:
        sample_uid = (row.get("sample_uid") or "").strip()
        structure_id = (row.get("structure_id") or "").strip()
        if not sample_uid:
            raise ReproductionError("Found empty sample_uid")
        if sample_uid != structure_id:
            raise ReproductionError(
                f"sample_uid/structure_id mismatch: {sample_uid!r}"
            )
        if sample_uid in sample_uids:
            raise ReproductionError(f"Duplicate sample_uid: {sample_uid}")
        sample_uids.add(sample_uid)

        cohort = (row.get("analysis_cohort") or "").strip()
        family = (row.get("analysis_family") or "").strip()
        state = (row.get("analysis_state") or "").strip()
        expected_state = cohort_states.get(cohort)
        if expected_state is None:
            raise ReproductionError(f"Unknown analysis_cohort: {cohort!r}")
        if state != expected_state:
            raise ReproductionError(
                f"Unexpected analysis_state for {cohort!r}: "
                f"expected={expected_state!r}, actual={state!r}"
            )
        if cohort == "baseline_master":
            if family not in CORE_BASELINE_FAMILIES:
                raise ReproductionError(
                    f"Unexpected baseline analysis_family: {family!r}"
                )
        else:
            expected_family = non_baseline_families.get(cohort)
            if family != expected_family:
                raise ReproductionError(
                    f"Unexpected analysis_family for {cohort!r}: "
                    f"expected={expected_family!r}, actual={family!r}"
                )

    if len(sample_uids) != invariants.row_count:
        raise ReproductionError(
            f"Expected {invariants.row_count} unique sample_uid values, "
            f"got {len(sample_uids)}"
        )

    _require_counter(rows, "analysis_cohort", invariants.cohort_counts)
    _require_counter(
        rows,
        "descriptor_v1_status",
        invariants.descriptor_status_counts,
    )
    _require_counter(rows, "energy_status", invariants.energy_status_counts)
    _require_counter(
        rows,
        "magnetism_status",
        invariants.magnetism_status_counts,
    )


def reproduce_analysis_v1(
    *,
    repo_root: str | Path = Path("."),
    artifact_root: str | Path | None = None,
    baseline_joined: str | Path,
    output_dir: str | Path = DEFAULT_ANALYSIS_V1_OUTPUT_DIR,
    force: bool = False,
    invariants: ProductionInvariants = PRODUCTION_INVARIANTS,
    cohorts: Sequence[ProductionAnalysisCohort] = PRODUCTION_ANALYSIS_COHORTS,
) -> ReproductionResult:
    root = Path(repo_root)
    artifacts = None if artifact_root is None else Path(artifact_root)
    baseline_path = Path(baseline_joined)
    destination_dir = Path(output_dir)
    output_path = destination_dir / UNIFIED_ANALYSIS_V1_FILENAME
    figure_output_dir = destination_dir / "figures"

    if output_path.exists() and not force:
        raise ReproductionError(
            f"Output already exists: {output_path}; use --force to replace it"
        )

    manifest_path = root / ANALYSIS_V1_MANIFEST_RELATIVE_PATH
    manifest_entries = parse_sha256_manifest(manifest_path)
    expected_output = unified_output_manifest_entry(manifest_entries)
    specs = resolve_analysis_v1_inputs(
        repo_root=root,
        artifact_root=artifacts,
        baseline_joined=baseline_path,
        manifest_entries=manifest_entries,
        cohorts=cohorts,
    )

    if output_path.exists() and force:
        output_path.unlink()

    report = run_unified_analysis(cohorts=specs, output_path=output_path)
    rows = read_stage_csv(report.output_path)
    validate_analysis_v1_rows(
        rows,
        invariants=invariants,
        cohorts=cohorts,
    )

    digest = sha256_file(report.output_path)
    if digest != expected_output.digest:
        raise ReproductionError(
            "Reproduced unified Analysis v1 SHA256 mismatch: "
            f"expected={expected_output.digest}, actual={digest}"
        )

    from mvpipeline.analysis.figures_v1 import (
        generate_analysis_v1_figures,
        prepare_analysis_v1_figure_outputs,
    )

    try:
        prepare_analysis_v1_figure_outputs(
            figure_output_dir,
            force=force,
        )
    except RuntimeError as exc:
        raise ReproductionError(str(exc)) from exc

    try:
        figure_report = generate_analysis_v1_figures(
            input_csv=report.output_path,
            output_dir=figure_output_dir,
            force=False,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        raise ReproductionError(str(exc)) from exc

    return ReproductionResult(
        output_path=report.output_path,
        row_count=len(rows),
        column_count=len(rows[0]) if rows else 0,
        sha256=digest,
        figure_output_dir=figure_report.output_dir,
        figure_files=figure_report.output_files,
    )
