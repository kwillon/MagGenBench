from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from pymatgen.core import Structure

from ..utils.config import PipelineConfig
from ..utils.constants import RejectionReason


@dataclass(frozen=True)
class ChargeCheckResult:
    """
    Результат проверки charge neutrality (электронейтральности).

    ok
        True  — структура проходит проверку (найдена нейтральная комбинация зарядов).
        False — структура отклоняется.

    reason
        Код причины отклонения (если ok=False).

    details
        Технические детали, которые записываются в reason.json и помогают понять,
        почему структура была отклонена.

    solution
        Если нейтральная комбинация найдена — словарь element -> oxidation_state,
        например {"Fe": 3, "O": -2}.
        Если не найдена — None.
    """

    ok: bool
    reason: Optional[RejectionReason]
    details: Dict[str, Any]
    solution: Optional[Dict[str, int]]


def check_charge_neutrality(
    struct: Structure, cfg: PipelineConfig
) -> ChargeCheckResult:
    """
    Проверяет электронейтральность структуры на основе таблицы oxidation_states из конфигурации.

    Идея:
    - Для каждого элемента задан список допустимых степеней окисления (зарядов), например:
        Fe: [2, 3]
        O:  [-2, -1]
    - Для структуры известны количества атомов каждого элемента, например Fe2O3:
        Fe: 2, O: 3
    - Нужно выбрать по одной степени окисления для каждого элемента так, чтобы:
        sum(count[element] * ox_state[element]) == 0

    Реализация:
    - Собираем counts (кол-во атомов каждого элемента).
    - Проверяем, что для всех элементов есть oxidation_states.
    - Перебираем комбинации степеней окисления через DFS (поиск в глубину),
      используя pruning (отсечение веток), чтобы ускорить поиск:
      если с оставшимися элементами уже невозможно прийти к сумме 0, ветка отбрасывается.

    Если нейтральную комбинацию найти не удалось — структура отклоняется с reason=CHARGE_IMBALANCE.

    Parameters
    ----------
    struct : Structure
        Структура pymatgen.

    cfg : PipelineConfig
        Конфигурация pipeline. Используется поле cfg.oxidation_states:
        Dict[str, List[int]] с допустимыми степенями окисления для элементов.

    Returns
    -------
    ChargeCheckResult
        ok=True  если найдена комбинация зарядов, дающая суммарный заряд 0.
        ok=False если нейтральную комбинацию подобрать нельзя или данные неполные.
    """

    # Composition как словарь element -> amount (часто float)
    comp = struct.composition.get_el_amt_dict()

    # Переводим количества атомов в int (в CIF чаще всего целые, округляем для устойчивости)
    counts: Dict[str, int] = {}
    for el, amt in comp.items():
        counts[str(el)] = int(round(float(amt)))

    # Пустой состав = невалидная структура
    if not counts:
        return ChargeCheckResult(
            ok=False,
            reason=RejectionReason.CHARGE_IMBALANCE,
            details={"error": "empty_composition"},
            solution=None,
        )

    ox = cfg.oxidation_states or {}

    # Если для какого-то элемента нет допустимых степеней окисления → не можем проверить → reject
    missing = [el for el in counts if el not in ox]
    if missing:
        return ChargeCheckResult(
            ok=False,
            reason=RejectionReason.CHARGE_IMBALANCE,
            details={"missing_elements": missing},
            solution=None,
        )

    # Сортируем элементы по количеству атомов (больше атомов → раньше),
    # чтобы быстрее отсеивать невозможные ветки (ускорение DFS).
    items: List[Tuple[str, int]] = sorted(counts.items(), key=lambda kv: -kv[1])
    elems: List[str] = [el for el, _ in items]
    nums: List[int] = [n for _, n in items]
    states: List[List[int]] = [ox[el] for el in elems]

    # Guard от комбинаторного взрыва (если слишком много различных элементов)
    if len(elems) > 10:
        return ChargeCheckResult(
            ok=False,
            reason=RejectionReason.CHARGE_IMBALANCE,
            details={"error": "too_many_elements", "n_elements": len(elems)},
            solution=None,
        )

    # Precompute диапазон возможных зарядов от "хвоста" списка элементов:
    # min_tail[i] — минимальный заряд, который можно получить от элементов i..end
    # max_tail[i] — максимальный заряд, который можно получить от элементов i..end
    # Это используется для pruning: если 0 недостижим, не углубляемся.
    min_tail: List[int] = [0] * (len(elems) + 1)
    max_tail: List[int] = [0] * (len(elems) + 1)

    for i in range(len(elems) - 1, -1, -1):
        n = nums[i]
        s = states[i]
        min_tail[i] = min_tail[i + 1] + min(s) * n
        max_tail[i] = max_tail[i + 1] + max(s) * n

    chosen: Dict[str, int] = {}

    def dfs(i: int, acc: int) -> bool:
        """
        Рекурсивно подбирает степени окисления.

        i   — индекс текущего элемента
        acc — текущая сумма зарядов: sum(chosen[element] * count[element])

        Возвращает True, если удалось дойти до суммарного заряда 0.
        """
        # Если назначили степени окисления всем элементам — проверяем нейтральность
        if i == len(elems):
            return acc == 0

        # Pruning: проверяем, достижим ли 0 с оставшимися элементами
        lo = acc + min_tail[i]
        hi = acc + max_tail[i]
        if 0 < lo or 0 > hi:
            return False

        el = elems[i]
        n = nums[i]

        # Перебираем возможные степени окисления для текущего элемента
        for st in states[i]:
            chosen[el] = int(st)
            if dfs(i + 1, acc + int(st) * n):
                return True

        # Backtrack
        chosen.pop(el, None)
        return False

    found = dfs(0, 0)

    # Если нашли — возвращаем solution
    if found:
        return ChargeCheckResult(
            ok=True,
            reason=None,
            details={"charge_check": "ok"},
            solution=dict(chosen),
        )

    # Если не нашли — структура не проходит charge neutrality
    return ChargeCheckResult(
        ok=False,
        reason=RejectionReason.CHARGE_IMBALANCE,
        details={"charge_check": "no_solution"},
        solution=None,
    )
