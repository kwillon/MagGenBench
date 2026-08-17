from __future__ import annotations

import math
from collections.abc import Collection
from typing import Any

from .magnetic_sites import configured_magnetic_site_indices


def compute_magnetic_symmetry_descriptors(
    structure: Any,
    *,
    configured_magnetic_elements: Collection[str],
    symprec: float = 0.01,
    angle_tolerance: float = 5.0,
) -> dict[str, Any]:
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    analyzer = SpacegroupAnalyzer(
        structure,
        symprec=symprec,
        angle_tolerance=angle_tolerance,
    )
    symmetrized = analyzer.get_symmetrized_structure()
    equivalent_indices = list(symmetrized.equivalent_indices)

    total_sites = len(structure)
    if total_sites <= 0:
        raise ValueError("Structure has no sites")

    magnetic_indices = set(
        configured_magnetic_site_indices(
            structure,
            configured_magnetic_elements,
        )
    )
    n_unique_sites = len(equivalent_indices)
    n_unique_magnetic_sites = sum(
        1 for group in equivalent_indices if magnetic_indices.intersection(group)
    )

    entropy = 0.0
    for group in equivalent_indices:
        probability = len(group) / total_sites
        if probability > 0:
            entropy -= probability * math.log(probability)

    return {
        "n_symmetry_unique_sites": n_unique_sites,
        "symmetry_unique_site_fraction": n_unique_sites / total_sites,
        "n_symmetry_unique_magnetic_sites": n_unique_magnetic_sites,
        "symmetry_unique_magnetic_site_fraction": (
            n_unique_magnetic_sites / len(magnetic_indices)
            if magnetic_indices
            else None
        ),
        "site_multiplicity_entropy": entropy,
        "magnetic_symmetry_status": "ok",
    }
