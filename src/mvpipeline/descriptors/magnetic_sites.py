from __future__ import annotations

from collections.abc import Collection
from typing import Any


def site_element_symbols(site: Any) -> frozenset[str]:
    species = getattr(site, "species", None)
    if species is None:
        return frozenset()
    return frozenset(
        str(getattr(element, "symbol", element))
        for element in species
    )


def is_configured_magnetic_site(
    site: Any,
    configured_magnetic_elements: Collection[str],
) -> bool:
    magnetic = frozenset(configured_magnetic_elements)
    return bool(site_element_symbols(site).intersection(magnetic))


def configured_magnetic_site_indices(
    structure: Any,
    configured_magnetic_elements: Collection[str],
) -> list[int]:
    return [
        index
        for index, site in enumerate(structure)
        if is_configured_magnetic_site(site, configured_magnetic_elements)
    ]
