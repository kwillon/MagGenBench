"""Fast standalone GitHub publication audit (stdlib + numpy)."""
from pathlib import Path
import ast
import hashlib
import json
import zipfile
import numpy as np

BASE = Path(__file__).resolve().parents[1]
MODEL = BASE / "src/cifmagfilter/data/model"
required = [
    "README.md", "LICENSE", "CITATION.cff", "DATA.md", "FILES_CHANGED.md",
    "REPRODUCIBILITY.md", "VERIFICATION.md", "pyproject.toml",
    "src/cifmagfilter/model.py", "src/cifmagfilter/cli.py",
    "src/cifmagfilter/reference.py", "src/cifmagfilter/core.py",
    "src/cifmagfilter/data/model/reference_filter.npz",
    "src/cifmagfilter/data/model/reference_filter.json",
    "configs/filter.example.json", "configs/generators.example.json",
    "paper/manifests/features.csv", "paper/results/mp_reference_validation_metrics.json",
    "paper/data/dft_fm_source_map.csv", "paper/data/dft_afm_source_map.csv",
    "scripts/run_mp_pipeline.py", "scripts/recalculate_dft_mp_only.py",
    "scripts/plot_mp_only_publication.py", "ci/filter.yml",
]
missing = [p for p in required if not (BASE / p).is_file()]
assert not missing, f"Missing files: {missing}"
meta = json.loads((MODEL / "reference_filter.json").read_text(encoding="utf-8"))
assert meta["reference_classes"] == ["AFM", "FM", "FiM", "NM"]
assert meta["magnetic_classes"] == ["AFM", "FM", "FiM"]
assert meta["reference_total"] == 8000
assert sum(meta["reference_counts"].values()) == 8000
with np.load(MODEL / "reference_filter.npz", allow_pickle=False) as z:
    names = z["feature_names"].astype(str).tolist()
    assert len(names) == meta["n_features"] == 45
    assert names == meta["feature_names"]
    for branch in meta["reference_classes"]:
        assert z[f"ref_{branch}"].shape == (2000, 45)
    assert "ref_MAGNDATA" not in z.files
    assert np.isfinite(z["center"]).all()
    assert (z["scale"] > 0).all()
    assert len(z["reference_self_dmag"]) == 8000

for script in (BASE / "scripts").glob("*.py"):
    ast.parse(script.read_text(encoding="utf-8"), filename=str(script))

junk=[]
for p in BASE.rglob("*"):
    if any(part in {"__pycache__", ".pytest_cache", "build", "dist", ".venv", "venv", ".git"} for part in p.parts):
        continue
    if p.is_file() and p.suffix in {".zip", ".pyc"}:
        junk.append(str(p.relative_to(BASE)))
assert not junk, junk
print("Repository audit PASS; MP-only, 45 descriptors, 8000 references, no MAGNDATA in default model")
