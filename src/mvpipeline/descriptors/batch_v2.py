from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ..io.stage_tables import write_stage_csv_atomic
from .config_v2 import (
    MagneticDescriptorV2RuntimeConfig,
    load_magnetic_descriptor_v2_runtime_config,
)
from .extractor_v2 import extract_magnetic_descriptor_v2
from .schema_v2 import (
    MAGNETIC_DESCRIPTOR_V2_RECORD_FIELDS,
    DescriptorV2Status,
    MagneticDescriptorInput,
    MagneticDescriptorResult,
    magnetic_descriptor_v2_result_to_record,
)


StructureLoader = Callable[[str], Any]


@dataclass(frozen=True)
class MagneticDescriptorV2BatchReport:
    input_count: int
    output_count: int
    output_path: Path
    fieldnames: list[str]


def default_structure_loader(cif_path: str) -> Any:
    from pymatgen.core import Structure

    return Structure.from_file(cif_path)


def read_descriptor_v2_input(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _required_text(row: Mapping[str, str], field: str) -> str:
    value = str(row.get(field) or "").strip()
    if not value:
        raise ValueError(f"{field} must be non-empty")
    return value


def _validate_input_rows(
    rows: Sequence[Mapping[str, str]],
    *,
    require_unique_sample_uid: bool,
) -> None:
    seen_sample_uids: set[str] = set()
    seen_structure_ids: set[str] = set()

    for row in rows:
        sample_uid = _required_text(row, "sample_uid")
        structure_id = _required_text(row, "structure_id")
        _required_text(row, "cif_path")

        if require_unique_sample_uid and sample_uid in seen_sample_uids:
            raise ValueError(f"Duplicate sample_uid: {sample_uid}")
        if structure_id in seen_structure_ids:
            raise ValueError(f"Duplicate structure_id: {structure_id}")
        if sample_uid != structure_id:
            raise ValueError(
                "Descriptor v2 input requires sample_uid == structure_id: "
                f"{sample_uid!r} != {structure_id!r}"
            )

        seen_sample_uids.add(sample_uid)
        seen_structure_ids.add(structure_id)


def _descriptor_input(
    row: Mapping[str, str],
    structure: Any,
) -> MagneticDescriptorInput:
    return MagneticDescriptorInput(
        sample_uid=_required_text(row, "sample_uid"),
        structure_id=_required_text(row, "structure_id"),
        structure=structure,
        analysis_cohort=str(row.get("analysis_cohort") or ""),
        analysis_family=str(row.get("analysis_family") or ""),
        analysis_state=str(row.get("analysis_state") or ""),
        model_name=str(row.get("model_name") or ""),
        model_short=str(row.get("model_short") or ""),
        formula_reduced=str(row.get("formula_reduced") or ""),
        formula_full_canonical=str(row.get("formula_full_canonical") or ""),
        cif_path=_required_text(row, "cif_path"),
    )


def _parse_error_result(
    row: Mapping[str, str],
    exc: Exception,
) -> MagneticDescriptorResult:
    return MagneticDescriptorResult(
        sample_uid=_required_text(row, "sample_uid"),
        structure_id=_required_text(row, "structure_id"),
        status=DescriptorV2Status.ERROR,
        analysis_cohort=str(row.get("analysis_cohort") or ""),
        analysis_family=str(row.get("analysis_family") or ""),
        analysis_state=str(row.get("analysis_state") or ""),
        model_name=str(row.get("model_name") or ""),
        model_short=str(row.get("model_short") or ""),
        formula_reduced=str(row.get("formula_reduced") or ""),
        formula_full_canonical=str(row.get("formula_full_canonical") or ""),
        cif_path=_required_text(row, "cif_path"),
        error_code="cif_parse_error",
        error_message=str(exc),
        values={
            "magnetic_geometry_status": "not_computed",
            "magnetic_symmetry_status": "not_computed",
        },
    )


def _resolve_cif_path(cif_path: str, repo_root: Path) -> str:
    path = Path(cif_path)
    if not path.is_absolute():
        path = repo_root / path
    return str(path)


def extract_magnetic_descriptor_v2_rows(
    rows: Sequence[Mapping[str, str]],
    *,
    config: MagneticDescriptorV2RuntimeConfig,
    repo_root: str | Path = ".",
    structure_loader: StructureLoader = default_structure_loader,
) -> list[dict[str, Any]]:
    input_rows = list(rows)
    _validate_input_rows(
        input_rows,
        require_unique_sample_uid=config.require_unique_sample_uid,
    )

    root = Path(repo_root).resolve()
    output: list[dict[str, Any]] = []

    for row in input_rows:
        cif_path = _required_text(row, "cif_path")
        resolved_cif_path = _resolve_cif_path(cif_path, root)

        try:
            structure = structure_loader(resolved_cif_path)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            result = _parse_error_result(row, exc)
            output.append(magnetic_descriptor_v2_result_to_record(result))
            continue

        descriptor_input = _descriptor_input(row, structure)
        result = extract_magnetic_descriptor_v2(
            descriptor_input,
            magnetic_elements=config.magnetic_elements,
            configured_magnetic_elements=config.configured_magnetic_elements,
            symprec=config.symprec,
            angle_tolerance=config.angle_tolerance,
            local_geometry_cutoff=config.local_geometry_cutoff,
            local_geometry_tolerance=config.local_geometry_tolerance,
            local_geometry_get_all_sites=config.local_geometry_get_all_sites,
        )
        output.append(magnetic_descriptor_v2_result_to_record(result))

    if len(output) != len(input_rows):
        raise RuntimeError(
            "Descriptor v2 row-preservation invariant failed: "
            f"{len(input_rows)} input rows, {len(output)} output rows"
        )

    return output


def run_magnetic_descriptor_v2_batch(
    *,
    input_path: str | Path,
    output_path: str | Path,
    descriptor_config_path: str | Path = "config/descriptors_v2_magnetic.yaml",
    project_root: str | Path | None = None,
    limit: int | None = None,
    structure_loader: StructureLoader = default_structure_loader,
) -> MagneticDescriptorV2BatchReport:
    root = Path(project_root or ".").resolve()
    rows = read_descriptor_v2_input(input_path)
    if limit is not None:
        rows = rows[:limit]

    config = load_magnetic_descriptor_v2_runtime_config(
        descriptor_config_path,
        project_root=root,
    )

    output = extract_magnetic_descriptor_v2_rows(
        rows,
        config=config,
        repo_root=root,
        structure_loader=structure_loader,
    )

    written_path = write_stage_csv_atomic(
        output_path,
        output,
        MAGNETIC_DESCRIPTOR_V2_RECORD_FIELDS,
    )

    return MagneticDescriptorV2BatchReport(
        input_count=len(rows),
        output_count=len(output),
        output_path=written_path,
        fieldnames=list(MAGNETIC_DESCRIPTOR_V2_RECORD_FIELDS),
    )
