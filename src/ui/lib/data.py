from __future__ import annotations

"""
Работа с данными:
- загрузка all_structures.csv
- нормализация типов (числа, булевы)
"""

from pathlib import Path

import pandas as pd


BOOL_COLS = ["is_suspicious", "is_duplicate", "is_novel", "is_magnetic"]
NUM_COLS = ["n_atoms", "density", "volume_per_atom", "min_distance"]


def normalize_bool_series(s: pd.Series) -> pd.Series:
    """
    Приводим "true"/"false"/NaN к pandas boolean (nullable) без FutureWarning.
    """
    return (
        s.astype("string")
        .str.lower()
        .map({"true": True, "false": False})
        .astype("boolean")
        .fillna(False)
    )


def load_all_structures_csv(path: Path, model_name: str) -> pd.DataFrame:
    """
    Читаем all_structures.csv и приводим типы.

    Добавляем:
    - model
    - is_valid / is_rejected
    """
    df = pd.read_csv(path)
    df["model"] = model_name

    # числа
    for col in NUM_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # булевы
    for col in BOOL_COLS:
        if col in df.columns:
            df[col] = normalize_bool_series(df[col])

    # строки/статусы
    df["status"] = df["status"].astype(str)
    df["rejection_reason"] = df.get("rejection_reason", "").fillna("").astype(str)

    df["is_valid"] = df["status"].str.lower().eq("validated")
    df["is_rejected"] = df["status"].str.lower().eq("rejected")

    # structure_id иногда может отсутствовать (на всякий случай)
    if "structure_id" not in df.columns and "input_path" in df.columns:
        df["structure_id"] = df["input_path"].astype(str)

    return df


def apply_basic_filters(
    df: pd.DataFrame,
    *,
    status: str = "all",
    only_magnetic: bool = False,
    only_novel: bool = False,
) -> pd.DataFrame:
    """
    Базовые фильтры по чекбоксам.
    """
    out = df.copy()

    if status != "all":
        out = out[out["status"].str.lower() == status]

    if only_magnetic and "is_magnetic" in out.columns:
        out = out[out["is_magnetic"] == True]  # noqa: E712

    if only_novel and "is_novel" in out.columns:
        out = out[out["is_novel"] == True]  # noqa: E712

    return out


def apply_range_filters(
    df: pd.DataFrame,
    ranges: dict[str, tuple[float, float]],
) -> pd.DataFrame:
    """
    Применяет фильтры по диапазонам.
    ranges = {"density": (0.5, 10), "n_atoms": (1, 200), ...}
    """
    out = df.copy()
    for col, (lo, hi) in ranges.items():
        if col not in out.columns:
            continue
        out = out[(out[col] >= lo) & (out[col] <= hi)]
    return out
