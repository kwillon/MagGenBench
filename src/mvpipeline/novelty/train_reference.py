from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set, Tuple

import pandas as pd

TrainKey = Tuple[str, str]  # (reduced_formula, spacegroup)


@dataclass(frozen=True)
class TrainReferenceIndex:
    """
    Быстрый индекс train_reference.csv.

    Храним set пар (reduced_formula, spacegroup) как строки,
    чтобы novelty-check был O(1), без pandas-фильтров на каждый CIF.
    """

    keys: Set[TrainKey]

    @classmethod
    def from_csv(cls, path: Path) -> TrainReferenceIndex:
        df = pd.read_csv(path)

        # Нормализуем типы
        if "reduced_formula" not in df.columns:
            raise ValueError(
                "train_reference.csv должен содержать столбец reduced_formula"
            )

        if "spacegroup" not in df.columns:
            # spacegroup опционален по ТЗ → тогда novelty будем считать только по формуле
            # но для простоты храним spacegroup как пустую строку
            df["spacegroup"] = ""

        df["reduced_formula"] = df["reduced_formula"].astype(str)
        df["spacegroup"] = df["spacegroup"].astype(str)

        keys: Set[TrainKey] = set(zip(df["reduced_formula"], df["spacegroup"]))
        return cls(keys=keys)


def load_train_reference(path: Optional[Path]) -> Optional[TrainReferenceIndex]:
    """
    Безопасная загрузка индекса.
    Возвращает None, если path не задан или файла нет.
    """
    if path is None:
        return None
    if not path.exists():
        return None
    return TrainReferenceIndex.from_csv(path)
