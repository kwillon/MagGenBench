from __future__ import annotations

"""
report/records.py — запись общего CSV со всеми структурами: all_structures.csv.

Задача:
    - собрать единую таблицу (для анализа в pandas / jupyter / excel)
    - писать эффективно: буфером, сбрасывая на диск каждые N строк

Публичный API:
    BufferedCSVWriter
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_RECORDS_FILENAME = "all_structures.csv"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class BufferedCSVWriter:
    """
    Буферизированный writer для CSV.

    Как работает:
        - add(record): добавляет строку в память
        - при достижении flush_every → автоматически пишет пачку на диск
        - close(): принудительно сбрасывает остаток и закрывает файл

    Почему так:
        - запись на диск по одной строке часто даёт ощутимый overhead
        - буфер помогает уменьшить число IO операций
    """

    path: Path
    fieldnames: List[str]
    flush_every: int = 500

    _buffer: List[Dict[str, Any]] = field(default_factory=list)
    _file: Optional[Any] = None
    _writer: Optional[csv.DictWriter] = None
    _wrote_header: bool = False

    def open(self) -> None:
        """Открывает файл и готовит DictWriter."""
        _ensure_parent(self.path)

        # newline="" важно для csv в Windows/macOS, чтобы не было пустых строк
        self._file = self.path.open("a", encoding="utf-8", newline="")
        self._writer = csv.DictWriter(self._file, fieldnames=self.fieldnames)
        self._writer.writeheader()
        self._wrote_header = True

    def add(self, record: Dict[str, Any]) -> None:
        """
        Добавляет одну запись в буфер.

        Если буфер достиг flush_every — сбрасываем на диск.
        """
        if self._writer is None or self._file is None:
            self.open()

        self._buffer.append(record)

        if len(self._buffer) >= self.flush_every:
            self.flush()

    def flush(self) -> None:
        """Записывает текущий буфер в файл и очищает его."""
        if not self._buffer:
            return

        if self._writer is None or self._file is None:
            # теоретически не должно происходить, но пусть будет безопасно
            self.open()

        assert self._writer is not None
        self._writer.writerows(self._buffer)
        self._buffer.clear()

        # Чтобы данные реально оказались на диске (полезно на долгих прогонах)
        assert self._file is not None
        self._file.flush()

    def close(self) -> None:
        """Сбрасывает остаток и закрывает файл."""
        try:
            self.flush()
        finally:
            if self._file is not None:
                self._file.close()
            self._file = None
            self._writer = None

    def __enter__(self) -> BufferedCSVWriter:
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
