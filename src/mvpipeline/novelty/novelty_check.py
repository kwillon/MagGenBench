from __future__ import annotations

from typing import Optional

from pymatgen.core import Structure

from .train_reference import TrainReferenceIndex


def is_novel(
    struct: Structure,
    reference: Optional[TrainReferenceIndex],
    *,
    reduced_formula: Optional[str] = None,
    spacegroup: Optional[int] = None,
) -> Optional[bool]:
    """
    Проверяет новизну относительно train_reference.

    Возвращает:
      - None, если reference=None (не считали novelty)
      - True, если структуры нет в train
      - False, если (formula, sg) найден в train

    Важно: novelty — метрика. Не отправляем в rejected.
    """
    if reference is None:
        return None

    formula = reduced_formula or struct.composition.reduced_formula

    # spacegroup опционален: если не определили, считаем по формуле+"" (как при индексации)
    sg_str = "" if spacegroup is None else str(spacegroup)

    return (str(formula), sg_str) not in reference.keys
