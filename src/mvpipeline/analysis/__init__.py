"""
Analysis module: вычисление дескрипторов и симметрийных свойств структур.

Этот пакет отвечает за извлечение характеристик структуры, которые используются
в validation pipeline для:

- формирования validation_report.json
- дедупликации
- проверки новизны
- анализа качества генеративных моделей

Публичный API:
    compute_basic_descriptors  — вычисление базовых физических дескрипторов
    get_spacegroup_number      — определение номера пространственной группы
"""

__all__ = [
    "compute_basic_descriptors",
    "get_spacegroup_number",
]

_LAZY_EXPORTS = {
    "compute_basic_descriptors": (
        "mvpipeline.analysis.descriptors",
        "compute_basic_descriptors",
    ),
    "get_spacegroup_number": (
        "mvpipeline.analysis.spacegroup",
        "get_spacegroup_number",
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
