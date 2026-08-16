from __future__ import annotations

import math
from typing import Any


def _error_result() -> dict[str, Any]:
    return {
        "nearest_neighbor_min": None,
        "nearest_neighbor_mean": None,
        "nearest_neighbor_std": None,
        "coordination_mean": None,
        "coordination_min": None,
        "coordination_max": None,
        "coordination_std": None,
        "local_geometry_status": "error",
    }


def compute_local_geometry_descriptors(
    structure: Any,
    *,
    cutoff: float = 10.0,
    tolerance: float = 0.1,
    get_all_sites: bool = False,
) -> dict[str, Any]:
    """Compute Descriptor v1 nearest-neighbor and coordination statistics.

    Neighbor searches use periodic boundary conditions through pymatgen.
    Nearest-neighbor statistics are aggregated from the nearest nonzero
    periodic neighbor of each crystallographic site. Coordination numbers
    use MinimumDistanceNN with the Descriptor v1 runtime parameters.
    """

    try:
        from pymatgen.core.local_env import MinimumDistanceNN

        if len(structure) <= 0:
            return _error_result()

        if cutoff <= 0:
            return _error_result()

        nearest_distances: list[float] = []

        for site in structure:
            neighbors = structure.get_neighbors(site, cutoff)
            distances = [
                float(neighbor.nn_distance)
                for neighbor in neighbors
                if math.isfinite(float(neighbor.nn_distance))
                and float(neighbor.nn_distance) > 1e-12
            ]

            if not distances:
                return _error_result()

            nearest_distances.append(min(distances))

        nn = MinimumDistanceNN(
            tol=tolerance,
            cutoff=cutoff,
            get_all_sites=get_all_sites,
        )

        coordination_numbers = [
            float(
                nn.get_cn(
                    structure,
                    index,
                    use_weights=False,
                )
            )
            for index in range(len(structure))
        ]

        if not coordination_numbers:
            return _error_result()

        if not all(math.isfinite(value) for value in coordination_numbers):
            return _error_result()

        nearest_mean = sum(nearest_distances) / len(nearest_distances)
        nearest_variance = sum(
            (value - nearest_mean) ** 2
            for value in nearest_distances
        ) / len(nearest_distances)

        coordination_mean = (
            sum(coordination_numbers) / len(coordination_numbers)
        )
        coordination_variance = sum(
            (value - coordination_mean) ** 2
            for value in coordination_numbers
        ) / len(coordination_numbers)

        return {
            "nearest_neighbor_min": min(nearest_distances),
            "nearest_neighbor_mean": nearest_mean,
            "nearest_neighbor_std": math.sqrt(nearest_variance),
            "coordination_mean": coordination_mean,
            "coordination_min": min(coordination_numbers),
            "coordination_max": max(coordination_numbers),
            "coordination_std": math.sqrt(coordination_variance),
            "local_geometry_status": "ok",
        }
    except Exception:
        return _error_result()
