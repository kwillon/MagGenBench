from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence


BASELINE_MANIFEST = Path(
    "tables/04_magnetic_screening/baseline_master_production_annotations.csv"
)

STANDARDIZED_MASTER_PATH = Path(
    "tables/08_standardized_enrichment/standardized_enrichment.csv"
)

EXPECTED_MASTER_SHA256 = (
    "8a62cc9720de9249cdb2c6ce929fa3f98e065ef93c881c1c1160d330940db02d"
)

EXPECTED_TOTAL_ROWS = 10684
EXPECTED_TOTAL_COLUMNS = 87

EXPECTED_ENERGY_ERROR_IDS = frozenset(
    {
        "cf__cf_repr_v1__cf_repr_v1_s19_000095",
        "cf__cf_repr_v1__cf_repr_v1_s20_000074",
        "cf__cf_repr_v1__cf_repr_v1_s20_000093",
        "cllm__crystallm_benchmark_30x100_seed1337_t08_k10__Nd2Fe14B__sample_88",
    }
)

STANDARDIZED_MASTER_FIELDS = (
    "analysis_cohort",
    "analysis_family",
    "analysis_state",
    "structure_id",
    "sample_uid",
    "model_name",
    "model_short",
    "formula_reduced",
    "formula_full_canonical",
    "run_uid",
    "source_sample_id",
    "cif_path",
    "cif_file_name",
    "formula_full",
    "status",
    "status_source",
    "rejection_reason",
    "compound_class",
    "cif_path_original",
    "cif_exists",
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
    "energy_join_status",
    "energy_status",
    "energy_error_code",
    "energy_error_message",
    "energy_backend",
    "energy_model_name",
    "energy_energy_unit",
    "energy_total_energy_eV",
    "energy_total_energy_eV_per_atom",
    "energy_formation_energy_proxy_eV",
    "energy_formation_energy_proxy_eV_per_atom",
    "energy_stability_energy_proxy_eV_per_atom",
    "energy_details",
    "magnetism_join_status",
    "magnetism_status",
    "magnetism_error_code",
    "magnetism_error_message",
    "magnetism_backend",
    "magnetism_model_name",
    "magnetism_predicted_moment_value",
    "magnetism_moment_unit",
    "magnetism_moment_normalization",
    "magnetism_uncertainty_proxy",
    "magnetism_confidence_score",
    "magnetism_risk_level",
    "magnetism_details",
    "formula_full_recomputed",
    "mvp_is_suspicious",
    "mvp_is_duplicate",
    "mvp_is_novel",
    "mvp_is_magnetic",
    "mvp_n_atoms",
    "mvp_density",
    "mvp_volume_per_atom",
    "mvp_spacegroup",
    "mvp_min_distance",
    "mvp_charge_solution_json",
    "mvp_details_json",
    "formula_reduced_recomputed",
)


@dataclass(frozen=True)
class StandardizedCohort:
    key: str
    analysis_family: str
    analysis_state: str
    expected_count: int
    model_name: str
    source_manifest: Path | None = None

    @property
    def manifest_name(self) -> str:
        return f"{self.key}.csv"

    @property
    def energy_name(self) -> str:
        return f"{self.key}_chgnet.csv"

    @property
    def magnetism_name(self) -> str:
        return f"{self.key}_dxmag.csv"

    @property
    def joined_name(self) -> str:
        return f"{self.key}_joined.csv"


STANDARDIZED_COHORTS = (
    StandardizedCohort(
        key="mattergen_baseline",
        analysis_family="MatterGen",
        analysis_state="baseline",
        expected_count=1657,
        model_name="MatterGen",
    ),
    StandardizedCohort(
        key="mattergen_finetuned",
        analysis_family="MatterGen",
        analysis_state="fine_tuned",
        expected_count=1376,
        model_name="MatterGen-finetuned",
        source_manifest=Path(
            "tables/04_magnetic_screening/"
            "phase5b_mattergen_finetuned_production_annotations.csv"
        ),
    ),
    StandardizedCohort(
        key="concdvae_baseline",
        analysis_family="Con-CDVAE",
        analysis_state="baseline",
        expected_count=1864,
        model_name="Con-CDVAE",
    ),
    StandardizedCohort(
        key="concdvae_finetuned",
        analysis_family="Con-CDVAE",
        analysis_state="fine_tuned",
        expected_count=1299,
        model_name="Con-CDVAE-finetuned",
        source_manifest=Path(
            "tables/04_magnetic_screening/"
            "phase5b_concdvae_finetuned_production_annotations.csv"
        ),
    ),
    StandardizedCohort(
        key="crystalformer_baseline",
        analysis_family="CrystalFormer",
        analysis_state="baseline",
        expected_count=1083,
        model_name="CrystalFormer",
    ),
    StandardizedCohort(
        key="crystallm_baseline",
        analysis_family="CrystaLLM",
        analysis_state="baseline",
        expected_count=98,
        model_name="CrystaLLM",
    ),
    StandardizedCohort(
        key="crysjepa_base",
        analysis_family="Crys-JEPA",
        analysis_state="base",
        expected_count=1764,
        model_name="Crys-JEPA-Base",
        source_manifest=Path(
            "tables/04_magnetic_screening/"
            "crysjepa_base_production_annotations.csv"
        ),
    ),
    StandardizedCohort(
        key="crysjepa_refined",
        analysis_family="Crys-JEPA",
        analysis_state="refined",
        expected_count=1543,
        model_name="Crys-JEPA-Refined",
        source_manifest=Path(
            "tables/04_magnetic_screening/"
            "crysjepa_refined_production_annotations.csv"
        ),
    ),
)

STANDARDIZED_COHORT_BY_KEY = {
    cohort.key: cohort for cohort in STANDARDIZED_COHORTS
}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Iterable[Mapping[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_baseline_manifest(
    source_path: Path = BASELINE_MANIFEST,
) -> dict[str, tuple[list[str], list[dict[str, str]]]]:
    fieldnames, rows = read_csv(source_path)
    if "model_name" not in fieldnames:
        raise RuntimeError(f"{source_path}: missing model_name column")

    baseline = {
        cohort.key: (fieldnames, [])
        for cohort in STANDARDIZED_COHORTS
        if cohort.source_manifest is None
    }
    model_to_key = {
        cohort.model_name: cohort.key
        for cohort in STANDARDIZED_COHORTS
        if cohort.source_manifest is None
    }

    for row in rows:
        model_name = row.get("model_name", "")
        key = model_to_key.get(model_name)
        if key is None:
            continue
        baseline[key][1].append(row)

    assigned = sum(len(cohort_rows) for _, cohort_rows in baseline.values())
    if assigned != len(rows):
        raise RuntimeError(
            "Expected all baseline rows to map to standardized cohorts; "
            f"assigned {assigned} of {len(rows)}"
        )

    for key, (_, cohort_rows) in baseline.items():
        expected = STANDARDIZED_COHORT_BY_KEY[key].expected_count
        if len(cohort_rows) != expected:
            raise RuntimeError(
                f"{key}: expected {expected} baseline rows, "
                f"got {len(cohort_rows)}"
            )

    return baseline


def prepare_manifests(output_dir: Path, repo_root: Path = Path(".")) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    baseline = split_baseline_manifest(repo_root / BASELINE_MANIFEST)

    for cohort in STANDARDIZED_COHORTS:
        destination = output_dir / cohort.manifest_name
        if cohort.source_manifest is None:
            fieldnames, rows = baseline[cohort.key]
            write_csv(destination, fieldnames, rows)
        else:
            source = repo_root / cohort.source_manifest
            shutil.copyfile(source, destination)


def row_with_standardized_identity(
    row: Mapping[str, str],
    cohort: StandardizedCohort,
) -> dict[str, str]:
    output = {field: row.get(field, "") for field in STANDARDIZED_MASTER_FIELDS}
    output["analysis_cohort"] = cohort.key
    output["analysis_family"] = cohort.analysis_family
    output["analysis_state"] = cohort.analysis_state

    formula_full = row.get("formula_full", "")
    formula_full_recomputed = row.get("formula_full_recomputed", "")
    output["formula_full_canonical"] = formula_full or formula_full_recomputed
    return output


def build_standardized_master(joined_dir: Path, output_path: Path) -> None:
    rows: list[dict[str, str]] = []
    for cohort in STANDARDIZED_COHORTS:
        _, cohort_rows = read_csv(joined_dir / cohort.joined_name)
        if len(cohort_rows) != cohort.expected_count:
            raise RuntimeError(
                f"{cohort.key}: expected {cohort.expected_count} joined rows, "
                f"got {len(cohort_rows)}"
            )
        rows.extend(
            row_with_standardized_identity(row, cohort)
            for row in cohort_rows
        )

    write_csv(output_path, STANDARDIZED_MASTER_FIELDS, rows)
    validate_standardized_master(output_path)


def _nonempty_count(rows: Sequence[Mapping[str, str]], field: str) -> int:
    return sum(1 for row in rows if row.get(field, ""))


def _status_count(
    rows: Sequence[Mapping[str, str]],
    field: str,
    status: str,
) -> int:
    return sum(1 for row in rows if row.get(field) == status)


def validate_standardized_master(path: Path) -> None:
    fieldnames, rows = read_csv(path)
    if len(rows) != EXPECTED_TOTAL_ROWS:
        raise RuntimeError(f"Expected {EXPECTED_TOTAL_ROWS} rows, got {len(rows)}")
    if len(fieldnames) != EXPECTED_TOTAL_COLUMNS:
        raise RuntimeError(
            f"Expected {EXPECTED_TOTAL_COLUMNS} columns, got {len(fieldnames)}"
        )
    if tuple(fieldnames) != STANDARDIZED_MASTER_FIELDS:
        raise RuntimeError("Standardized master field order check failed")

    structure_ids = [row.get("structure_id", "") for row in rows]
    sample_uids = [row.get("sample_uid", "") for row in rows]
    if len(set(structure_ids)) != EXPECTED_TOTAL_ROWS:
        raise RuntimeError("structure_id uniqueness check failed")
    if len(set(sample_uids)) != EXPECTED_TOTAL_ROWS:
        raise RuntimeError("sample_uid uniqueness check failed")
    if structure_ids != sample_uids:
        raise RuntimeError("sample_uid must equal structure_id for every row")

    for cohort in STANDARDIZED_COHORTS:
        count = sum(1 for row in rows if row.get("analysis_cohort") == cohort.key)
        if count != cohort.expected_count:
            raise RuntimeError(
                f"{cohort.key}: expected {cohort.expected_count} rows, got {count}"
            )

    if _nonempty_count(rows, "formula_reduced") != EXPECTED_TOTAL_ROWS:
        raise RuntimeError("formula_reduced coverage check failed")
    if _nonempty_count(rows, "formula_full_canonical") != EXPECTED_TOTAL_ROWS:
        raise RuntimeError("formula_full_canonical coverage check failed")

    mismatches = [
        row.get("structure_id", "")
        for row in rows
        if row.get("formula_reduced_recomputed", "")
        and row.get("formula_reduced") != row.get("formula_reduced_recomputed")
    ]
    if mismatches:
        raise RuntimeError(
            "formula_reduced/formula_reduced_recomputed mismatches: "
            + ", ".join(mismatches[:5])
        )

    if _status_count(rows, "energy_status", "ok") != 10680:
        raise RuntimeError("energy ok count check failed")
    if _status_count(rows, "energy_status", "error") != 4:
        raise RuntimeError("energy error count check failed")

    error_ids = frozenset(
        row.get("structure_id", "")
        for row in rows
        if row.get("energy_status") == "error"
    )
    if error_ids != EXPECTED_ENERGY_ERROR_IDS:
        raise RuntimeError("energy error ID check failed")

    if _status_count(rows, "magnetism_status", "ok") != EXPECTED_TOTAL_ROWS:
        raise RuntimeError("magnetism ok count check failed")
    if _status_count(rows, "magnetism_status", "error") != 0:
        raise RuntimeError("magnetism error count check failed")


def write_sha_manifest(root: Path, output_path: Path) -> None:
    paths = sorted(path for path in root.rglob("*.csv") if path.is_file())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for path in paths:
            relpath = path.relative_to(root).as_posix()
            handle.write(f"{sha256_file(path)}  {relpath}\n")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare and validate standardized enrichment artifacts."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare-manifests")
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.add_argument("--repo-root", type=Path, default=Path("."))

    build = subparsers.add_parser("build-master")
    build.add_argument("--joined-dir", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)

    validate = subparsers.add_parser("validate-master")
    validate.add_argument("--input", type=Path, required=True)

    sha = subparsers.add_parser("write-sha-manifest")
    sha.add_argument("--root", type=Path, required=True)
    sha.add_argument("--output", type=Path, required=True)

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)

    if args.command == "prepare-manifests":
        prepare_manifests(args.output_dir, repo_root=args.repo_root)
    elif args.command == "build-master":
        build_standardized_master(args.joined_dir, args.output)
    elif args.command == "validate-master":
        validate_standardized_master(args.input)
    elif args.command == "write-sha-manifest":
        write_sha_manifest(args.root, args.output)
    else:
        raise RuntimeError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    main()
