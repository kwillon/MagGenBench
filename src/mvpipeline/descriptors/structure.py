from __future__ import annotations

from typing import Any


def compute_unit_cell_descriptors(structure: Any) -> dict[str, Any]:
    """Compute Descriptor v1 unit-cell geometry fields."""

    n_atoms = len(structure)
    if n_atoms <= 0:
        raise ValueError("Structure contains no crystallographic sites")

    lattice = structure.lattice
    a, b, c = (float(value) for value in lattice.abc)
    alpha, beta, gamma = (float(value) for value in lattice.angles)

    min_length = min(a, b, c)
    max_length = max(a, b, c)
    if min_length <= 0:
        raise ValueError("Lattice lengths must be positive")

    volume = float(structure.volume)

    return {
        "n_atoms": n_atoms,
        "lattice_a": a,
        "lattice_b": b,
        "lattice_c": c,
        "lattice_alpha": alpha,
        "lattice_beta": beta,
        "lattice_gamma": gamma,
        "cell_volume": volume,
        "volume_per_atom": volume / float(n_atoms),
        "density": float(structure.density),
        "min_lattice_length": min_length,
        "max_lattice_length": max_length,
        "lattice_length_ratio": max_length / min_length,
    }


def compute_symmetry_descriptors(
    structure: Any,
    *,
    symprec: float = 0.01,
    angle_tolerance: float = 5.0,
) -> dict[str, Any]:
    """Compute Descriptor v1 symmetry fields without failing the full row."""

    try:
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

        analyzer = SpacegroupAnalyzer(
            structure,
            symprec=symprec,
            angle_tolerance=angle_tolerance,
        )
        return {
            "spacegroup_number": int(analyzer.get_space_group_number()),
            "spacegroup_symbol": str(analyzer.get_space_group_symbol()),
            "crystal_system": str(analyzer.get_crystal_system()),
            "point_group_symbol": str(analyzer.get_point_group_symbol()),
            "symmetry_status": "ok",
        }
    except Exception:
        return {
            "spacegroup_number": None,
            "spacegroup_symbol": None,
            "crystal_system": None,
            "point_group_symbol": None,
            "symmetry_status": "error",
        }
