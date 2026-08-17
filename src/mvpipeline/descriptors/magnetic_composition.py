from __future__ import annotations

from typing import Any

from ..magnetism.config import MagneticElementGroups


def _fraction_and_species_count(
    amounts: dict[str, float],
    group: tuple[str, ...],
    total: float,
) -> tuple[float, int]:
    group_set = set(group)
    group_amount = sum(
        amount for element, amount in amounts.items() if element in group_set
    )
    species_count = sum(1 for element in amounts if element in group_set)
    fraction = group_amount / total if total > 0 else 0.0
    return fraction, species_count


def compute_magnetic_composition_descriptors(
    composition: Any,
    magnetic_elements: MagneticElementGroups,
) -> dict[str, Any]:
    amounts = {
        str(element): float(amount)
        for element, amount in composition.get_el_amt_dict().items()
    }
    total = sum(amounts.values())

    transition_fraction, n_transition = _fraction_and_species_count(
        amounts,
        magnetic_elements.transition_3d,
        total,
    )
    selected_fraction, n_selected = _fraction_and_species_count(
        amounts,
        magnetic_elements.selected_4d_5d,
        total,
    )
    lanthanide_fraction, n_lanthanide = _fraction_and_species_count(
        amounts,
        magnetic_elements.lanthanides,
        total,
    )

    return {
        "transition_3d_fraction": transition_fraction,
        "selected_4d_5d_fraction": selected_fraction,
        "configured_lanthanide_fraction": lanthanide_fraction,
        "n_transition_3d_species": n_transition,
        "n_selected_4d_5d_species": n_selected,
        "n_configured_lanthanide_species": n_lanthanide,
        "contains_3d_and_configured_lanthanide": (
            n_transition > 0 and n_lanthanide > 0
        ),
    }
