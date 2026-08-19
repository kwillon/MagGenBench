from __future__ import annotations

import csv
import hashlib
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ANALYSIS_V2 = (
    REPO_ROOT / "tables/10_analysis_v2_magnetic/analysis_v2_magnetic.csv"
)
EXPECTED_SHA256 = (
    "221deb82b2ac3e5442b4930dd9dcf05dc411e46244f1ce80a401a7d6775bc181"
)
EXPECTED_COHORT_COUNTS = {
    "mattergen_baseline": 1657,
    "mattergen_finetuned": 1376,
    "concdvae_baseline": 1864,
    "concdvae_finetuned": 1299,
    "crystalformer_baseline": 1083,
    "crystallm_baseline": 98,
    "crysjepa_base": 1764,
    "crysjepa_refined": 1543,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def test_canonical_analysis_v2_magnetic_artifact_contract():
    assert CANONICAL_ANALYSIS_V2.exists()
    assert sha256_file(CANONICAL_ANALYSIS_V2) == EXPECTED_SHA256

    fieldnames, rows = read_rows(CANONICAL_ANALYSIS_V2)

    assert len(rows) == 10684
    assert len(fieldnames) == 118
    assert not any(
        field.endswith("_x") or field.endswith("_y")
        for field in fieldnames
    )

    structure_ids = [row["structure_id"] for row in rows]
    sample_uids = [row["sample_uid"] for row in rows]

    assert len(set(structure_ids)) == 10684
    assert len(set(sample_uids)) == 10684
    assert structure_ids == sample_uids

    assert Counter(row["analysis_cohort"] for row in rows) == (
        EXPECTED_COHORT_COUNTS
    )
    assert Counter(row["descriptor_v2_status"] for row in rows) == {
        "ok": 10684,
    }
    assert Counter(row["magnetic_geometry_status"] for row in rows) == {
        "ok": 7756,
        "not_applicable": 2928,
    }
    assert Counter(row["magnetic_symmetry_status"] for row in rows) == {
        "ok": 10684,
    }
    assert Counter(row["energy_status"] for row in rows) == {
        "ok": 10680,
        "error": 4,
    }
    assert Counter(row["magnetism_status"] for row in rows) == {
        "ok": 10684,
    }
