"""
Report module: формирование артефактов анализа.

Отвечает за:
    - запись общего CSV со всеми структурами (all_structures.csv)
    - (при желании) будущие графики/агрегации/таблицы

Публичный API:
    BufferedCSVWriter
"""

from .records import BufferedCSVWriter

__all__ = ["BufferedCSVWriter"]
