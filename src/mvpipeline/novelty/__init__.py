"""
Novelty module: проверка новизны относительно train dataset.

Отвечает за:
    - загрузку train_reference.csv,
    - быстрый lookup по (reduced_formula, spacegroup),
    - расчёт флага is_novel (метрика, а не reject).

Публичный API:
    load_train_reference
    is_novel
"""

from .train_reference import TrainReferenceIndex, load_train_reference
from .novelty_check import is_novel  # см. ниже

__all__ = [
    "TrainReferenceIndex",
    "load_train_reference",
    "is_novel",
]
