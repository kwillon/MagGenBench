"""General descriptor contracts.

This package is separate from validation descriptors and from model-specific
DXMag Magpie features. Heavy scientific dependencies must remain behind
implementation modules rather than being imported at package import time.
"""

from .schema import (
    DESCRIPTOR_SCHEMA_VERSION,
    DESCRIPTOR_SOURCE,
    DescriptorInput,
    DescriptorResult,
    DescriptorStatus,
)
from .extractor_v2 import extract_magnetic_descriptor_v2
from .schema_v2 import (
    DESCRIPTOR_V2_SCHEMA_VERSION,
    MAGNETIC_DESCRIPTOR_V2_SCIENTIFIC_FIELDS,
    MagneticDescriptorInput,
    MagneticDescriptorResult,
)

__all__ = [
    "DESCRIPTOR_SCHEMA_VERSION",
    "DESCRIPTOR_SOURCE",
    "DescriptorInput",
    "DescriptorResult",
    "DescriptorStatus",
    "DESCRIPTOR_V2_SCHEMA_VERSION",
    "MAGNETIC_DESCRIPTOR_V2_SCIENTIFIC_FIELDS",
    "MagneticDescriptorInput",
    "MagneticDescriptorResult",
    "extract_magnetic_descriptor_v2",
]
