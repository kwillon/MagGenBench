"""
mvpipeline — validation pipeline для кристаллических структур (CIF).

Этот пакет предоставляет полный pipeline для:

    - проверки корректности CIF,
    - физической и химической валидации,
    - удаления дубликатов,
    - проверки новизны относительно train dataset,
    - вычисления дескрипторов,
    - формирования validation_report.json.

Основная точка входа:
    run_validation — запускает validation pipeline.

Также экспортируются базовые типы и конфигурация для удобного использования в CLI
и других инструментах.

Пример использования:

    from mvpipeline import run_validation, load_config

    cfg = load_config("thresholds.yaml")

    run_validation(
        input_dir=Path("samples"),
        out_dir=Path("outputs"),
        cfg=cfg,
        train_reference=Path("train_reference.csv"),
    )
"""

# Pipeline runner (главная функция)
from .pipeline import run_validation

# Config
from .utils import PipelineConfig, DedupConfig, load_config

# Core types
from .utils import (
    StructureItem,
    Descriptors,
    Rejection,
    ValidationResult,
)

# Enums and constants
from .utils import (
    ValidationStatus,
    GeometryQuality,
    RejectionReason,
    MAGNETIC_ELEMENTS_DEFAULT,
)

__all__ = [
    # main entrypoint
    "run_validation",
    # config
    "PipelineConfig",
    "DedupConfig",
    "load_config",
    # types
    "StructureItem",
    "Descriptors",
    "Rejection",
    "ValidationResult",
    # enums
    "ValidationStatus",
    "GeometryQuality",
    "RejectionReason",
    # constants
    "MAGNETIC_ELEMENTS_DEFAULT",
]

# версия пакета
__version__ = "0.1.0"
