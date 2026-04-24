"""
Utils module: базовые типы, конфигурация и константы pipeline.

Отвечает за:
    - определение структур данных (StructureItem, ValidationResult, Descriptors),
    - загрузку и хранение конфигурации pipeline (PipelineConfig, load_config),
    - определение стабильных enums и констант (ValidationStatus, RejectionReason),
    - обеспечение единого интерфейса для всех модулей pipeline.

Этот модуль является "ядром" проекта и используется всеми компонентами:
    io, validation, analysis, dedup, novelty, pipeline, report.

Публичный API:
    StructureItem
    Descriptors
    Rejection
    ValidationResult
    PipelineConfig
    DedupConfig
    load_config
    ValidationStatus
    GeometryQuality
    RejectionReason
    MAGNETIC_ELEMENTS_DEFAULT
"""

from .types import (
    StructureItem,
    Descriptors,
    Rejection,
    ValidationResult,
)

from .config import (
    PipelineConfig,
    DedupConfig,
    load_config,
)

from .constants import (
    ValidationStatus,
    GeometryQuality,
    RejectionReason,
    MAGNETIC_ELEMENTS_DEFAULT,
)

__all__ = [
    "StructureItem",
    "Descriptors",
    "Rejection",
    "ValidationResult",
    "PipelineConfig",
    "DedupConfig",
    "load_config",
    "ValidationStatus",
    "GeometryQuality",
    "RejectionReason",
    "MAGNETIC_ELEMENTS_DEFAULT",
]
