from __future__ import annotations

from typing import Mapping


def formation_energy_proxy(
    *,
    total_energy_eV: float,
    composition: Mapping[str, float],
    isolated_atom_reference_eV: Mapping[str, float],
) -> float:
    """Compute an isolated-atom-reference formation-energy proxy in eV."""

    ref_sum = 0.0
    for element, amount in composition.items():
        ref_sum += float(amount) * float(isolated_atom_reference_eV[element])
    return float(total_energy_eV) - ref_sum


def formation_energy_proxy_per_atom(
    *, formation_energy_proxy_eV: float, n_atoms: int
) -> float:
    if n_atoms <= 0:
        raise ValueError("n_atoms must be positive")
    return float(formation_energy_proxy_eV) / float(n_atoms)
