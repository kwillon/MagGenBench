from __future__ import annotations

import csv
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from mvpipeline.io.manifests import load_manifest_rows


FIELDS = [
    "sample_uid",
    "structure_id",
    "cif_path",
    "formula_reduced",
]


def write_manifest(
    path: Path,
    rows: list[dict[str, str]],
    *,
    encoding: str = "utf-8",
) -> None:
    with path.open("w", newline="", encoding=encoding) as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def base_row(structure_id: str = "s1") -> dict[str, str]:
    return {
        "sample_uid": structure_id,
        "structure_id": structure_id,
        "cif_path": f"{structure_id}.cif",
        "formula_reduced": "FeO",
    }


def test_normal_csv_preserves_dictreader_rows_and_order(tmp_path: Path) -> None:
    path = tmp_path / "manifest.csv"
    rows = [base_row("s1"), base_row("s2")]
    write_manifest(path, rows)

    loaded = load_manifest_rows(path)

    assert loaded == rows
    assert [row["structure_id"] for row in loaded] == ["s1", "s2"]


def test_header_only_csv_is_empty_manifest(tmp_path: Path) -> None:
    path = tmp_path / "manifest.csv"
    write_manifest(path, [])

    with pytest.raises(RuntimeError, match="Empty manifest"):
        load_manifest_rows(path)


def test_empty_file_is_empty_manifest(tmp_path: Path) -> None:
    path = tmp_path / "manifest.csv"
    path.write_text("", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Empty manifest"):
        load_manifest_rows(path)


def test_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_manifest_rows(tmp_path / "missing.csv")


def test_utf8_sig_and_non_ascii_content_are_preserved(tmp_path: Path) -> None:
    path = tmp_path / "manifest.csv"
    rows = [base_row("структура-1")]
    rows[0]["formula_reduced"] = "PrFeO3"
    write_manifest(path, rows, encoding="utf-8-sig")

    assert load_manifest_rows(path) == rows


def test_validations_match_current_manifest_contract(tmp_path: Path) -> None:
    path = tmp_path / "manifest.csv"
    write_manifest(path, [base_row("s1"), base_row("s1")])

    with pytest.raises(RuntimeError, match="Duplicate structure_id"):
        load_manifest_rows(path)

    write_manifest(path, [{**base_row("s1"), "sample_uid": "other"}])

    with pytest.raises(RuntimeError, match="sample_uid/structure_id mismatch"):
        load_manifest_rows(path)

    write_manifest(path, [{**base_row("s1"), "structure_id": ""}])

    with pytest.raises(RuntimeError, match="Empty structure_id"):
        load_manifest_rows(path)


def test_manifest_loader_expects_path_like_object() -> None:
    with pytest.raises(AttributeError, match="open"):
        load_manifest_rows("manifest.csv")  # type: ignore[arg-type]


def test_manifest_module_is_dependency_light() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = textwrap.dedent(
        """
        import builtins
        import importlib
        import sys

        blocked = {
            "pymatgen",
            "yaml",
            "matgl",
            "chgnet",
            "torch",
            "numpy",
            "pandas",
            "matminer",
            "sklearn",
            "joblib",
        }
        real_import = builtins.__import__

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            root = name.split(".", 1)[0]
            if level == 0 and root in blocked:
                raise AssertionError(f"{name} must not be imported")
            return real_import(name, globals, locals, fromlist, level)

        builtins.__import__ = guarded_import
        importlib.import_module("mvpipeline.io.manifests")
        assert not [m for m in sys.modules if m.split(".", 1)[0] in blocked]
        """
    )
    env = dict(os.environ)
    src_path = str(repo_root / "src")
    env["PYTHONPATH"] = (
        src_path
        if not env.get("PYTHONPATH")
        else src_path + os.pathsep + env["PYTHONPATH"]
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        env=env,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
