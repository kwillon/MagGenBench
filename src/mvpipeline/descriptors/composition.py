from __future__ import annotations

import math
from collections.abc import Collection
from typing import Any


def compute_composition_descriptors(
    composition: Any,
    *,
    magnetic_screening_elements: Collection[str],
) -> dict[str, Any]:
    """Compute Descriptor v1 composition and periodic-category fields."""

    from pymatgen.core import Element

    amounts = {
        str(symbol): float(amount)
        for symbol, amount in composition.get_el_amt_dict().items()
        if float(amount) > 0
    }

    if not amounts:
        raise ValueError("Composition contains no positive elemental amounts")

    total = sum(amounts.values())
    if total <= 0:
        raise ValueError("Composition total amount must be positive")

    fractions = {
        symbol: amount / total
        for symbol, amount in amounts.items()
    }

    elements = {
        symbol: Element(symbol)
        for symbol in fractions
    }

    entropy = -sum(
        fraction * math.log(fraction)
        for fraction in fractions.values()
    )

    magnetic_set = frozenset(str(x) for x in magnetic_screening_elements)

    return {
        "n_elements": len(fractions),
        "min_element_fraction": min(fractions.values()),
        "max_element_fraction": max(fractions.values()),
        "composition_entropy": entropy,
        "transition_metal_fraction": sum(
            fractions[symbol]
            for symbol, element in elements.items()
            if element.is_transition_metal
        ),
        "d_block_fraction": sum(
            fractions[symbol]
            for symbol, element in elements.items()
            if element.block == "d"
        ),
        "f_block_fraction": sum(
            fractions[symbol]
            for symbol, element in elements.items()
            if element.block == "f"
        ),
        "lanthanide_fraction": sum(
            fractions[symbol]
            for symbol, element in elements.items()
            if element.is_lanthanoid
        ),
        "actinide_fraction": sum(
            fractions[symbol]
            for symbol, element in elements.items()
            if element.is_actinoid
        ),
        "magnetic_screening_element_fraction": sum(
            fractions[symbol]
            for symbol in fractions
            if symbol in magnetic_set
        ),
    }
