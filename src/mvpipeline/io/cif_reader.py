from __future__ import annotations
from pathlib import Path
import warnings
from pymatgen.core import Structure


def read_structure(path: Path) -> Structure:
    """
    Читает CIF-файл и возвращает объект pymatgen Structure.

    Это основной входной шаг pipeline, который преобразует файл структуры
    на диске в объект, с которым можно работать программно.

    Structure содержит:
    - атомы и их координаты,
    - параметры решётки,
    - состав,
    - плотность,
    - объём,
    - методы для вычисления расстояний, симметрии и других свойств.

    Parameters
    ----------
    path : Path
        Путь к CIF-файлу.

    Returns
    -------
    Structure
        Объект структуры pymatgen.

    Raises
    ------
    Exception
        Если файл повреждён или не является корректным CIF.
        Ошибка должна обрабатываться на уровне pipeline.runner,
        где структура будет помечена как rejected с причиной cif_parse_error.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r".*fractional coordinates rounded to ideal values.*",
            category=UserWarning,
        )
        return Structure.from_file(path)
