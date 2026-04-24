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

from .descriptors import compute_basic_descriptors
from .spacegroup import get_spacegroup_number

__all__ = [
    "compute_basic_descriptors",
    "get_spacegroup_number",
]
