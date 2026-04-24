"""
UI pages.

Каждая страница — это отдельная функция render_*_page(),
которую вызывает app.py в зависимости от выбранного раздела.
"""

from .run_view import render_run_page
from .explore_view import render_explore_page
from .compare_view import render_compare_page

__all__ = [
    "render_run_page",
    "render_explore_page",
    "render_compare_page",
]
