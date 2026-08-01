from __future__ import annotations

from typing import Any


VALID_OUTPUT_SEMANTICS = {"total_energy_eV", "energy_per_atom_eV"}


def scalar_to_float(value: Any) -> float:
    if value is None:
        raise ValueError("Model returned empty energy")
    if hasattr(value, "item"):
        try:
            return float(value.item())
        except (TypeError, ValueError) as exc:
            raise ValueError("Model energy output is not a scalar") from exc
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Model energy output is not a scalar") from exc


def normalize_energy(value: Any, semantics: str, n_atoms: int) -> tuple[float, float]:
    if n_atoms <= 0:
        raise ValueError("n_atoms must be positive")
    if semantics not in VALID_OUTPUT_SEMANTICS:
        raise ValueError(f"Unsupported energy output semantics: {semantics}")

    raw = scalar_to_float(value)
    if semantics == "total_energy_eV":
        total = raw
        per_atom = raw / float(n_atoms)
    else:
        per_atom = raw
        total = raw * float(n_atoms)
    return total, per_atom
