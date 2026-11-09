"""Resolve historical provenance paths after the publication-directory cleanup."""
import json
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def resolve_artifact_path(path: str | Path) -> Path:
    value = str(path).replace('\\', '/')
    mapping_path = REPOSITORY_ROOT / 'tables/figure_sources/path_relocations.json'
    mapping = json.loads(mapping_path.read_text(encoding='utf-8'))
    return REPOSITORY_ROOT / mapping.get(value, value)
