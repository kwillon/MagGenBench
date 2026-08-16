from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ..io.stage_tables import write_stage_csv_atomic
from .config import DescriptorRuntimeConfig, load_descriptor_runtime_config
from .extractor import extract_descriptor_v1
from .records import DESCRIPTOR_RECORD_FIELDS, descriptor_result_to_record
from .schema import DescriptorInput, DescriptorResult, DescriptorStatus


StructureLoader = Callable[[str], Any]


@dataclass(frozen=True)
class DescriptorBatchReport:
    input_count: int
    output_count: int
    output_path: Path
    fieldnames: list[str]


def default_structure_loader(cif_path: str) -> Any:
    from pymatgen.core import Structure

    return Structure.from_file(cif_path)


def read_descriptor_manifest(
    path: str | Path,
) -> list[dict[str, str]]:
    with Path(path).open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        return list(csv.DictReader(handle))


def _required_text(
    row: Mapping[str, str],
    field: str,
) -> str:
    value = str(row.get(field) or "").strip()
    if not value:
        raise ValueError(f"{field} must be non-empty")
    return value


def _validate_manifest_rows(
    rows: Sequence[Mapping[str, str]],
) -> None:
    seen_sample_uids: set[str] = set()
    seen_structure_ids: set[str] = set()

    for row in rows:
        sample_uid = _required_text(row, "sample_uid")
        structure_id = _required_text(row, "structure_id")
        _required_text(row, "cif_path")

        if sample_uid in seen_sample_uids:
            raise ValueError(f"Duplicate sample_uid: {sample_uid}")
        if structure_id in seen_structure_ids:
            raise ValueError(
                f"Duplicate structure_id: {structure_id}"
            )
        if sample_uid != structure_id:
            raise ValueError(
                "Descriptor v1 benchmark manifest requires "
                f"sample_uid == structure_id: "
                f"{sample_uid!r} != {structure_id!r}"
            )

        seen_sample_uids.add(sample_uid)
        seen_structure_ids.add(structure_id)


def _descriptor_input(
    row: Mapping[str, str],
    structure: Any,
) -> DescriptorInput:
    return DescriptorInput(
        sample_uid=_required_text(row, "sample_uid"),
        structure_id=_required_text(row, "structure_id"),
        structure=structure,
        model_name=str(row.get("model_name") or ""),
        model_short=str(row.get("model_short") or ""),
        run_uid=str(row.get("run_uid") or ""),
        source_sample_id=str(
            row.get("source_sample_id") or ""
        ),
        cif_path=_required_text(row, "cif_path"),
    )


def _parse_error_result(
    row: Mapping[str, str],
    exc: Exception,
) -> DescriptorResult:
    return DescriptorResult(
        sample_uid=_required_text(row, "sample_uid"),
        structure_id=_required_text(row, "structure_id"),
        status=DescriptorStatus.ERROR,
        model_name=str(row.get("model_name") or ""),
        model_short=str(row.get("model_short") or ""),
        run_uid=str(row.get("run_uid") or ""),
        source_sample_id=str(
            row.get("source_sample_id") or ""
        ),
        cif_path=_required_text(row, "cif_path"),
        error_code="cif_parse_error",
        error_message=str(exc),
        values={},
    )


def extract_descriptor_rows(
    rows: Sequence[Mapping[str, str]],
    *,
    config: DescriptorRuntimeConfig,
    structure_loader: StructureLoader = default_structure_loader,
) -> list[dict[str, Any]]:
    input_rows = list(rows)
    _validate_manifest_rows(input_rows)

    output: list[dict[str, Any]] = []

    for row in input_rows:
        cif_path = _required_text(row, "cif_path")

        try:
            structure = structure_loader(cif_path)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            result = _parse_error_result(row, exc)
            output.append(descriptor_result_to_record(result))
            continue

        descriptor_input = _descriptor_input(row, structure)
        result = extract_descriptor_v1(
            descriptor_input,
            magnetic_screening_elements=(
                config.magnetic_screening_elements
            ),
            symprec=config.symprec,
            angle_tolerance=config.angle_tolerance,
            local_geometry_cutoff=(
                config.local_geometry_cutoff
            ),
            local_geometry_tolerance=(
                config.local_geometry_tolerance
            ),
            local_geometry_get_all_sites=(
                config.local_geometry_get_all_sites
            ),
        )
        output.append(descriptor_result_to_record(result))

    if len(output) != len(input_rows):
        raise RuntimeError(
            "Descriptor v1 row-preservation invariant failed: "
            f"{len(input_rows)} input rows, "
            f"{len(output)} output rows"
        )

    return output


def run_descriptor_batch(
    *,
    input_path: str | Path,
    output_path: str | Path,
    descriptor_config_path: str | Path = "config/descriptors.yaml",
    project_root: str | Path | None = None,
    structure_loader: StructureLoader = default_structure_loader,
) -> DescriptorBatchReport:
    rows = read_descriptor_manifest(input_path)
    config = load_descriptor_runtime_config(
        descriptor_config_path,
        project_root=project_root,
    )

    output = extract_descriptor_rows(
        rows,
        config=config,
        structure_loader=structure_loader,
    )

    written_path = write_stage_csv_atomic(
        output_path,
        output,
        DESCRIPTOR_RECORD_FIELDS,
    )

    return DescriptorBatchReport(
        input_count=len(rows),
        output_count=len(output),
        output_path=written_path,
        fieldnames=list(DESCRIPTOR_RECORD_FIELDS),
    )
