from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

from .schema import EnergyResult


ENERGY_RECORD_FIELDS = [
    "structure_id",
    "status",
    "error_code",
    "error_message",
    "backend",
    "model_name",
    "energy_unit",
    "total_energy_eV",
    "total_energy_eV_per_atom",
    "formation_energy_proxy_eV",
    "formation_energy_proxy_eV_per_atom",
    "stability_energy_proxy_eV_per_atom",
    "details",
]


def energy_result_to_record(result: EnergyResult) -> Dict[str, Any]:
    record = asdict(result)
    record["status"] = result.status.value
    return record
