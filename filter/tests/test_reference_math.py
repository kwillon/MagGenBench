import numpy as np
import pandas as pd

from cifmagfilter.reference import (
    robust_fit,
    robust_transform,
    knn_distance,
    knn_distance_training,
    finish_scores,
    score_against_references,
    score_reference_training,
)


def test_robust_fit_transform_are_identical_on_same_rows():
    df = pd.DataFrame({
        "a": [0.0, 1.0, 2.0, np.nan, 4.0, 5.0],
        "b": [10.0, 11.0, 12.0, 13.0, np.nan, 15.0],
    })
    mask = np.ones(len(df), dtype=bool)
    z1, center, scale, miss1 = robust_fit(df, ["a", "b"], mask, 8.0)
    z2, miss2 = robust_transform(df, ["a", "b"], center, scale, 8.0)
    np.testing.assert_allclose(z1, z2, rtol=0, atol=0)
    np.testing.assert_allclose(miss1, miss2, rtol=0, atol=0)


def test_knn_distance_known_example():
    ref = np.array([[0.0], [2.0], [4.0]])
    q = np.array([[1.0], [3.0]])
    got = knn_distance(q, ref, 2)
    np.testing.assert_allclose(got, [1.0, 1.0])


def test_training_distance_removes_self():
    X = np.array([[0.0], [1.0], [3.0], [10.0]])
    idx = np.array([0, 1, 2])
    got = knn_distance_training(X, idx, 1)
    # Each in-branch point uses its nearest *other* branch point.
    np.testing.assert_allclose(got[:3], [1.0, 1.0, 2.0])


def test_contrast_definition_and_binary_flag():
    out = pd.DataFrame({
        "distance_to_MAGNDATA": [2.0, 4.0],
        "distance_to_AFM": [3.0, 5.0],
        "distance_to_FM": [4.0, 6.0],
        "distance_to_FiM": [5.0, 7.0],
        "distance_to_NM": [6.0, 1.0],
    })
    got = finish_scores(out, ["MAGNDATA", "AFM", "FM", "FiM", "NM"], ["MAGNDATA", "AFM", "FM", "FiM"])
    np.testing.assert_allclose(got["magnetic_reference_vs_NM_contrast"], [4.0, -3.0])
    assert got["is_closer_to_magnetic_reference_than_NM"].tolist() == [1, 0]
    assert got["nearest_magnetic_reference_branch"].tolist() == ["MAGNDATA", "MAGNDATA"]


def test_query_and_training_score_columns_are_canonical():
    X = np.array([[0.0], [0.2], [5.0], [5.2], [10.0], [10.2], [15.0], [15.2], [20.0], [20.2]])
    labels = pd.Series(["MAGNDATA", "MAGNDATA", "AFM", "AFM", "FM", "FM", "FiM", "FiM", "NM", "NM"])
    meta = pd.DataFrame({"structure_id": [str(i) for i in range(len(X))]})
    train = score_reference_training(meta, X, labels, ["MAGNDATA", "AFM", "FM", "FiM", "NM"], ["MAGNDATA", "AFM", "FM", "FiM"], 1)
    refs = {c: X[labels.eq(c).to_numpy()] for c in ["MAGNDATA", "AFM", "FM", "FiM", "NM"]}
    query = score_against_references(meta.iloc[:1].copy(), X[:1], refs, ["MAGNDATA", "AFM", "FM", "FiM"], 1)
    for frame in [train, query]:
        for c in [
            "nearest_reference_branch",
            "nearest_magnetic_reference_branch",
            "nearest_magnetic_reference_distance",
            "magnetic_reference_vs_NM_contrast",
            "is_closer_to_magnetic_reference_than_NM",
        ]:
            assert c in frame.columns


def test_mp_only_reference_classes_scoring():
    from cifmagfilter.reference import score_against_references
    X = np.asarray([[1., 0.]])
    refs = {"AFM": np.asarray([[1., 1.]]), "FM": np.asarray([[1., 2.]]),
            "FiM": np.asarray([[1., 3.]]), "NM": np.asarray([[0., 7.]])}
    scored = score_against_references(pd.DataFrame({"structure_id": ["one"]}), X, refs,
                                      ["AFM", "FM", "FiM"], k=1)
    assert scored.loc[0, "nearest_magnetic_reference_branch"] == "AFM"
    assert "distance_to_MAGNDATA" not in scored
    assert scored.loc[0, "magnetic_reference_vs_NM_contrast"] > 0
