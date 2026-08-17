from __future__ import annotations

import math
from collections.abc import Collection
from typing import Any

from .magnetic_sites import (
    configured_magnetic_site_indices,
    is_configured_magnetic_site,
)


MAGNETIC_GEOMETRY_FIELDS = (
    "magnetic_site_nearest_neighbor_distance_min",
    "magnetic_site_nearest_neighbor_distance_mean",
    "magnetic_site_nearest_neighbor_distance_std",
    "magnetic_site_nearest_magnetic_neighbor_distance_min",
    "magnetic_site_nearest_magnetic_neighbor_distance_mean",
    "magnetic_site_nearest_magnetic_neighbor_distance_std",
    "magnetic_site_coordination_mean",
    "magnetic_site_coordination_std",
    "magnetic_site_magnetic_coordination_mean",
    "magnetic_site_magnetic_coordination_std",
    "magnetic_site_magnetic_neighbor_fraction_mean",
    "magnetic_site_magnetic_neighbor_fraction_std",
)


def _empty_geometry(status: str) -> dict[str, Any]:
    values = {field: None for field in MAGNETIC_GEOMETRY_FIELDS}
    values["magnetic_geometry_status"] = status
    return values


def _mean_std(values: list[float]) -> tuple[float, float]:
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return mean, math.sqrt(variance)


def _neighbor_site_is_magnetic(
    structure: Any,
    neighbor: Any,
    configured_magnetic_elements: Collection[str],
) -> bool:
    index = getattr(neighbor, "index", None)
    if index is not None:
        try:
            return is_configured_magnetic_site(
                structure[int(index)],
                configured_magnetic_elements,
            )
        except Exception:
            pass
    return is_configured_magnetic_site(neighbor, configured_magnetic_elements)


def compute_magnetic_geometry_descriptors(
    structure: Any,
    *,
    configured_magnetic_elements: Collection[str],
    cutoff: float = 10.0,
    tolerance: float = 0.1,
    get_all_sites: bool = False,
) -> dict[str, Any]:
    from pymatgen.core.local_env import MinimumDistanceNN

    magnetic_indices = configured_magnetic_site_indices(
        structure,
        configured_magnetic_elements,
    )
    if not magnetic_indices:
        return _empty_geometry("not_applicable")

    nearest_any: list[float] = []
    nearest_magnetic: list[float] = []

    for index in magnetic_indices:
        site = structure[index]
        neighbors = structure.get_neighbors(site, cutoff)
        distances = [
            float(neighbor.nn_distance)
            for neighbor in neighbors
            if math.isfinite(float(neighbor.nn_distance))
            and float(neighbor.nn_distance) > 1e-12
        ]
        magnetic_distances = [
            float(neighbor.nn_distance)
            for neighbor in neighbors
            if math.isfinite(float(neighbor.nn_distance))
            and float(neighbor.nn_distance) > 1e-12
            and _neighbor_site_is_magnetic(
                structure,
                neighbor,
                configured_magnetic_elements,
            )
        ]

        if not distances or not magnetic_distances:
            return _empty_geometry("error")

        nearest_any.append(min(distances))
        nearest_magnetic.append(min(magnetic_distances))

    nn = MinimumDistanceNN(
        tol=tolerance,
        cutoff=cutoff,
        get_all_sites=get_all_sites,
    )

    coordination: list[float] = []
    magnetic_coordination: list[float] = []
    magnetic_neighbor_fraction: list[float] = []

    for index in magnetic_indices:
        total_coordination = float(
            nn.get_cn(
                structure,
                index,
                use_weights=False,
            )
        )
        if not math.isfinite(total_coordination):
            return _empty_geometry("error")

        info = nn.get_nn_info(structure, index)
        magnetic_count = 0.0
        for neighbor in info:
            neighbor_index = neighbor.get("site_index")
            if neighbor_index is not None and is_configured_magnetic_site(
                structure[int(neighbor_index)],
                configured_magnetic_elements,
            ):
                magnetic_count += 1.0

        coordination.append(total_coordination)
        magnetic_coordination.append(magnetic_count)
        if total_coordination > 0:
            magnetic_neighbor_fraction.append(
                magnetic_count / total_coordination
            )
        else:
            magnetic_neighbor_fraction.append(0.0)

    nearest_any_mean, nearest_any_std = _mean_std(nearest_any)
    nearest_mag_mean, nearest_mag_std = _mean_std(nearest_magnetic)
    coordination_mean, coordination_std = _mean_std(coordination)
    magnetic_coordination_mean, magnetic_coordination_std = _mean_std(
        magnetic_coordination
    )
    fraction_mean, fraction_std = _mean_std(magnetic_neighbor_fraction)

    return {
        "magnetic_site_nearest_neighbor_distance_min": min(nearest_any),
        "magnetic_site_nearest_neighbor_distance_mean": nearest_any_mean,
        "magnetic_site_nearest_neighbor_distance_std": nearest_any_std,
        "magnetic_site_nearest_magnetic_neighbor_distance_min": min(
            nearest_magnetic
        ),
        "magnetic_site_nearest_magnetic_neighbor_distance_mean": nearest_mag_mean,
        "magnetic_site_nearest_magnetic_neighbor_distance_std": nearest_mag_std,
        "magnetic_site_coordination_mean": coordination_mean,
        "magnetic_site_coordination_std": coordination_std,
        "magnetic_site_magnetic_coordination_mean": magnetic_coordination_mean,
        "magnetic_site_magnetic_coordination_std": magnetic_coordination_std,
        "magnetic_site_magnetic_neighbor_fraction_mean": fraction_mean,
        "magnetic_site_magnetic_neighbor_fraction_std": fraction_std,
        "magnetic_geometry_status": "ok",
    }
