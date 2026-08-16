from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path

from typer.testing import CliRunner

from mvpipeline.cli import app


def test_pyproject_keeps_mvp_and_adds_maggenbench_entry_point() -> None:
    root = Path(__file__).resolve().parents[1]
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    scripts = data["project"]["scripts"]
    assert scripts["mvp"] == "cli.app:app"
    assert scripts["maggenbench"] == "mvpipeline.cli:app"


def test_maggenbench_cli_exposes_reproduce_analysis_v1() -> None:
    runner = CliRunner()

    root_result = runner.invoke(app, ["--help"])
    reproduce_result = runner.invoke(app, ["reproduce", "--help"])
    analysis_result = runner.invoke(
        app,
        ["reproduce", "analysis-v1", "--help"],
    )

    assert root_result.exit_code == 0
    assert "reproduce" in root_result.output
    assert reproduce_result.exit_code == 0
    assert "analysis-v1" in reproduce_result.output
    assert analysis_result.exit_code == 0
    assert "--baseline-joined" in analysis_result.output


def test_maggenbench_cli_help_is_dependency_light() -> None:
    root = Path(__file__).resolve().parents[1]
    script = textwrap.dedent(
        """
        import builtins
        import sys

        blocked = {
            "chgnet",
            "torch",
            "pymatgen",
            "matminer",
            "sklearn",
            "joblib",
            "numpy",
            "pandas",
        }
        real_import = builtins.__import__

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            root = name.split(".", 1)[0]
            if level == 0 and root in blocked:
                raise AssertionError(f"{name} must not be imported")
            return real_import(name, globals, locals, fromlist, level)

        builtins.__import__ = guarded_import

        import mvpipeline.cli

        assert mvpipeline.cli.app is not None
        assert not [name for name in sys.modules if name.split(".", 1)[0] in blocked]
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
