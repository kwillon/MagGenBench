from __future__ import annotations
import json
import shutil
from pathlib import Path
from ..utils.types import StructureItem, ValidationResult


def write_validated(item: StructureItem, out_dir: Path) -> Path:
    """
    Сохраняет валидированную структуру в validated_structures/.

    Структура директорий сохраняется такой же, как во входной директории,
    чтобы обеспечить воспроизводимость и удобную трассировку.

    Пример:

        input:
            samples/mattergen/subdir/A.cif

        output:
            outputs/mattergen/validated_structures/subdir/A.cif

    Parameters
    ----------
    item : StructureItem
        Описание структуры.

    out_dir : Path
        Корневая директория output.

    Returns
    -------
    Path
        Путь к сохранённому файлу.
    """

    dst = out_dir / "validated_structures" / item.rel_path

    # создаём директории, если их нет
    dst.parent.mkdir(parents=True, exist_ok=True)

    # копируем исходный CIF
    shutil.copy(item.path, dst)

    return dst


def write_rejected(
    item: StructureItem,
    out_dir: Path,
    result: ValidationResult,
) -> Path:
    """
    Сохраняет отклонённую структуру и файл причины отклонения.

    Создаёт:

        rejected_structures/<path>.cif
        rejected_structures/<path>.reason.json

    reason.json содержит:
    - structure_id
    - reason (код причины отклонения)
    - details (подробности проверки)

    Это необходимо для:
    - анализа ошибок генератора,
    - воспроизводимости результатов,
    - отладки pipeline.

    Parameters
    ----------
    item : StructureItem
        Описание структуры.

    out_dir : Path
        Корневая директория output.

    result : ValidationResult
        Результат валидации структуры.

    Returns
    -------
    Path
        Путь к сохранённому CIF-файлу.
    """

    dst = out_dir / "rejected_structures" / item.rel_path

    # создаём директории
    dst.parent.mkdir(parents=True, exist_ok=True)

    # копируем CIF
    shutil.copy(item.path, dst)

    # создаём reason.json рядом с CIF
    reason_path = dst.with_suffix(".reason.json")

    payload = {
        "structure_id": item.structure_id,
        "reason": result.rejection.reason if result.rejection else "unknown",
        "details": result.rejection.details if result.rejection else {},
    }

    reason_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
    )

    return dst
