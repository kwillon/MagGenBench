from __future__ import annotations

import csv
import hashlib
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_DESCRIPTOR_V2 = (
    REPO_ROOT
    / "tables/09_descriptor_v2_magnetic/descriptor_v2_magnetic.csv"
)
EXPECTED_SHA256 = (
    "7667aad820f859a13b326c1b6d3c76c258ca4b63bc55ef20066ce99d79e11980"
)


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


def test_canonical_descriptor_v2_magnetic_artifact_contract():
    assert CANONICAL_DESCRIPTOR_V2.exists()
    assert sha256_file(CANONICAL_DESCRIPTOR_V2) == EXPECTED_SHA256

    fieldnames, rows = read_rows(CANONICAL_DESCRIPTOR_V2)

    assert len(rows) == 10684
    assert len(fieldnames) == 41

    structure_ids = [row["structure_id"] for row in rows]
    sample_uids = [row["sample_uid"] for row in rows]

    assert len(set(structure_ids)) == 10684
    assert len(set(sample_uids)) == 10684
    assert structure_ids == sample_uids

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
