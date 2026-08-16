from __future__ import annotations

import math
import warnings
from typing import Any


ELEMENT_PROPERTY_NAMES = (
    "atomic_number",
    "atomic_mass",
    "atomic_radius",
    "electronegativity",
    "periodic_row",
    "periodic_group",
)


def _finite_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(numeric):
        return None

    return numeric


def _element_property_value(element: Any, property_name: str) -> float | None:
    if property_name == "atomic_number":
        value = element.Z
    elif property_name == "atomic_mass":
        value = element.atomic_mass
    elif property_name == "atomic_radius":
        value = element.atomic_radius
    elif property_name == "electronegativity":
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"No Pauling electronegativity for .*",
                category=UserWarning,
            )
            value = element.X
    elif property_name == "periodic_row":
        value = element.row
    elif property_name == "periodic_group":
        value = element.group
    else:
        raise ValueError(f"Unsupported element property: {property_name}")

    return _finite_float(value)


def compute_element_property_descriptors(
    composition: Any,
) -> dict[str, Any]:
    """Compute Descriptor v1 composition-weighted elemental statistics.

    Means and population standard deviations use atomic fractions.
    Minima, maxima, and ranges are evaluated over distinct present elements.
    If a property has incomplete coverage, its five statistics are returned
    as missing rather than renormalizing the available elemental fractions.
    """

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

    result: dict[str, Any] = {}

    for property_name in ELEMENT_PROPERTY_NAMES:
        available: list[tuple[float, float]] = []

        for symbol, fraction in fractions.items():
            value = _element_property_value(
                Element(symbol),
                property_name,
            )
            if value is not None:
                available.append((fraction, value))

        coverage = sum(fraction for fraction, _ in available)
        result[f"{property_name}_coverage"] = coverage

        if not math.isclose(
            coverage,
            1.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            result[f"{property_name}_mean"] = None
            result[f"{property_name}_min"] = None
            result[f"{property_name}_max"] = None
            result[f"{property_name}_range"] = None
            result[f"{property_name}_std"] = None
            continue

        mean = sum(
            fraction * value
            for fraction, value in available
        )
        values = [value for _, value in available]
        minimum = min(values)
        maximum = max(values)
        variance = sum(
            fraction * (value - mean) ** 2
            for fraction, value in available
        )

        result[f"{property_name}_mean"] = mean
        result[f"{property_name}_min"] = minimum
        result[f"{property_name}_max"] = maximum
        result[f"{property_name}_range"] = maximum - minimum
        result[f"{property_name}_std"] = math.sqrt(variance)

    return result
