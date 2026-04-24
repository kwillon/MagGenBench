"""
Validation module: проверки корректности кристаллических структур.

Этот пакет содержит все проверки, которые могут отклонить структуру
или пометить её как suspicious.

Проверки выполняются последовательно в pipeline.runner:

    1. sanity_ok
        Быстрая базовая проверка корректности структуры.

    2. geometry_validate
        Проверка геометрических и физических ограничений:
        - минимальные расстояния между атомами
        - плотность
        - объём на атом
        - максимальное число атомов

    3. check_charge_neutrality
        Проверка электронейтральности структуры на основе oxidation_states.

    4. has_magnetic_elements
        Проверка наличия магнитных элементов (используется для метрик,
        не для отклонения структуры).

Публичный API:
    sanity_ok
    geometry_validate
    GeometryOutcome
    check_charge_neutrality
    ChargeCheckResult
    has_magnetic_elements
"""

from .cif_sanity import sanity_ok
from .geometry import geometry_validate, GeometryOutcome
from .chemistry import check_charge_neutrality, ChargeCheckResult
from .magnetism import has_magnetic_elements

__all__ = [
    # sanity
    "sanity_ok",
    # geometry
    "geometry_validate",
    "GeometryOutcome",
    # chemistry
    "check_charge_neutrality",
    "ChargeCheckResult",
    # magnetism
    "has_magnetic_elements",
]
