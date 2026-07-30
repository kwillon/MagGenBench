from __future__ import annotations

from dataclasses import dataclass

from ..formation import formation_energy_proxy, formation_energy_proxy_per_atom
from ..proxies import positive_formation_energy_proxy
from ..schema import EnergyInput, EnergyResult, EnergyStatus


@dataclass(frozen=True)
class FakeEnergyBackend:
    """Deterministic backend for local tests and pipeline wiring."""

    name: str = "fake"
    model_name: str = "deterministic-fake-v1"
    energy_per_atom_eV: float = -1.0
    isolated_atom_reference_eV: float = -0.25

    def predict(self, item: EnergyInput) -> EnergyResult:
        try:
            if item.n_atoms <= 0:
                raise ValueError("n_atoms must be positive")

            total = float(item.n_atoms) * self.energy_per_atom_eV
            refs = {
                element: self.isolated_atom_reference_eV
                for element in item.composition
            }
            form_proxy = formation_energy_proxy(
                total_energy_eV=total,
                composition=item.composition,
                isolated_atom_reference_eV=refs,
            )
            form_proxy_pa = formation_energy_proxy_per_atom(
                formation_energy_proxy_eV=form_proxy,
                n_atoms=item.n_atoms,
            )

            return EnergyResult(
                structure_id=item.structure_id,
                status=EnergyStatus.OK,
                backend=self.name,
                model_name=self.model_name,
                total_energy_eV=total,
                total_energy_eV_per_atom=total / float(item.n_atoms),
                formation_energy_proxy_eV=form_proxy,
                formation_energy_proxy_eV_per_atom=form_proxy_pa,
                stability_energy_proxy_eV_per_atom=positive_formation_energy_proxy(
                    form_proxy_pa
                ),
            )
        except Exception as exc:
            return EnergyResult(
                structure_id=item.structure_id,
                status=EnergyStatus.ERROR,
                error_code="fake_energy_error",
                error_message=str(exc),
                backend=self.name,
                model_name=self.model_name,
            )
