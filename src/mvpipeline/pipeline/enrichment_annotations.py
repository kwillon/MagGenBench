from __future__ import annotations

import csv
import json
import math
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from ..io.stage_tables import write_stage_csv_atomic
from ..magnetism.config import MagnetismConfig, load_magnetism_config


ANNOTATION_FIELDS = [
    "structure_id",
    "cif_load_status",
    "cif_warning_count",
    "cif_warnings",
    "n_sites",
    "composition_num_atoms",
    "volume_A3",
    "volume_per_site_A3",
    "volume_per_composition_atom_A3",
    "density_g_cm3",
    "crystal_system",
    "point_group_symbol",
    "space_group_number_recomputed",
    "space_group_symbol_recomputed",
    "descriptor_status",
    "descriptor_error_code",
    "descriptor_error_message",
    "descriptor_source",
    "contains_magnetic_element",
    "magnetic_elements",
    "magnetic_element_species_count",
    "magnetic_element_site_count",
    "contains_3d",
    "contains_4f",
    "nonmagnetic_by_composition_heuristic",
    "magnetic_screening_status",
    "magnetic_screening_reason",
    "compound_class_filter_status",
    "compound_class_filter_reason",
]

StructureLoader = Callable[[str], Any]
SymmetryAnalyzer = Callable[[Any], Mapping[str, Any]]


@dataclass(frozen=True)
class MagneticAnnotationConfig:
    transition_3d: frozenset[str] = frozenset()
    selected_4d_5d: frozenset[str] = frozenset()
    lanthanides: frozenset[str] = frozenset()

    @property
    def all_elements(self) -> frozenset[str]:
        return self.transition_3d | self.selected_4d_5d | self.lanthanides


@dataclass(frozen=True)
class CompoundClassRules:
    high_priority: frozenset[str] = frozenset()
    low_priority: frozenset[str] = frozenset()
    rejected: frozenset[str] = frozenset()
    unlisted_status: str = "accepted"


@dataclass(frozen=True)
class EnrichmentAnnotationConfig:
    magnetic: MagneticAnnotationConfig = MagneticAnnotationConfig()
    class_rules: CompoundClassRules = CompoundClassRules()
    symprec: float = 0.01


@dataclass(frozen=True)
class EnrichmentAnnotationReport:
    input_count: int
    output_count: int
    output_path: Optional[Path]
    fieldnames: list[str]


@dataclass(frozen=True)
class StructureLoadResult:
    structure: Any
    warnings: list[dict[str, str]]


class StructureLoadError(Exception):
    def __init__(self, original: Exception, warning_records: list[dict[str, str]]):
        super().__init__(str(original))
        self.original = original
        self.warning_records = warning_records


def enrichment_annotation_config_from_magnetism_config(
    config: MagnetismConfig,
    *,
    symprec: float = 0.01,
) -> EnrichmentAnnotationConfig:
    return EnrichmentAnnotationConfig(
        magnetic=MagneticAnnotationConfig(
            transition_3d=frozenset(config.magnetic_elements.transition_3d),
            selected_4d_5d=frozenset(config.magnetic_elements.selected_4d_5d),
            lanthanides=frozenset(config.magnetic_elements.lanthanides),
        ),
        class_rules=CompoundClassRules(
            high_priority=frozenset(
                cls.lower() for cls in config.screening_rules.high_priority_classes
            ),
            low_priority=frozenset(
                cls.lower() for cls in config.screening_rules.low_priority_classes
            ),
            rejected=frozenset(
                cls.lower() for cls in config.screening_rules.reject_classes
            ),
            unlisted_status="accepted",
        ),
        symprec=symprec,
    )


def load_enrichment_annotation_config(
    path: str | Path,
    *,
    symprec: float = 0.01,
) -> EnrichmentAnnotationConfig:
    return enrichment_annotation_config_from_magnetism_config(
        load_magnetism_config(path),
        symprec=symprec,
    )


def _finite_scalar(value: Any, field_name: str) -> float:
    scalar = float(value)
    if not math.isfinite(scalar):
        raise ValueError(f"{field_name} must be finite")
    return scalar


def _json_array(values: Iterable[str]) -> str:
    return json.dumps(sorted(values), ensure_ascii=False)


def _json_warning_records(records: Sequence[Mapping[str, str]]) -> str:
    return json.dumps(list(records), ensure_ascii=False)


def _warning_records(captured: Sequence[warnings.WarningMessage]) -> list[dict[str, str]]:
    return [
        {
            "category": warning.category.__name__,
            "message": str(warning.message),
        }
        for warning in captured
    ]


def _cif_load_annotations(
    records: Sequence[Mapping[str, str]],
    *,
    error: bool,
) -> dict[str, Any]:
    if error:
        status = "error"
    elif records:
        status = "ok_with_warnings"
    else:
        status = "ok"
    return {
        "cif_load_status": status,
        "cif_warning_count": len(records),
        "cif_warnings": _json_warning_records(records),
    }


def _load_structure_with_warning_capture(
    structure_loader: StructureLoader,
    cif_path: str,
) -> StructureLoadResult:
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        try:
            structure = structure_loader(cif_path)
        except Exception as exc:
            raise StructureLoadError(exc, _warning_records(captured)) from exc
        return StructureLoadResult(
            structure=structure,
            warnings=_warning_records(captured),
        )


def default_structure_loader(cif_path: str) -> Any:
    from pymatgen.core import Structure

    return Structure.from_file(cif_path)


def default_symmetry_analyzer(structure: Any, symprec: float = 0.01) -> Mapping[str, Any]:
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    analyzer = SpacegroupAnalyzer(structure, symprec=symprec)
    return {
        "crystal_system": analyzer.get_crystal_system(),
        "point_group_symbol": analyzer.get_point_group_symbol(),
        "space_group_number_recomputed": analyzer.get_space_group_number(),
        "space_group_symbol_recomputed": analyzer.get_space_group_symbol(),
    }


def read_manifest_csv(path: str | Path) -> tuple[list[dict[str, str]], list[str]]:
    with Path(path).open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def _composition_num_atoms(structure: Any) -> float:
    return _finite_scalar(structure.composition.num_atoms, "composition_num_atoms")


def _element_symbol(element: Any) -> str:
    return str(getattr(element, "symbol", element))


def _composition_elements(structure: Any) -> set[str]:
    composition = structure.composition
    if hasattr(composition, "elements"):
        return {_element_symbol(element) for element in composition.elements}
    if isinstance(composition, Mapping):
        return {str(element) for element in composition}
    if hasattr(composition, "as_dict"):
        return {str(element) for element in composition.as_dict()}
    raise ValueError("Cannot extract composition elements")


def _site_elements(site: Any) -> set[str]:
    if hasattr(site, "species"):
        species = site.species
        if hasattr(species, "items"):
            return {
                _element_symbol(element)
                for element, occupancy in species.items()
                if float(occupancy) > 0
            }
        if hasattr(species, "elements"):
            return {_element_symbol(element) for element in species.elements}
    if hasattr(site, "specie"):
        return {_element_symbol(site.specie)}
    if isinstance(site, Mapping):
        return {
            str(element) for element, occupancy in site.items() if float(occupancy) > 0
        }
    raise ValueError("Cannot extract site species")


def _iter_sites(structure: Any) -> list[Any]:
    return list(structure)


def compute_structural_annotations(
    structure: Any,
    *,
    symmetry_analyzer: Optional[SymmetryAnalyzer] = None,
    symprec: float = 0.01,
) -> dict[str, Any]:
    n_sites = len(structure)
    composition_atoms = _composition_num_atoms(structure)
    volume = _finite_scalar(structure.volume, "volume_A3")
    density = _finite_scalar(structure.density, "density_g_cm3")
    if n_sites <= 0:
        raise ValueError("n_sites must be positive")
    if composition_atoms <= 0:
        raise ValueError("composition_num_atoms must be positive")

    record: dict[str, Any] = {
        "n_sites": n_sites,
        "composition_num_atoms": composition_atoms,
        "volume_A3": volume,
        "volume_per_site_A3": volume / float(n_sites),
        "volume_per_composition_atom_A3": volume / composition_atoms,
        "density_g_cm3": density,
        "crystal_system": "",
        "point_group_symbol": "",
        "space_group_number_recomputed": "",
        "space_group_symbol_recomputed": "",
        "descriptor_status": "ok",
        "descriptor_error_code": "",
        "descriptor_error_message": "",
        "descriptor_source": "cif_recomputed",
    }

    analyzer = symmetry_analyzer or (
        lambda struct: default_symmetry_analyzer(struct, symprec=symprec)
    )
    try:
        symmetry = analyzer(structure)
        for field in (
            "crystal_system",
            "point_group_symbol",
            "space_group_number_recomputed",
            "space_group_symbol_recomputed",
        ):
            record[field] = symmetry.get(field, "")
    except Exception as exc:
        record["descriptor_status"] = "partial"
        record["descriptor_error_code"] = "symmetry_analysis_error"
        record["descriptor_error_message"] = str(exc)
    return record


def magnetic_annotations(
    structure: Any,
    config: MagneticAnnotationConfig,
) -> dict[str, Any]:
    elements = _composition_elements(structure)
    magnetic_elements = elements & config.all_elements
    contains_3d = bool(magnetic_elements & config.transition_3d)
    contains_4f = bool(magnetic_elements & config.lanthanides)
    site_count = 0
    for site in _iter_sites(structure):
        if _site_elements(site) & config.all_elements:
            site_count += 1

    if contains_3d:
        status = "candidate"
        reason = "contains_3d_element"
    elif contains_4f:
        status = "candidate"
        reason = "contains_4f_element"
    elif magnetic_elements:
        status = "candidate"
        reason = "contains_other_configured_magnetic_element"
    else:
        status = "nonmagnetic_by_composition"
        reason = "no_configured_magnetic_elements"

    return {
        "contains_magnetic_element": bool(magnetic_elements),
        "magnetic_elements": _json_array(magnetic_elements),
        "magnetic_element_species_count": len(magnetic_elements),
        "magnetic_element_site_count": site_count,
        "contains_3d": contains_3d,
        "contains_4f": contains_4f,
        "nonmagnetic_by_composition_heuristic": not magnetic_elements,
        "magnetic_screening_status": status,
        "magnetic_screening_reason": reason,
    }


def magnetic_not_evaluated(reason: str) -> dict[str, Any]:
    return {
        "contains_magnetic_element": "",
        "magnetic_elements": "[]",
        "magnetic_element_species_count": "",
        "magnetic_element_site_count": "",
        "contains_3d": "",
        "contains_4f": "",
        "nonmagnetic_by_composition_heuristic": "",
        "magnetic_screening_status": "not_evaluated",
        "magnetic_screening_reason": reason,
    }


def classify_compound_class(
    compound_class: str,
    rules: CompoundClassRules,
) -> tuple[str, str]:
    normalized = (compound_class or "").strip().lower()
    if not normalized:
        return "unknown", "missing_compound_class"
    if normalized in rules.rejected:
        return "rejected", "compound_class_rejected"
    if normalized in rules.high_priority:
        return "high_priority", "compound_class_high_priority"
    if normalized in rules.low_priority:
        return "low_priority", "compound_class_low_priority"
    return rules.unlisted_status, "compound_class_unlisted"


def _row_parse_error(
    row: Mapping[str, str],
    message: str,
    warning_records: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    return {
        **_cif_load_annotations(warning_records, error=True),
        "n_sites": "",
        "composition_num_atoms": "",
        "volume_A3": "",
        "volume_per_site_A3": "",
        "volume_per_composition_atom_A3": "",
        "density_g_cm3": "",
        "crystal_system": "",
        "point_group_symbol": "",
        "space_group_number_recomputed": "",
        "space_group_symbol_recomputed": "",
        "descriptor_status": "error",
        "descriptor_error_code": "cif_parse_error",
        "descriptor_error_message": message,
        "descriptor_source": "cif_recomputed",
        **magnetic_not_evaluated("cif_parse_failed"),
    }


def enrich_manifest_rows(
    rows: Sequence[Mapping[str, str]],
    *,
    structure_loader: StructureLoader = default_structure_loader,
    symmetry_analyzer: Optional[SymmetryAnalyzer] = None,
    config: EnrichmentAnnotationConfig,
    limit: Optional[int] = None,
    fail_fast: bool = False,
) -> list[dict[str, Any]]:
    if limit is not None and limit < 0:
        raise ValueError("limit must be None or non-negative")
    all_rows = list(rows)
    seen: set[str] = set()
    for row in all_rows:
        sample_uid = (row.get("sample_uid") or "").strip()
        if not sample_uid:
            raise ValueError("sample_uid must be non-empty")
        if sample_uid in seen:
            raise ValueError(f"Duplicate sample_uid: {sample_uid}")
        seen.add(sample_uid)
    selected_rows = all_rows if limit is None else all_rows[:limit]

    output: list[dict[str, Any]] = []
    for row in selected_rows:
        sample_uid = (row.get("sample_uid") or "").strip()
        enriched: dict[str, Any] = dict(row)
        enriched["structure_id"] = sample_uid
        status, reason = classify_compound_class(
            row.get("compound_class", ""), config.class_rules
        )
        enriched["compound_class_filter_status"] = status
        enriched["compound_class_filter_reason"] = reason

        try:
            load_result = _load_structure_with_warning_capture(
                structure_loader,
                row.get("cif_path", ""),
            )
        except StructureLoadError as exc:
            if fail_fast:
                raise exc.original from exc
            enriched.update(_row_parse_error(row, str(exc), exc.warning_records))
            output.append(enriched)
            continue

        structure = load_result.structure
        enriched.update(_cif_load_annotations(load_result.warnings, error=False))

        try:
            enriched.update(
                compute_structural_annotations(
                    structure,
                    symmetry_analyzer=symmetry_analyzer,
                    symprec=config.symprec,
                )
            )
        except Exception as exc:
            if fail_fast:
                raise
            enriched.update(
                {
                    "n_sites": "",
                    "composition_num_atoms": "",
                    "volume_A3": "",
                    "volume_per_site_A3": "",
                    "volume_per_composition_atom_A3": "",
                    "density_g_cm3": "",
                    "crystal_system": "",
                    "point_group_symbol": "",
                    "space_group_number_recomputed": "",
                    "space_group_symbol_recomputed": "",
                    "descriptor_status": "error",
                    "descriptor_error_code": "basic_descriptor_error",
                    "descriptor_error_message": str(exc),
                    "descriptor_source": "cif_recomputed",
                }
            )

        try:
            if enriched.get("descriptor_error_code") == "basic_descriptor_error":
                enriched.update(magnetic_not_evaluated("magnetic_annotation_error"))
            else:
                enriched.update(magnetic_annotations(structure, config.magnetic))
        except Exception as exc:
            if fail_fast:
                raise
            enriched.update(magnetic_not_evaluated("magnetic_annotation_error"))
            enriched["magnetic_screening_status"] = "error"
            if not enriched.get("descriptor_error_message"):
                enriched["descriptor_error_message"] = str(exc)
        output.append(enriched)
    return output


def output_fieldnames(input_fieldnames: Sequence[str]) -> list[str]:
    fields = list(input_fieldnames)
    for field_name in ANNOTATION_FIELDS:
        if field_name not in fields:
            fields.append(field_name)
    return fields


def run_enrichment_annotations(
    *,
    input_path: str | Path,
    output_path: str | Path,
    structure_loader: StructureLoader = default_structure_loader,
    symmetry_analyzer: Optional[SymmetryAnalyzer] = None,
    config: Optional[EnrichmentAnnotationConfig] = None,
    config_path: str | Path = "config/magnetism.yaml",
    limit: Optional[int] = None,
    fail_fast: bool = False,
) -> EnrichmentAnnotationReport:
    runtime_config = config or load_enrichment_annotation_config(config_path)
    rows, fieldnames = read_manifest_csv(input_path)
    enriched = enrich_manifest_rows(
        rows,
        structure_loader=structure_loader,
        symmetry_analyzer=symmetry_analyzer,
        config=runtime_config,
        limit=limit,
        fail_fast=fail_fast,
    )
    out_fields = output_fieldnames(fieldnames)
    written_path = write_stage_csv_atomic(output_path, enriched, out_fields)
    return EnrichmentAnnotationReport(
        input_count=len(rows),
        output_count=len(enriched),
        output_path=written_path,
        fieldnames=out_fields,
    )
