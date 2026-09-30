from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from mvpipeline.enrichment.standardized import (
    EXPECTED_ENERGY_ERROR_IDS,
    EXPECTED_MASTER_SHA256,
    EXPECTED_TOTAL_COLUMNS,
    EXPECTED_TOTAL_ROWS,
    STANDARDIZED_COHORTS,
    STANDARDIZED_MASTER_FIELDS,
    STANDARDIZED_MASTER_PATH,
    split_baseline_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = REPO_ROOT / STANDARDIZED_MASTER_PATH

EXPECTED_COUNTS = {
    "mattergen_baseline": 1657,
    "mattergen_finetuned": 1376,
    "concdvae_baseline": 1864,
    "concdvae_finetuned": 1299,
    "crystalformer_baseline": 1083,
    "crystalformer_finetuned": 1380,
    "crystallm_baseline": 98,
    "crystallm_finetuned": 217,
    "crysjepa_base": 1764,
    "crysjepa_refined": 1543,
}


def read_master() -> tuple[list[str], list[dict[str, str]]]:
    with MASTER_PATH.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_standardized_master_shape_identity_and_hash():
    fieldnames, rows = read_master()

    assert len(rows) == EXPECTED_TOTAL_ROWS
    assert len(fieldnames) == EXPECTED_TOTAL_COLUMNS
    assert tuple(fieldnames) == STANDARDIZED_MASTER_FIELDS
    assert sha256_file(MASTER_PATH) == EXPECTED_MASTER_SHA256

    structure_ids = [row["structure_id"] for row in rows]
    sample_uids = [row["sample_uid"] for row in rows]

    assert len(set(structure_ids)) == EXPECTED_TOTAL_ROWS
    assert len(set(sample_uids)) == EXPECTED_TOTAL_ROWS
    assert sample_uids == structure_ids


def test_standardized_master_cohort_counts_and_formula_coverage():
    _, rows = read_master()

    counts = {
        cohort: sum(1 for row in rows if row["analysis_cohort"] == cohort)
        for cohort in EXPECTED_COUNTS
    }
    assert counts == EXPECTED_COUNTS

    assert sum(1 for row in rows if row["formula_reduced"]) == EXPECTED_TOTAL_ROWS
    assert (
        sum(1 for row in rows if row["formula_full_canonical"])
        == EXPECTED_TOTAL_ROWS
    )

    mismatches = [
        row["structure_id"]
        for row in rows
        if row.get("formula_reduced_recomputed")
        and row["formula_reduced"] != row["formula_reduced_recomputed"]
    ]
    assert mismatches == []


def test_standardized_master_energy_and_magnetism_status_contract():
    _, rows = read_master()

    energy_ok = [row for row in rows if row["energy_status"] == "ok"]
    energy_error = [row for row in rows if row["energy_status"] == "error"]
    magnetism_ok = [row for row in rows if row["magnetism_status"] == "ok"]
    magnetism_error = [
        row for row in rows if row["magnetism_status"] == "error"
    ]

    assert len(energy_ok) == EXPECTED_TOTAL_ROWS - len(EXPECTED_ENERGY_ERROR_IDS)
    assert len(energy_error) == 4
    assert {row["structure_id"] for row in energy_error} == EXPECTED_ENERGY_ERROR_IDS

    assert len(magnetism_ok) == EXPECTED_TOTAL_ROWS
    assert magnetism_error == []


def test_standardized_registry_order_and_counts():
    assert [cohort.key for cohort in STANDARDIZED_COHORTS] == list(EXPECTED_COUNTS)
    assert {
        cohort.key: cohort.expected_count for cohort in STANDARDIZED_COHORTS
    } == EXPECTED_COUNTS


def test_baseline_split_is_deterministic_and_counted():
    split = split_baseline_manifest(
        REPO_ROOT
        / "tables/04_magnetic_screening/baseline_master_production_annotations.csv"
    )

    baseline_counts = {
        key: len(rows)
        for key, (_, rows) in split.items()
    }

    assert baseline_counts == {
        "mattergen_baseline": 1657,
        "concdvae_baseline": 1864,
        "crystalformer_baseline": 1083,
        "crystallm_baseline": 98,
    }
    assert split["mattergen_baseline"][1][0]["structure_id"] == (
        "mg__benchmark_mgd_2000__mgd_0p00_g_1p2_seed_101__cand_0001"
    )
