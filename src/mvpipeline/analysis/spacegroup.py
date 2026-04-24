from __future__ import annotations

from typing import Optional

from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


def get_spacegroup_number(struct: Structure, symprec: float) -> Optional[int]:
    """
    Определяет номер пространственной группы (spacegroup) кристаллической структуры.

    Spacegroup — это числовой идентификатор симметрии кристалла (от 1 до 230),
    который описывает, как структура повторяется в пространстве. Это одна из
    ключевых характеристик кристалла и используется для:

    - проверки новизны относительно train dataset
    - дедупликации структур
    - анализа симметрии сгенерированных кристаллов
    - формирования validation_report.json

    Функция использует SpacegroupAnalyzer из pymatgen, который анализирует
    симметрию структуры с заданной точностью symprec.

    Parameters
    ----------
    struct : Structure
        Объект pymatgen Structure, представляющий кристалл.

    symprec : float
        Допуск (Å) для определения симметрии.
        Определяет, насколько близко атомы должны совпадать для обнаружения симметрии.
        Типичные значения:
            0.01  — стандартное значение
            0.001 — более строгое
            0.1   — более мягкое

    Returns
    -------
    Optional[int]
        Номер пространственной группы (1–230), если удалось определить.

        None возвращается если:
        - структура имеет слишком сильные искажения,
        - структура повреждена,
        - симметрия не может быть надёжно определена,
        - возникла внутренняя ошибка pymatgen/spglib.

    Notes
    -----
    Возврат None не является критической ошибкой pipeline.
    В этом случае структура может всё ещё быть валидной, но некоторые проверки,
    такие как novelty или дедупликация, будут менее точными.
    """
    try:
        sga = SpacegroupAnalyzer(struct, symprec=symprec)
        return int(sga.get_space_group_number())

    except Exception:
        # Если симметрию определить не удалось, возвращаем None
        # вместо того чтобы прерывать весь pipeline
        return None
