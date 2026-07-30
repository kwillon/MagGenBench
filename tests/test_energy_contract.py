from mvpipeline.energy import (
    EnergyInput,
    EnergyResult,
    EnergyStatus,
    formation_energy_proxy,
    formation_energy_proxy_per_atom,
    positive_formation_energy_proxy,
)
from mvpipeline.energy.records import ENERGY_RECORD_FIELDS, energy_result_to_record


def test_energy_result_contract_has_required_status_and_error_fields():
    result = EnergyResult(structure_id="s1", status=EnergyStatus.OK)
    record = energy_result_to_record(result)

    assert record["structure_id"] == "s1"
    assert record["status"] == "ok"
    assert "error_code" in record
    assert "error_message" in record
    assert "formation_energy_proxy_eV" in ENERGY_RECORD_FIELDS
    assert "stability_energy_proxy_eV_per_atom" in ENERGY_RECORD_FIELDS


def test_formation_proxy_names_and_units_are_explicit():
    item = EnergyInput(
        structure_id="s1",
        structure=object(),
        n_atoms=3,
        composition={"Fe": 1, "O": 2},
    )
    proxy = formation_energy_proxy(
        total_energy_eV=-10.0,
        composition=item.composition,
        isolated_atom_reference_eV={"Fe": -1.0, "O": -2.0},
    )
    proxy_per_atom = formation_energy_proxy_per_atom(
        formation_energy_proxy_eV=proxy,
        n_atoms=item.n_atoms,
    )

    assert proxy == -5.0
    assert proxy_per_atom == -5.0 / 3.0
    assert positive_formation_energy_proxy(proxy_per_atom) == 0.0
