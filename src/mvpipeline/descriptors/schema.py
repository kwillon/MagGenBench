from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


DESCRIPTOR_SCHEMA_VERSION = "v1"
DESCRIPTOR_SOURCE = "cif_recomputed"


class DescriptorStatus(str, Enum):
    OK = "ok"
    PARTIAL = "partial"
    ERROR = "error"


@dataclass(frozen=True)
class DescriptorInput:
    """Input contract for Descriptor v1 extraction."""

    sample_uid: str
    structure_id: str
    structure: Any
    model_name: str = ""
    model_short: str = ""
    run_uid: str = ""
    source_sample_id: str = ""
    cif_path: str = ""


@dataclass(frozen=True)
class DescriptorResult:
    """Descriptor v1 result before flattening to the CSV schema."""

    sample_uid: str
    structure_id: str
    status: DescriptorStatus
    model_name: str = ""
    model_short: str = ""
    run_uid: str = ""
    source_sample_id: str = ""
    cif_path: str = ""
    error_code: str = ""
    error_message: str = ""
    source: str = DESCRIPTOR_SOURCE
    schema_version: str = DESCRIPTOR_SCHEMA_VERSION
    values: Mapping[str, Any] = field(default_factory=dict)
