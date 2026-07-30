from mvpipeline.energy import EnergyInput, EnergyStatus
from mvpipeline.energy.backends import FakeEnergyBackend


def test_fake_energy_backend_is_deterministic_and_structured():
    backend = FakeEnergyBackend()
    item = EnergyInput(
        structure_id="fake-1",
        structure=object(),
        n_atoms=2,
        composition={"Fe": 1, "O": 1},
    )

    first = backend.predict(item)
    second = backend.predict(item)

    assert first == second
    assert first.structure_id == "fake-1"
    assert first.status == EnergyStatus.OK
    assert first.error_code == ""
    assert first.total_energy_eV == -2.0
    assert first.total_energy_eV_per_atom == -1.0


def test_fake_energy_backend_returns_structured_error():
    backend = FakeEnergyBackend()
    item = EnergyInput(
        structure_id="bad",
        structure=object(),
        n_atoms=0,
        composition={},
    )

    result = backend.predict(item)

    assert result.structure_id == "bad"
    assert result.status == EnergyStatus.ERROR
    assert result.error_code == "fake_energy_error"
    assert result.error_message
