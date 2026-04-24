from __future__ import annotations

"""
Этот файл содержит:

1. Enum-статусы валидации
2. Enum-причины отклонения (стабильный API)
3. Дефолтные значения констант

ВАЖНО:
RejectionReason — часть публичного API pipeline.
Эти значения используются в:

    - validation_report.json
    - *.reason.json
    - downstream analysis
    - benchmark scripts

Поэтому их нельзя менять без version bump.
"""

from enum import Enum


# =============================================================================
# Default values
# =============================================================================

# Дефолтный список магнитных элементов.
# Используется если magnetic_elements не задан в thresholds.yaml.
MAGNETIC_ELEMENTS_DEFAULT = {
    "Fe",
    "Co",
    "Ni",
    "Mn",
    "Cr",
    "V",
}


# =============================================================================
# Validation status
# =============================================================================


class ValidationStatus(str, Enum):
    """
    Финальный статус структуры после validation pipeline.

    VALIDATED
        Структура прошла все проверки и считается валидной.

    REJECTED
        Структура отклонена на одном из этапов pipeline.
    """

    VALIDATED = "validated"
    REJECTED = "rejected"


# =============================================================================
# Geometry quality (не влияет на статус)
# =============================================================================


class GeometryQuality(str, Enum):
    """
    Качество геометрии структуры.

    Используется для анализа качества генерации,
    но не обязательно приводит к отклонению структуры.

    OK
        Геометрия находится в нормальных пределах.

    SUSPICIOUS
        Геометрия допустима, но имеет подозрительные значения,
        например:
            - слишком малые расстояния
            - необычный объём на атом
    """

    OK = "ok"
    SUSPICIOUS = "suspicious"


# =============================================================================
# Rejection reasons
# =============================================================================


class RejectionReason(str, Enum):
    """
    Причины отклонения структуры.

    Эти значения записываются в:

        rejected_structures/*.reason.json
        validation_report.json → rejection_reasons

    Они используются для анализа ошибок генеративной модели.
    """

    # -----------------------
    # I/O errors
    # -----------------------

    CIF_PARSE_ERROR = "cif_parse_error"
    # CIF невозможно прочитать (повреждён файл)

    CIF_SANITY_ERROR = "cif_sanity_error"
    # CIF прочитан, но структура некорректна
    # (например volume <= 0 или нет атомов)

    # -----------------------
    # Geometry / physics
    # -----------------------

    TOO_MANY_ATOMS = "too_many_atoms"
    # структура слишком большая

    PHYS_IMPOSSIBLE_DISTANCE = "physically_impossible_distance"
    # атомы находятся слишком близко → overlap

    UNREALISTIC_DENSITY = "unrealistic_density"
    # плотность вне допустимого диапазона

    NON_STANDARD_VPA = "non_standard_vpa"
    # объём на атом вне нормального диапазона

    # -----------------------
    # Chemistry
    # -----------------------

    CHARGE_IMBALANCE = "charge_imbalance"
    # невозможно подобрать степени окисления,
    # дающие суммарный заряд 0 → химически невозможная структура

    # -----------------------
    # Dataset / deduplication
    # -----------------------

    DUPLICATE = "duplicate"
    # структура уже была сгенерирована ранее

    # -----------------------
    # Internal errors
    # -----------------------

    INTERNAL_ERROR = "internal_error"
    # непредвиденная ошибка pipeline
