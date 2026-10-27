from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from cifmagfilter.reference import ReferenceModel

ROOT = Path(__file__).resolve().parents[1]


def test_reference_reference_validation_scores_match_metrics():
    metrics = json.loads((ROOT / "paper/manifests/validation_metrics.json").read_text(encoding="utf-8"))
    d = pd.read_csv(ROOT / "paper/results/reference_validation_scores.csv")
    true = d["label_order"].astype(str)
    pred = d["nearest_reference_branch"].astype(str)
    mag = true.isin(["MAGNDATA", "AFM", "FM", "FiM"])
    pred_mag = pred.ne("NM")
    five = float((true == pred).mean())
    sens = float(pred_mag[mag].mean())
    spec = float((~pred_mag[~mag]).mean())
    ba = float((sens + spec) / 2.0)
    exp = metrics["reference_validation"]
    np.testing.assert_allclose(five, exp["five_branch_agreement"], atol=5e-7)
    np.testing.assert_allclose(sens, exp["magnetic_sensitivity"], atol=5e-7)
    np.testing.assert_allclose(spec, exp["nm_specificity"], atol=5e-7)
    np.testing.assert_allclose(ba, exp["binary_balanced_accuracy"], atol=5e-7)


def test_reference_control_tables_match_canonical_metrics():
    metrics = json.loads((ROOT / "paper/manifests/validation_metrics.json").read_text(encoding="utf-8"))
    table = pd.read_csv(ROOT / "paper/results/reference_control_reference_metrics.csv").set_index("variant")
    for variant, expected in metrics["reference_controls"].items():
        assert variant in table.index
        row = table.loc[variant]
        assert int(row["n_features"]) == int(expected["n_features"])
        for col in ["five_branch_agreement", "magnetic_sensitivity", "nm_specificity", "binary_balanced_accuracy"]:
            np.testing.assert_allclose(float(row[col]), float(expected[col]), atol=1e-12)


def test_public_reference_model_can_score_feature_rows():
    model = ReferenceModel.load(ROOT / "src/cifmagfilter/data/model")
    scaler = pd.read_csv(ROOT / "paper/manifests/scaler.csv")
    row = pd.DataFrame([{c: float(v) for c, v in zip(scaler["feature"], scaler["center"])}])
    X, missing = model.transform(row)
    assert X.shape == (1, 45)
    assert float(missing[0]) == 0.0
    meta = pd.DataFrame({"structure_id": ["synthetic_center"]})
    scored = model.score(meta, X)
    assert scored.loc[0, "nearest_reference_branch"] in {"AFM", "FM", "FiM", "NM"}
    assert np.isfinite(float(scored.loc[0, "magnetic_reference_vs_NM_contrast"]))


def test_no_ground_state_prediction_columns_in_public_model_output():
    model = ReferenceModel.load(ROOT / "src/cifmagfilter/data/model")
    scaler = pd.read_csv(ROOT / "paper/manifests/scaler.csv")
    row = pd.DataFrame([{c: float(v) for c, v in zip(scaler["feature"], scaler["center"])}])
    X, _ = model.transform(row)
    scored = model.score(pd.DataFrame({"structure_id": ["x"]}), X)
    forbidden = {"predicted_class", "predicted_magnetic_order", "predicted_ground_state"}
    assert forbidden.isdisjoint(scored.columns)


def test_reference_generator_summary_matches_canonical_metrics():
    metrics = json.loads((ROOT / "paper/manifests/validation_metrics.json").read_text(encoding="utf-8"))
    table = pd.read_csv(ROOT / "paper/results/generator_query_summary.csv").set_index("dataset")
    for ds, expected in metrics["generator_benchmark"].items():
        row = table.loc[ds]
        assert int(row["n_scored"]) == int(expected["n_scored"])
        np.testing.assert_allclose(float(row["fraction_closer_to_magnetic_reference_than_NM"]), expected["fmag"], atol=1e-12)
        np.testing.assert_allclose(float(row["median_magnetic_reference_vs_NM_contrast"]), expected["median_contrast"], atol=1e-12)
        np.testing.assert_allclose(float(row["median_nearest_magnetic_reference_distance"]), expected["median_dmag"], atol=1e-12)
