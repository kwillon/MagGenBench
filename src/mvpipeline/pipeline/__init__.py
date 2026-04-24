"""
Pipeline module: сборка всех компонентов в единый validation pipeline.

Отвечает за:
    - запуск пайплайна по шагам (оркестрация),
    - применение всех проверок (sanity/geometry/chemistry),
    - дедупликацию и проверку новизны,
    - запись результатов (validated/rejected + report).

Публичный API:
    run_validation
"""

from .runner import run_validation

__all__ = [
    "run_validation",
]
