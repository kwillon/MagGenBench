from __future__ import annotations
from pathlib import Path
from typing import List
from ..utils.types import StructureItem


def discover_cifs(input_dir: Path) -> List[StructureItem]:
    """
    Рекурсивно находит все CIF-файлы в директории input_dir и формирует список StructureItem.

    Эта функция отвечает за этап "discovery" pipeline — обнаружение всех входных структур,
    которые нужно валидировать.

    Для каждого файла создаётся StructureItem, содержащий:
    - structure_id — уникальный ID структуры (относительный путь),
    - path — абсолютный путь к файлу,
    - rel_path — относительный путь (используется для сохранения результатов).

    structure_id используется как уникальный идентификатор структуры
    во всех отчётах и reason.json.

    Пример:

        input_dir/
            subdir/
                A.cif

        → structure_id = "subdir/A.cif"

    Это гарантирует:
    - уникальность ID,
    - воспроизводимость,
    - сохранение структуры директорий в output.

    Parameters
    ----------
    input_dir : Path
        Корневая директория с CIF-файлами.

    Returns
    -------
    List[StructureItem]
        Список найденных структур, отсортированный по пути для воспроизводимости.
    """

    # Рекурсивно находим все *.cif
    files = sorted(input_dir.rglob("*.cif"))

    items: List[StructureItem] = []

    for f in files:

        # относительный путь используется как уникальный ID структуры
        rel = f.relative_to(input_dir)

        # нормализуем путь (важно для Windows/Linux совместимости)
        structure_id = str(rel).replace("\\", "/")

        items.append(
            StructureItem(
                structure_id=structure_id,
                path=f,
                rel_path=rel,
            )
        )

    return items
