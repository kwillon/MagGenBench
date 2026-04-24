from __future__ import annotations

from pymatgen.core import Structure

from ..utils.config import PipelineConfig


def has_magnetic_elements(struct: Structure, cfg: PipelineConfig) -> bool:
    """
    Проверяет, содержит ли структура потенциально магнитные элементы.

    Магнитные элементы определяются списком cfg.magnetic_elements,
    который задаётся в thresholds.yaml.

    Примеры магнитных элементов:
        Fe, Co, Ni, Mn, Cr, V, редкоземельные элементы и др.

    Эта функция НЕ отклоняет структуру.
    Она используется только для вычисления метрики:

        magnetic_ratio

    которая показывает долю структур, содержащих магнитные элементы.

    Parameters
    ----------
    struct : Structure
        Структура pymatgen.

    cfg : PipelineConfig
        Конфигурация pipeline, содержащая список magnetic_elements.

    Returns
    -------
    bool
        True  → структура содержит магнитные элементы
        False → структура не содержит магнитных элементов
    """

    # множество элементов структуры
    elements = {site.specie.symbol for site in struct}

    # проверяем, есть ли пересечение с магнитными элементами
    return not elements.isdisjoint(cfg.magnetic_elements)
