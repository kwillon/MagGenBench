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
def run_validation(*args, **kwargs):
    """Lazily run the validation pipeline.

    Importing mvpipeline should stay dependency-light for contract modules.
    The real pipeline import happens on call, so missing pymatgen still raises
    the original ImportError in environments that try to run validation.
    """

    from .pipeline import run_validation as _run_validation

    return _run_validation(*args, **kwargs)

_LAZY_EXPORTS = {
    "PipelineConfig": ("mvpipeline.utils.config", "PipelineConfig"),
    "DedupConfig": ("mvpipeline.utils.config", "DedupConfig"),
    "load_config": ("mvpipeline.utils.config", "load_config"),
    "StructureItem": ("mvpipeline.utils.types", "StructureItem"),
    "Descriptors": ("mvpipeline.utils.types", "Descriptors"),
    "Rejection": ("mvpipeline.utils.types", "Rejection"),
    "ValidationResult": ("mvpipeline.utils.types", "ValidationResult"),
    "ValidationStatus": ("mvpipeline.utils.constants", "ValidationStatus"),
    "GeometryQuality": ("mvpipeline.utils.constants", "GeometryQuality"),
    "RejectionReason": ("mvpipeline.utils.constants", "RejectionReason"),
    "MAGNETIC_ELEMENTS_DEFAULT": (
        "mvpipeline.utils.constants",
        "MAGNETIC_ELEMENTS_DEFAULT",
    ),
}


def __getattr__(name):
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _LAZY_EXPORTS[name]
    from importlib import import_module

    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value

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
