from __future__ import annotations

"""
Этот файл определяет основные структуры данных (dataclasses),
которые используются для передачи информации между модулями pipeline.

Использование dataclass вместо dict даёт:

    - type safety
    - автодополнение в IDE
    - читаемый код
    - предотвращение ошибок ключей
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .constants import RejectionReason, ValidationStatus


# =============================================================================
# Input structure descriptor
# =============================================================================


@dataclass(frozen=True)
class StructureItem:
    """
    Описывает входной CIF-файл.

    structure_id
        Уникальный ID структуры (относительный путь в input_dir).
        Пример:
            "subdir/Fe2O3_001.cif"

    path
        Абсолютный путь к файлу на диске.

    rel_path
        Относительный путь относительно input_dir.
        Используется для сохранения структуры в validated/rejected папках.
    """

    structure_id: str
    path: Path
    rel_path: Path


# =============================================================================
# Physical descriptors of structure
# =============================================================================


@dataclass(frozen=True)
class Descriptors:
    """
    Физические и структурные дескрипторы кристалла.

    Используются для:

        - validation_report.json
        - анализа генератора
        - novelty detection
        - deduplication

    n_atoms
        Число атомов в ячейке.

    density
        Плотность структуры (g/cm³).

    volume_per_atom
        Объём на атом (Å³/atom).

    reduced_formula
        Нормализованная химическая формула.
        Пример:
            Fe4O6 → Fe2O3

    spacegroup
        Номер spacegroup (1–230), или None если определить не удалось.
    """

    n_atoms: int
    density: float
    volume_per_atom: float
    reduced_formula: str
    spacegroup: Optional[int]


# =============================================================================
# Rejection descriptor
# =============================================================================


@dataclass(frozen=True)
class Rejection:
    """
    Описывает причину отклонения структуры.

    reason
        Код причины (Enum RejectionReason).

    details
        Дополнительная информация:
            - density
            - min_distance
            - n_atoms
            - error message
            и др.

        Используется для reason.json и debugging.
    """

    reason: RejectionReason
    details: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Final validation result
# =============================================================================


@dataclass(frozen=True)
class ValidationResult:
    """
    Финальный результат validation pipeline для одной структуры.

    status
        VALIDATED или REJECTED

    descriptors
        Физические дескрипторы (если структура валидна)

    rejection
        Причина отклонения (если структура отклонена)

    is_magnetic
        Содержит ли структура магнитные элементы.

    is_novel
        Является ли структура новой относительно train dataset.

    is_duplicate
        Является ли структура дубликатом другой структуры.

    is_suspicious
        Структура допустима, но имеет подозрительные параметры.
    """

    status: ValidationStatus

    descriptors: Optional[Descriptors] = None

    rejection: Optional[Rejection] = None

    is_magnetic: bool = False

    is_novel: Optional[bool] = None

    is_duplicate: bool = False

    is_suspicious: bool = False
