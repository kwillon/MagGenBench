from __future__ import annotations

import json
from pathlib import Path

from paper.reproduce import load_reproduction_config

ROOT = Path(__file__).resolve().parents[1]


def test_paper_example_config_uses_current_inputs_and_no_concept_panel():
    cfg = json.loads((ROOT / "configs/paper.example.json").read_text(encoding="utf-8"))
    assert "reference_scores" in cfg
    assert "query_scores" in cfg
    assert "feature_manifest" in cfg
    assert "figure1_concept" not in cfg
    assert int(cfg["dpi"]) == 600
    assert int(cfg["n_bootstrap"]) == 1000


def test_paper_reproduce_config_resolves_paths(tmp_path):
    p = tmp_path / "paper.json"
    p.write_text(json.dumps({
        "reference_scores": "a.csv",
        "query_scores": "b.csv",
        "feature_manifest": "c.csv",
        "dft_join": "d.csv",
        "output_dir": "out",
    }), encoding="utf-8")
    cfg = load_reproduction_config(p)
    assert cfg["reference_scores"] == (tmp_path / "a.csv").resolve()
    assert cfg["output_dir"] == (tmp_path / "out").resolve()
