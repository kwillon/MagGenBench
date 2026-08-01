import os
import subprocess
import sys
import textwrap
from pathlib import Path


BLOCKED_IMPORTS = {"yaml", "pymatgen", "matgl", "chgnet", "torch"}


def run_import_check(body: str) -> subprocess.CompletedProcess[str]:
    repo_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    src_path = str(repo_root / "src")
    env["PYTHONPATH"] = (
        src_path
        if not env.get("PYTHONPATH")
        else src_path + os.pathsep + env["PYTHONPATH"]
    )
    header = textwrap.dedent(
        f"""
        import builtins
        import sys

        blocked = {sorted(BLOCKED_IMPORTS)!r}
        real_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name.split(".", 1)[0] in blocked:
                raise AssertionError(
                    f"{{name}} must not be imported for dependency-light API"
                )
            return real_import(name, *args, **kwargs)

        builtins.__import__ = guarded_import
        """
    )
    footer = textwrap.dedent(
        """

        loaded_blocked = [
            name for name in sys.modules
            if name.split(".", 1)[0] in blocked
        ]
        assert loaded_blocked == [], loaded_blocked
        """
    )
    script = header + "\n" + textwrap.dedent(body).strip() + "\n" + footer
    return subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        env=env,
        text=True,
        capture_output=True,
    )


def assert_import_check_passes(body: str) -> None:
    completed = run_import_check(body)
    assert completed.returncode == 0, completed.stderr


def test_mvpipeline_import_is_dependency_light():
    assert_import_check_passes(
        """
        import mvpipeline

        assert callable(mvpipeline.run_validation)
        """
    )


def test_energy_and_magnetism_contract_imports_are_dependency_light():
    assert_import_check_passes(
        """
        import mvpipeline.energy
        import mvpipeline.magnetism

        assert mvpipeline.energy.EnergyInput.__name__ == "EnergyInput"
        assert mvpipeline.magnetism.MagnetismInput.__name__ == "MagnetismInput"
        """
    )


def test_lazy_top_level_exports_are_listed_in_public_api():
    assert_import_check_passes(
        """
        import mvpipeline

        expected = {
            "run_validation",
            "PipelineConfig",
            "DedupConfig",
            "load_config",
            "StructureItem",
            "Descriptors",
            "Rejection",
            "ValidationResult",
            "ValidationStatus",
            "GeometryQuality",
            "RejectionReason",
            "MAGNETIC_ELEMENTS_DEFAULT",
        }

        assert expected.issubset(set(mvpipeline.__all__))
        """
    )
