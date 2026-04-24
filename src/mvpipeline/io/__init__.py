"""
IO module: работа с файловой системой.

Отвечает за:
    - обнаружение CIF-файлов,
    - чтение структур,
    - запись validated и rejected структур,
    - запись reason.json.

Публичный API:
    discover_cifs
    read_structure
    write_validated
    write_rejected
"""

from .discover import discover_cifs
from .cif_reader import read_structure
from .writers import write_validated, write_rejected

__all__ = [
    "discover_cifs",
    "read_structure",
    "write_validated",
    "write_rejected",
]
