import os
import subprocess
import sys
import textwrap

import pytest

from mvpipeline.energy import EnergyInput, EnergyStatus
from mvpipeline.energy.backends.chgnet import CHGNetBackend
from mvpipeline.energy.backends.factory import create_energy_backend
from mvpipeline.energy.backends.fake import FakeEnergyBackend
from mvpipeline.energy.backends.matgl import MatGLBackend
from mvpipeline.energy.config import EnergyBackendSettings


class MockEnergyModel:
    def __init__(self, value):
        self.value = value
        self.calls = 0

    def predict_energy(self, structure):
        self.calls += 1
        return self.value


def make_item(n_atoms=4):
    return EnergyInput(
        structure_id="s1",
        structure=object(),
        n_atoms=n_atoms,
        composition={"Fe": 2, "O": 2},
    )


def test_backend_modules_import_without_optional_dependencies():
    script = textwrap.dedent(
        """
        import builtins
        import importlib

        blocked = {"matgl", "chgnet", "torch", "pymatgen"}
        real_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name.split(".", 1)[0] in blocked:
                raise AssertionError(
                    f"{name} must not be imported at module import time"
                )
            return real_import(name, *args, **kwargs)

        builtins.__import__ = guarded_import
        importlib.import_module("mvpipeline.energy.backends.matgl")
        importlib.import_module("mvpipeline.energy.backends.chgnet")
        """
    )
    env = dict(os.environ)
    src_path = os.path.abspath("src")
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


def test_matgl_adapter_uses_injected_loader_once_and_normalizes_total_energy():
    model = MockEnergyModel(-8.0)
    calls = []

    def loader(model_name, device):
        calls.append((model_name, device))
        return model

    backend = MatGLBackend(
        model_name="mock-matgl",
        device="cpu",
        output_semantics="total_energy_eV",
        model_loader=loader,
    )

    first = backend.predict(make_item())
    second = backend.predict(make_item())

    assert calls == [("mock-matgl", "cpu")]
    assert model.calls == 2
    assert first.status == EnergyStatus.OK
    assert second == first
    assert first.backend == "matgl"
    assert first.model_name == "mock-matgl"
    assert first.energy_unit == "eV"
    assert first.total_energy_eV == -8.0
    assert first.total_energy_eV_per_atom == -2.0


def test_chgnet_adapter_with_mock_model_converts_per_atom_to_total_energy():
    backend = CHGNetBackend(
        model_name="mock-chgnet",
        model_selector="mock-selector",
        output_semantics="energy_per_atom_eV",
        model_loader=lambda selector, device: MockEnergyModel(-1.5),
    )

    result = backend.predict(make_item(n_atoms=3))

    assert result.status == EnergyStatus.OK
    assert result.backend == "chgnet"
    assert result.total_energy_eV == -4.5
    assert result.total_energy_eV_per_atom == -1.5
    assert result.details["model_selector"] == "mock-selector"


def test_invalid_n_atoms_returns_structured_error_result():
    backend = MatGLBackend(
        model_name="mock-matgl",
        model_loader=lambda model_name, device: MockEnergyModel(-8.0),
    )

    result = backend.predict(make_item(n_atoms=0))

    assert result.status == EnergyStatus.ERROR
    assert result.error_code == "invalid_n_atoms"
    assert result.error_message
    assert result.total_energy_eV is None


def test_missing_optional_dependency_returns_structured_error_result():
    def loader(model_name, device):
        raise ImportError("missing optional package")

    backend = MatGLBackend(model_name="mock-matgl", model_loader=loader)

    result = backend.predict(make_item())

    assert result.status == EnergyStatus.ERROR
    assert result.error_code == "missing_optional_dependency"
    assert "missing optional package" in result.error_message
    assert result.total_energy_eV is None


def test_malformed_model_output_returns_structured_error_result():
    backend = CHGNetBackend(
        model_name="mock-chgnet",
        model_loader=lambda selector, device: MockEnergyModel(None),
    )

    result = backend.predict(make_item())

    assert result.status == EnergyStatus.ERROR
    assert result.error_code == "model_output_error"
    assert result.error_message
    assert result.total_energy_eV is None


def test_unexpected_model_errors_are_not_hidden():
    class ExplodingModel:
        def predict_energy(self, structure):
            raise RuntimeError("model exploded")

    backend = MatGLBackend(
        model_name="mock-matgl",
        model_loader=lambda model_name, device: ExplodingModel(),
    )

    with pytest.raises(RuntimeError, match="model exploded"):
        backend.predict(make_item())


def test_backend_factory_selector():
    fake = create_energy_backend("fake")
    matgl = create_energy_backend(
        EnergyBackendSettings(
            name="matgl",
            model_name="factory-matgl",
            device="cpu",
            output_semantics="total_energy_eV",
        )
    )
    chgnet = create_energy_backend(
        {
            "name": "chgnet",
            "model_name": "factory-chgnet",
            "model_selector": "factory-selector",
            "device": "cpu",
            "output_semantics": "energy_per_atom_eV",
        }
    )

    assert isinstance(fake, FakeEnergyBackend)
    assert isinstance(matgl, MatGLBackend)
    assert matgl.model_name == "factory-matgl"
    assert isinstance(chgnet, CHGNetBackend)
    assert chgnet.model_selector == "factory-selector"
