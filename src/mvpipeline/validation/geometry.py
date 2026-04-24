from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Dict
import numpy as np
from pymatgen.core import Structure

from ..utils.config import PipelineConfig
from ..utils.constants import RejectionReason, ValidationStatus


@dataclass(frozen=True)
class GeometryOutcome:
    """
    Результат геометрической проверки структуры.

    status
        VALIDATED — структура прошла геометрическую проверку
        REJECTED  — структура отклонена

    is_suspicious
        True  — структура прошла проверку, но имеет подозрительные характеристики
        False — структура выглядит физически нормальной

        Suspicious структуры не отклоняются, но учитываются отдельно
        для анализа качества генератора.

    reason
        Код причины отклонения (если status == REJECTED).

    details
        Подробные численные значения параметров структуры:
            - n_atoms
            - density
            - volume_per_atom
            - min_distance

        Используется для:
            - reason.json
            - validation_report.json
            - анализа ошибок генератора
    """

    status: ValidationStatus
    is_suspicious: bool
    reason: Optional[RejectionReason]
    details: Dict[str, Any]


def geometry_validate(struct: Structure, cfg: PipelineConfig) -> GeometryOutcome:
    """
    Выполняет геометрическую и физическую валидацию структуры.

    Проверяемые условия:

    1. Ограничение на число атомов
        Защищает pipeline от слишком больших или повреждённых структур.

    2. Минимальное расстояние между атомами (min_distance)
        Если атомы находятся слишком близко → структура физически невозможна.

    3. Плотность структуры (density)
        Нереалистично высокая или низкая плотность указывает на ошибку генерации.

    4. Объём на атом (volume_per_atom)
        Используется для выявления неестественной упаковки атомов.

    Структура может быть:

        VALIDATED
            структура физически допустима

        VALIDATED + suspicious=True
            структура допустима, но имеет подозрительные параметры

        REJECTED
            структура физически невозможна

    Parameters
    ----------
    struct : Structure
        Структура pymatgen.

    cfg : PipelineConfig
        Конфигурация pipeline с пороговыми значениями.

    Returns
    -------
    GeometryOutcome
        Результат проверки структуры.
    """

    # число атомов в ячейке
    n_atoms = len(struct)

    # защита от слишком больших структур
    if n_atoms > cfg.max_n_atoms:
        return GeometryOutcome(
            status=ValidationStatus.REJECTED,
            is_suspicious=False,
            reason=RejectionReason.TOO_MANY_ATOMS,
            details={
                "n_atoms": n_atoms,
                "max_n_atoms": cfg.max_n_atoms,
            },
        )

    # плотность (g/cm³)
    dens = float(struct.density)

    # объём на атом (Å³/atom)
    vpa = struct.volume / n_atoms if n_atoms else 0.0

    # матрица расстояний между всеми парами атомов
    dm = struct.distance_matrix

    # заменяем диагональ большим числом,
    # чтобы не учитывать расстояние атома до самого себя (=0)
    np.fill_diagonal(dm, 1e9)

    # минимальное расстояние между разными атомами
    dmin = float(np.min(dm))

    # базовые дескрипторы для отчёта
    details = {
        "n_atoms": n_atoms,
        "density": round(dens, 6),
        "volume_per_atom": round(vpa, 6),
        "min_distance": round(dmin, 6),
    }

    # физически невозможное расстояние → reject
    if dmin < cfg.d_min_reject:
        return GeometryOutcome(
            status=ValidationStatus.REJECTED,
            is_suspicious=False,
            reason=RejectionReason.PHYS_IMPOSSIBLE_DISTANCE,
            details={
                **details,
                "d_min_reject": cfg.d_min_reject,
            },
        )

    # нереалистичная плотность → reject
    if dens < cfg.min_density or dens > cfg.max_density:
        return GeometryOutcome(
            status=ValidationStatus.REJECTED,
            is_suspicious=False,
            reason=RejectionReason.UNREALISTIC_DENSITY,
            details={
                **details,
                "density_min": cfg.min_density,
                "density_max": cfg.max_density,
            },
        )

    # suspicious структура (но не reject)
    suspicious = (
        (dmin < cfg.d_max_suspicious) or (vpa < cfg.vol_min) or (vpa > cfg.vol_max)
    )

    # записываем причину suspicious для анализа
    if suspicious and dmin < cfg.d_max_suspicious:
        details["suspicious_reason"] = "low_interatomic_distance"
    elif suspicious:
        details["suspicious_reason"] = "non_standard_vpa"

    return GeometryOutcome(
        status=ValidationStatus.VALIDATED,
        is_suspicious=suspicious,
        reason=None,
        details=details,
    )
