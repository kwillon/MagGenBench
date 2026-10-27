from pathlib import Path
import json
import numpy as np
import pandas as pd

from cifmagfilter.reference import ReferenceModel

ROOT = Path(__file__).resolve().parents[1]


def test_reference_scaler_matches_ordered_feature_manifest():
    names = pd.read_csv(ROOT / "paper/manifests/features.csv")["feature"].astype(str).tolist()
    scaler = pd.read_csv(ROOT / "paper/manifests/scaler.csv")
    assert scaler["feature"].astype(str).tolist() == names
    assert len(names) == 45
    assert np.isfinite(pd.to_numeric(scaler["center"], errors="coerce")).all()
    assert (pd.to_numeric(scaler["scale"], errors="coerce") > 0).all()


def test_reference_reference_model_matches_manifest_and_counts():
    model = ReferenceModel.load(ROOT / "src/cifmagfilter/data/model")
    names = pd.read_csv(ROOT / "paper/manifests/features.csv")["feature"].astype(str).tolist()
    assert model.feature_names == names
    assert model.metadata["n_features"] == 45
    assert model.metadata["reference_total"] == 8000
    assert sum(model.metadata["reference_counts"].values()) == 8000
    assert set(model.reference_arrays) == {"AFM", "FM", "FiM", "NM"}


def test_reference_metrics_include_reference_controls():
    d = json.loads((ROOT / "paper/manifests/validation_metrics.json").read_text(encoding="utf-8"))
    assert d["feature_count"] == 45
    assert abs(d["reference_validation"]["binary_balanced_accuracy"] - 0.934639) < 1e-6
    assert abs(d["external_dft"]["pipeline_magnetic_like_dft_magnetic_fraction"] - 0.748918) < 1e-6
    assert "no_computability" in d["reference_controls"]
    assert "no_center_support_summaries" in d["reference_controls"]


def test_refactored_reference_math_matches_canonical_scores_exactly():
    d = json.loads((ROOT / "paper/results/reference_math_equivalence.json").read_text(encoding="utf-8"))
    for key in ["reference", "query"]:
        assert d[key]["max_abs_numeric_difference"] == 0.0
        assert d[key]["nearest_branch_mismatches"] == 0
        assert d[key]["binary_assignment_mismatches"] == 0
    assert d["reference"]["n_shared"] == 9283
    assert d["query"]["n_shared"] == 15574


def test_default_mp_only_model_has_no_magndata_reference():
    model = ReferenceModel.load(ROOT / "src/cifmagfilter/data/model")
    assert model.metadata["reference_classes"] == ["AFM", "FM", "FiM", "NM"]
    assert model.metadata["magnetic_classes"] == ["AFM", "FM", "FiM"]
    assert set(model.reference_arrays) == {"AFM", "FM", "FiM", "NM"}
    assert model.reference_self_dmag is not None
    assert len(model.reference_self_dmag) == 8000
    scaler = pd.read_csv(ROOT / "paper/manifests/mp_reference_scaler.csv")
    assert scaler["feature"].tolist() == model.feature_names
    np.testing.assert_allclose(scaler["center"].to_numpy(float), model.center)
    np.testing.assert_allclose(scaler["scale"].to_numpy(float), model.scale)
    import json
    metrics = json.loads((ROOT / "paper/results/mp_reference_validation_metrics.json").read_text())
    assert metrics["n_reference"] == 8000
    assert abs(metrics["binary_balanced_accuracy"] - 0.9295833333333333) < 1e-11

def test_default_model_api_features_and_distances_are_mp_only():
    from cifmagfilter import CIFMagFilter
    m = CIFMagFilter.from_pretrained()
    feature_row = {f: float(v) for f, v in zip(m.feature_names, m.reference_model.center)}
    df = m.score_features(pd.DataFrame([feature_row]))
    assert set(["distance_to_AFM", "distance_to_FM", "distance_to_FiM", "distance_to_NM"]).issubset(df.columns)
    assert "distance_to_MAGNDATA" not in df.columns
    assert df["nearest_magnetic_reference_branch"].iloc[0] in {"AFM", "FM", "FiM"}
