from __future__ import annotations

import csv

from mvpipeline.report.records import BufferedCSVWriter


def test_reopen_replaces_previous_run(tmp_path):
    path = tmp_path / "all_structures.csv"
    fieldnames = ["structure_id", "status"]

    with BufferedCSVWriter(
        path=path,
        fieldnames=fieldnames,
        flush_every=1,
    ) as writer:
        writer.add({"structure_id": "first_run", "status": "validated"})

    with BufferedCSVWriter(
        path=path,
        fieldnames=fieldnames,
        flush_every=1,
    ) as writer:
        writer.add({"structure_id": "second_run", "status": "validated"})

    with path.open(
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert rows == [
        {
            "structure_id": "second_run",
            "status": "validated",
        }
    ]

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines.count("structure_id,status") == 1
