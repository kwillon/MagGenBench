from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_required_publication_files_exist():
    required = [
        "README.md", "LICENSE", "CITATION.cff", "DATA.md", "VERIFICATION.md",
        "REPRODUCIBILITY.md", "DESCRIPTORS.md", "pyproject.toml",
        "src/cifmagfilter/core.py", "src/cifmagfilter/reference.py", "src/cifmagfilter/model.py", "src/cifmagfilter/cli.py",
        "src/cifmagfilter/data/model/reference_filter.npz", "src/cifmagfilter/data/model/reference_filter.json",
        "paper/METHODS.md", "paper/run_reference_benchmark.py", "paper/run_reference_controls.py",
        "paper/reproduce.py", "paper/figures.py",
        "paper/manifests/features.csv", "paper/manifests/scaler.csv", "paper/manifests/validation_metrics.json",
        "ci/filter.yml",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    assert not missing, missing


def test_no_development_artifact_names_in_release():
    # Runtime caches may be created by pytest itself; release packaging strips them.
    forbidden = re.compile(r"(article_figures_v0_|old[_-]?zip|smoke[_-]?output|H5|SWY)", re.I)
    bad = []
    for p in ROOT.rglob("*"):
        if any(part in {"__pycache__", ".pytest_cache"} for part in p.parts):
            continue
        rel = str(p.relative_to(ROOT))
        if forbidden.search(rel):
            bad.append(rel)
    assert not bad, bad
