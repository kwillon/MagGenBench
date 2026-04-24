# src/mvpipeline/pipeline/runner.py
from __future__ import annotations

"""
runner.py — главный файл, который запускает весь validation pipeline.

Это "оркестратор". Он ничего не проверяет сам, а вызывает другие модули
в правильном порядке.

Общий flow pipeline:

    1. Находим все CIF файлы (discover_cifs)
    2. Для каждого файла:
        - читаем CIF
        - sanity проверка
        - определяем spacegroup
        - считаем дескрипторы
        - проверяем геометрию
        - проверяем электронейтральность
        - проверяем новизну
        - проверяем дубликаты
        - проверяем магнитность
        - сохраняем validated или rejected
        - обновляем статистику

    3. После обработки всех структур:
        - считаем итоговые метрики
        - записываем validation_report.json
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from pymatgen.core import Structure
from tqdm import tqdm

from ..analysis import compute_basic_descriptors, get_spacegroup_number
from ..dedup import SimilarityChecker
from ..io import discover_cifs, read_structure, write_rejected, write_validated
from ..novelty import load_train_reference, is_novel
from ..report import BufferedCSVWriter
from ..utils import (
    PipelineConfig,
    Rejection,
    RejectionReason,
    ValidationResult,
    ValidationStatus,
)
from ..validation import (
    check_charge_neutrality,
    geometry_validate,
    has_magnetic_elements,
    sanity_ok,
)


# =============================================================================
# Класс для накопления статистики
# =============================================================================


@dataclass
class RunStats:
    """
    Этот класс хранит статистику по всем структурам.

    Мы постепенно обновляем эти значения во время работы pipeline,
    а в конце используем их для создания validation_report.json.
    """

    # сколько всего структур нашли
    total: int = 0

    # сколько приняли
    validated: int = 0

    # сколько отклонили
    rejected: int = 0

    # сколько валидных содержат магнитные элементы
    magnetic_count: int = 0

    # сколько валидных являются новыми
    novel_count: int = 0

    # плотности валидных структур (для среднего)
    densities: list[float] = field(default_factory=list)

    # объем на атом валидных структур (для среднего)
    vpas: list[float] = field(default_factory=list)

    # причины отклонения (словарь: причина -> сколько раз)
    rejection_reasons: Dict[str, int] = field(default_factory=dict)

    def add_rejection_reason(self, reason: RejectionReason) -> None:
        """
        Увеличивает счетчик конкретной причины отклонения.

        Например:
            duplicate -> 15
            cif_parse_error -> 3
        """

        key = reason.value
        self.rejection_reasons[key] = self.rejection_reasons.get(key, 0) + 1


# =============================================================================
# Вспомогательная функция: безопасное среднее
# =============================================================================


def _avg(values: list[float]) -> float:
    """
    Возвращает среднее значение списка.

    Если список пустой — возвращает 0.
    """

    if not values:
        return 0.0

    return sum(values) / len(values)


# =============================================================================
# Вспомогательная функция: формирование записи для общего CSV
# =============================================================================

RECORDS_FIELDS = [
    "structure_id",
    "input_path",
    "status",
    "rejection_reason",
    "is_suspicious",
    "is_duplicate",
    "is_novel",
    "is_magnetic",
    "n_atoms",
    "density",
    "volume_per_atom",
    "reduced_formula",
    "spacegroup",
    "min_distance",
    "charge_solution_json",
    "details_json",
]


def _make_record(
    *,
    item: Any,
    result: ValidationResult,
    geo_details: Optional[Dict[str, Any]] = None,
    charge_solution: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Формирует одну строку для общего CSV (all_structures.csv).

    Что мы кладём в отдельные колонки (самое важное для анализа):
        - идентификатор файла (structure_id) и путь до CIF (input_path)
        - финальный статус (validated / rejected)
        - причина отклонения (rejection_reason), если rejected
        - флаги: suspicious / duplicate / novel / magnetic
        - базовые дескрипторы (если они есть): n_atoms, density, volume_per_atom,
          reduced_formula, spacegroup
        - min_distance (минимальная межатомная дистанция) — один из ключевых сигналов,
          почему структура может быть плохой

    Откуда берём min_distance:
        1) в первую очередь из geo_details (потому что geo проверка выполнялась почти всегда
           и там min_distance посчитан одинаково и для валидных, и для rejected)
        2) если geo_details не передали (или там нет поля), пробуем взять из
           result.rejection.details (иногда туда может попасть)

    Про charge_solution_json:
        - если при проверке электронейтральности удалось подобрать степени окисления,
          мы сохраняем “решение” как JSON: {"Fe": 3, "O": -2, ...}
        - это полезно для отладки: видно, “как именно” сошёлся заряд.

    Про details_json:
        - сюда складываем структурированные детали:
            {
              "geometry": {...},
              "rejection_details": {...}
            }
        - это страховка на будущее: если позже понадобится новое поле
          (например, thresholds, плотность до округления, и т.п.) — его можно
          положить в details_json, не ломая схему CSV.

    Возвращает:
        dict[str, Any] — готовую запись (строку) для добавления.
    """
    desc = result.descriptors

    # min_distance лучше брать из geo_details (есть и для validated, и для rejected по геометрии)
    min_distance = ""
    if geo_details and "min_distance" in geo_details:
        min_distance = geo_details.get("min_distance", "")
    elif result.rejection and result.rejection.details:
        min_distance = result.rejection.details.get("min_distance", "")

    # Собираем “сырые” детали — одной структурой, чтобы потом не потерять контекст.
    details_payload: dict[str, Any] = {}
    if geo_details:
        details_payload["geometry"] = geo_details
    if result.rejection:
        details_payload["rejection_details"] = result.rejection.details

    # Основная “плоская” строка CSV
    record = {
        "structure_id": item.structure_id,
        "input_path": str(item.path),
        # статус структуры
        "status": result.status.value,
        # причина отклонения (если rejected)
        "rejection_reason": result.rejection.reason.value if result.rejection else "",
        # флаги для анализа
        "is_suspicious": bool(result.is_suspicious),
        "is_duplicate": bool(result.is_duplicate),
        "is_novel": "" if result.is_novel is None else bool(result.is_novel),
        "is_magnetic": bool(result.is_magnetic),
        # дескрипторы (если они есть)
        "n_atoms": desc.n_atoms if desc else "",
        "density": desc.density if desc else "",
        "volume_per_atom": desc.volume_per_atom if desc else "",
        "reduced_formula": desc.reduced_formula if desc else "",
        "spacegroup": desc.spacegroup if desc else "",
        # ключевая геометрическая метрика
        "min_distance": min_distance,
        # решение по степеням окисления (если нашли)
        "charge_solution_json": (
            json.dumps(charge_solution, ensure_ascii=False) if charge_solution else ""
        ),
        # “мешок” для всех деталей в JSON
        "details_json": json.dumps(details_payload, ensure_ascii=False),
    }

    return record


def _emit_record(
    *,
    writer: Any,
    item: Any,
    result: ValidationResult,
    geo_details: Optional[Dict[str, Any]] = None,
    charge_solution: Optional[Dict[str, int]] = None,
) -> None:
    """
    Добавляет одну строку в all_structures.csv.

    Важно:
        Вызываем для ВСЕХ структур:
          - validated
          - rejected (parse/sanity/geometry/charge/duplicate/...)
    """
    writer.add(
        _make_record(
            item=item,
            result=result,
            geo_details=geo_details,
            charge_solution=charge_solution,
        )
    )


# =============================================================================
# Главная функция pipeline
# =============================================================================


def run_validation(
    *,
    input_dir: Path,
    out_dir: Path,
    cfg: PipelineConfig,
    train_reference: Optional[Path] = None,
    model_name: Optional[str] = None,
) -> dict[str, Any]:
    """
    Главная функция, которая запускает весь pipeline.

    input_dir:
        папка с CIF файлами

    out_dir:
        папка, куда сохраняем результаты

    cfg:
        конфигурация pipeline

    train_reference:
        CSV файл с train dataset (для novelty проверки)

    model_name:
        имя модели (если None — используем имя input_dir)
    """

    # создаем папку результатов
    out_dir.mkdir(parents=True, exist_ok=True)

    records_path = out_dir / "all_structures.csv"
    records_writer = BufferedCSVWriter(
        path=records_path,
        fieldnames=RECORDS_FIELDS,
        flush_every=500,
    )

    # находим все CIF файлы
    items = discover_cifs(input_dir)

    # загружаем train_reference.csv
    reference = load_train_reference(train_reference)

    # создаем объект статистики
    stats = RunStats(total=len(items))

    # создаем checker дубликатов
    sim_checker = SimilarityChecker()

    # =========================================================================
    # Главный цикл — обрабатываем каждый CIF
    # =========================================================================
    try:
        for item in tqdm(items, desc="Валидация CIF", unit="cif"):

            # ------------------------------------------------------------
            # 1. Читаем CIF
            # ------------------------------------------------------------

            try:
                struct: Structure = read_structure(item.path)

            except Exception as e:
                # если CIF не читается — отклоняем

                result = ValidationResult(
                    status=ValidationStatus.REJECTED,
                    rejection=Rejection(
                        reason=RejectionReason.CIF_PARSE_ERROR,
                        details={"error": str(e)},
                    ),
                )

                _emit_record(writer=records_writer, item=item, result=result)
                write_rejected(item, out_dir, result)

                stats.rejected += 1
                stats.add_rejection_reason(RejectionReason.CIF_PARSE_ERROR)

                continue

            # ------------------------------------------------------------
            # 2. sanity проверка
            # ------------------------------------------------------------

            if not sanity_ok(struct):

                result = ValidationResult(
                    status=ValidationStatus.REJECTED,
                    rejection=Rejection(
                        reason=RejectionReason.CIF_SANITY_ERROR,
                        details={"error": "sanity_failed"},
                    ),
                )

                _emit_record(writer=records_writer, item=item, result=result)
                write_rejected(item, out_dir, result)

                stats.rejected += 1
                stats.add_rejection_reason(RejectionReason.CIF_SANITY_ERROR)

                continue

            # ------------------------------------------------------------
            # 3. определяем spacegroup
            # ------------------------------------------------------------

            sg = get_spacegroup_number(struct, cfg.symprec)

            # ------------------------------------------------------------
            # 4. считаем дескрипторы
            # ------------------------------------------------------------

            desc = compute_basic_descriptors(struct, sg)

            # ------------------------------------------------------------
            # 5. проверяем геометрию
            # ------------------------------------------------------------

            geo = geometry_validate(struct, cfg)

            if geo.status == ValidationStatus.REJECTED:

                result = ValidationResult(
                    status=ValidationStatus.REJECTED,
                    descriptors=desc,
                    rejection=Rejection(geo.reason, geo.details),
                )

                _emit_record(
                    writer=records_writer,
                    item=item,
                    result=result,
                    geo_details=geo.details,
                )
                write_rejected(item, out_dir, result)

                stats.rejected += 1
                stats.add_rejection_reason(geo.reason)

                continue

            # ------------------------------------------------------------
            # 6. проверяем заряд
            # ------------------------------------------------------------

            charge = check_charge_neutrality(struct, cfg)

            if not charge.ok:

                result = ValidationResult(
                    status=ValidationStatus.REJECTED,
                    descriptors=desc,
                    rejection=Rejection(charge.reason, charge.details),
                )

                _emit_record(
                    writer=records_writer,
                    item=item,
                    result=result,
                    geo_details=geo.details,
                )
                write_rejected(item, out_dir, result)

                stats.rejected += 1
                stats.add_rejection_reason(charge.reason)

                continue

            # ------------------------------------------------------------
            # 7. проверяем новизну
            # ------------------------------------------------------------

            novel = is_novel(
                struct,
                reference,
                reduced_formula=desc.reduced_formula,
                spacegroup=desc.spacegroup,
            )

            # ------------------------------------------------------------
            # 8. проверяем дубликаты
            # ------------------------------------------------------------

            formula = desc.reduced_formula
            sg_key = desc.spacegroup or -1

            if sim_checker.is_duplicate(struct, formula, sg_key):

                result = ValidationResult(
                    status=ValidationStatus.REJECTED,
                    descriptors=desc,
                    rejection=Rejection(RejectionReason.DUPLICATE),
                )

                _emit_record(
                    writer=records_writer,
                    item=item,
                    result=result,
                    geo_details=geo.details,
                    charge_solution=charge.solution,
                )
                write_rejected(item, out_dir, result)

                stats.rejected += 1
                stats.add_rejection_reason(RejectionReason.DUPLICATE)

                continue

            sim_checker.add_to_accepted(struct, formula, sg_key)

            # ------------------------------------------------------------
            # 9. проверяем магнитность
            # ------------------------------------------------------------

            magnetic = has_magnetic_elements(struct, cfg)

            # ------------------------------------------------------------
            # 10. структура валидна — сохраняем
            # ------------------------------------------------------------

            result = ValidationResult(
                status=ValidationStatus.VALIDATED,
                descriptors=desc,
                is_magnetic=magnetic,
                is_novel=novel,
            )

            _emit_record(
                writer=records_writer,
                item=item,
                result=result,
                geo_details=geo.details,
                charge_solution=charge.solution,
            )

            write_validated(item, out_dir)

            stats.validated += 1

            if magnetic:
                stats.magnetic_count += 1

            if novel:
                stats.novel_count += 1

            stats.densities.append(desc.density)
            stats.vpas.append(desc.volume_per_atom)

    finally:
        records_writer.close()

    # =========================================================================
    # Формируем итоговый отчет
    # =========================================================================

    report = {
        "model_name": model_name or input_dir.name,
        "n_total": stats.total,
        "n_validated": stats.validated,
        "n_rejected": stats.rejected,
        "validity_ratio": stats.validated / stats.total if stats.total else 0,
        "magnetic_ratio": (
            stats.magnetic_count / stats.validated if stats.validated else 0
        ),
        "novelty_ratio": stats.novel_count / stats.validated if stats.validated else 0,
        "duplicate_ratio": (
            stats.rejection_reasons.get("duplicate", 0) / stats.total
            if stats.total
            else 0
        ),
        "avg_density": _avg(stats.densities),
        "avg_volume_per_atom": _avg(stats.vpas),
        "rejection_reasons": stats.rejection_reasons,
        "all_structures_csv": str(records_path),
    }

    report_path = out_dir / "validation_report.json"

    report_path.write_text(json.dumps(report, indent=2))

    return report
