"""General Descriptor v1 contracts.

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

__all__ = [
    "DESCRIPTOR_SCHEMA_VERSION",
    "DESCRIPTOR_SOURCE",
    "DescriptorInput",
    "DescriptorResult",
    "DescriptorStatus",
]
