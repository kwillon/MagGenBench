import builtins
import importlib
import sys


def test_energy_and_magnetism_contract_imports_do_not_require_pymatgen_or_yaml(
    monkeypatch,
):
    for name in list(sys.modules):
        if (
            name == "mvpipeline"
            or name.startswith("mvpipeline.")
            or name == "pymatgen"
            or name.startswith("pymatgen.")
            or name == "yaml"
            or name.startswith("yaml.")
        ):
            sys.modules.pop(name, None)

    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if (
            name == "pymatgen"
            or name.startswith("pymatgen.")
            or name == "yaml"
            or name.startswith("yaml.")
        ):
            raise AssertionError(f"{name} must not be imported for contracts")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    mvpipeline = importlib.import_module("mvpipeline")
    energy = importlib.import_module("mvpipeline.energy")
    magnetism = importlib.import_module("mvpipeline.magnetism")

    assert callable(mvpipeline.run_validation)
    assert energy.EnergyInput.__name__ == "EnergyInput"
    assert magnetism.MagnetismInput.__name__ == "MagnetismInput"


def test_lazy_top_level_exports_are_listed_in_public_api():
    mvpipeline = importlib.import_module("mvpipeline")

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
