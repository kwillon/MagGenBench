from __future__ import annotations

"""
Файловые утилиты.

Тут:
- индексируем существующие запуски в outputs/*
- читаем JSON безопасно
"""

import json
from pathlib import Path


def safe_read_json(path: Path) -> dict:
    """Безопасно читаем JSON. Если файл битый — возвращаем {}."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_outputs_index(outputs_root: Path = Path("outputs")) -> list[dict]:
    """
    Ищем запуски в outputs/*/validation_report.json

    Возвращаем список словарей:
    {
        name: <имя папки>,
        dir: Path,
        report: Path,
        csv: Optional[Path],
        validated_dir: Path,
        rejected_dir: Path
    }
    """
    runs: list[dict] = []
    if not outputs_root.exists():
        return runs

    for model_dir in sorted(outputs_root.iterdir()):
        if not model_dir.is_dir():
            continue

        report_path = model_dir / "validation_report.json"
        csv_path = model_dir / "all_structures.csv"

        if report_path.exists():
            runs.append(
                {
                    "name": model_dir.name,
                    "dir": model_dir,
                    "report": report_path,
                    "csv": csv_path if csv_path.exists() else None,
                    "validated_dir": model_dir / "validated_structures",
                    "rejected_dir": model_dir / "rejected_structures",
                }
            )

    return runs
