from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Union

import yaml


@dataclass(frozen=True)
class DedupConfig:
    """
    Конфигурация дедупликации структур.

    Эти параметры используются pymatgen StructureMatcher и определяют,
    насколько "похожими" должны быть структуры, чтобы считаться одинаковыми.

    ltol (lattice tolerance)
        Допуск различия параметров решётки.
        Например, 0.2 означает допустимое отклонение до 20%.

    stol (site tolerance)
        Допуск различия координат атомов (в долях решётки).

    angle_tol (angle tolerance)
        Допуск различия углов решётки (в градусах).

    Более строгие значения → меньше ложных совпадений,
    более мягкие → больше совпадений (но выше риск false positives).
    """

    ltol: float = 0.2
    stol: float = 0.3
    angle_tol: float = 5.0


@dataclass(frozen=True)
class PipelineConfig:
    """
    Главная конфигурация validation pipeline.

    Содержит все пороговые значения и параметры,
    используемые во всех этапах pipeline.

    Эти значения обычно загружаются из thresholds.yaml.
    """

    # -----------------------
    # Geometry thresholds
    # -----------------------

    # минимально допустимое расстояние между атомами (Å)
    # меньше → физически невозможная структура
    d_min_reject: float = 0.7

    # порог suspicious расстояния
    d_max_suspicious: float = 1.2

    # минимальный объём на атом (Å³/atom)
    vol_min: float = 8.0

    # максимальный объём на атом (Å³/atom)
    vol_max: float = 40.0

    # -----------------------
    # Physical properties
    # -----------------------

    # минимально допустимая плотность (g/cm³)
    min_density: float = 0.5

    # максимально допустимая плотность (g/cm³)
    max_density: float = 30.0

    # -----------------------
    # System limits
    # -----------------------

    # максимальное число атомов в структуре
    max_n_atoms: int = 500

    # -----------------------
    # Chemistry
    # -----------------------

    # допустимые степени окисления для элементов
    #
    # пример:
    # {
    #   "Fe": [2, 3],
    #   "O": [-2]
    # }
    oxidation_states: Dict[str, List[int]] = None

    # список магнитных элементов
    #
    # используется только для статистики magnetic_ratio
    magnetic_elements: Set[str] = None

    # -----------------------
    # Behavior flags
    # -----------------------

    # отклонять ли suspicious структуры
    # False → принимать, но помечать
    reject_suspicious: bool = False

    # -----------------------
    # Symmetry detection
    # -----------------------

    # точность определения симметрии (Å)
    symprec: float = 0.01

    # -----------------------
    # Deduplication config
    # -----------------------

    dedup: DedupConfig = DedupConfig()


# тип пути (для удобства typing)
PathLike = Union[str, Path]


def load_config(path: PathLike) -> PipelineConfig:
    """
    Загружает конфигурацию pipeline из YAML-файла.

    Этот файл (обычно thresholds.yaml) содержит все пороговые значения,
    используемые validation pipeline.

    Пример thresholds.yaml:

        geometry:
            d_min_reject: 0.7

        physical_properties:
            min_density: 0.5

        oxidation_states:
            Fe: [2, 3]

        magnetic_elements:
            - Fe
            - Co

    Parameters
    ----------
    path : PathLike
        Путь к YAML-файлу конфигурации.

    Returns
    -------
    PipelineConfig
        Объект конфигурации pipeline.
    """

    p = Path(path)

    # читаем YAML
    with p.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # -----------------------
    # sections
    # -----------------------

    geo = cfg.get("geometry", {}) or {}
    phys = cfg.get("physical_properties", {}) or {}
    sys_lim = cfg.get("system_limits", {}) or {}

    # -----------------------
    # oxidation states
    # -----------------------

    ox = cfg.get("oxidation_states", {}) or {}

    # нормализуем типы → Dict[str, List[int]]
    ox_norm: Dict[str, List[int]] = {}

    for el, states in ox.items():

        if isinstance(states, list):
            ox_norm[str(el)] = [int(x) for x in states]

        else:
            ox_norm[str(el)] = [int(states)]

    # -----------------------
    # magnetic elements
    # -----------------------

    mag_list = cfg.get("magnetic_elements", []) or []

    mag_set: Set[str] = {str(x) for x in mag_list}

    # -----------------------
    # optional flags
    # -----------------------

    reject_suspicious = bool(cfg.get("reject_suspicious", False))

    symprec = float(cfg.get("symprec", 0.01))

    # -----------------------
    # build config object
    # -----------------------

    return PipelineConfig(
        # geometry
        d_min_reject=float(geo.get("d_min_reject", 0.7)),
        d_max_suspicious=float(geo.get("d_max_suspicious", 1.2)),
        vol_min=float(geo.get("vol_min", 8.0)),
        vol_max=float(geo.get("vol_max", 40.0)),
        # physical
        min_density=float(phys.get("min_density", 0.5)),
        max_density=float(phys.get("max_density", 30.0)),
        # system
        max_n_atoms=int(sys_lim.get("max_n_atoms", 500)),
        # chemistry
        oxidation_states=ox_norm,
        magnetic_elements=mag_set,
        # flags
        reject_suspicious=reject_suspicious,
        # symmetry
        symprec=symprec,
    )
