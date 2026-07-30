from __future__ import annotations


def positive_formation_energy_proxy(formation_energy_proxy_eV_per_atom: float) -> float:
    """Return max(proxy formation energy per atom, 0).

    This is a stability proxy only. It must not be labeled as e_above_hull.
    """

    return max(0.0, float(formation_energy_proxy_eV_per_atom))
