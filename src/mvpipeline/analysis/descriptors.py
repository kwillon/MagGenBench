from __future__ import annotations
from pymatgen.core import Structure
from ..utils.types import Descriptors
from typing import Optional


def compute_basic_descriptors(
    struct: Structure, spacegroup: Optional[int]
) -> Descriptors:
    """
    Вычисляет базовые физические и структурные дескрипторы кристалла.

    Эта функция извлекает ключевые характеристики структуры, которые используются:
    - для формирования validation_report.json,
    - для анализа качества генеративных моделей,
    - для дедупликации и проверки новизны.

    Вычисляемые дескрипторы:

    n_atoms
        Число атомов в элементарной ячейке структуры.

    density
        Плотность кристалла в g/cm³.
        Рассчитывается pymatgen на основе состава и объёма ячейки.

    volume_per_atom
        Объём, приходящийся на один атом (Å³/atom).
        Используется для проверки реалистичности упаковки атомов.

    reduced_formula
        Приведённая химическая формула (например Fe4O6 → Fe2O3).
        Используется для:
        - дедупликации
        - проверки новизны относительно train dataset
        - статистики по составам

    spacegroup
        Номер пространственной группы (симметрия кристалла), если доступен.
        Используется для:
        - проверки новизны
        - дедупликации
        - анализа симметрии сгенерированных структур

    Parameters
    ----------
    struct : Structure
        Объект структуры pymatgen, представляющий кристалл.

    spacegroup : Optional[int]
        Номер пространственной группы, полученный через SpacegroupAnalyzer.
        Может быть None, если определить симметрию не удалось.

    Returns
    -------
    Descriptors
        Dataclass с вычисленными дескрипторами структуры.
    """
    n_atoms = len(struct)

    # объём на атом (Å³/atom)
    # используется для проверки реалистичности структуры
    vpa = struct.volume / n_atoms if n_atoms else 0.0

    # плотность (g/cm³)
    # pymatgen вычисляет автоматически на основе атомных масс и объёма
    dens = float(struct.density)

    # приведённая формула (например Fe4O6 → Fe2O3)
    formula = struct.composition.reduced_formula

    return Descriptors(
        n_atoms=n_atoms,
        density=dens,
        volume_per_atom=vpa,
        reduced_formula=formula,
        spacegroup=spacegroup,
    )
