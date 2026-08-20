from __future__ import annotations

import pytest

from mvpipeline.analysis import plotting_v2
from mvpipeline.analysis.projections_v2 import (
    COMPOSITION_SYMMETRY_PCA_FEATURES,
    MAGNETIC_GEOMETRY_PCA_FEATURES,
    PCA_OUTPUT_DIR,
    build_analysis_v2_pca_spaces,
)


def _base_row(structure_id: str, cohort: str, *, geometry_status: str = "ok"):
    row = {
        "structure_id": structure_id,
        "sample_uid": structure_id,
        "analysis_cohort": cohort,
        "model_name": cohort,
        "model_short": cohort,
        "magnetic_geometry_status": geometry_status,
    }
    for index, feature in enumerate(COMPOSITION_SYMMETRY_PCA_FEATURES, start=1):
        row[feature] = float(index)
    for index, feature in enumerate(MAGNETIC_GEOMETRY_PCA_FEATURES, start=1):
        row[feature] = float(index) if geometry_status == "ok" else ""
    return row


def _synthetic_rows():
    cohorts = plotting_v2.ANALYSIS_V2_MAGNETIC_COHORT_ORDER
    rows = []
    for index, cohort in enumerate(cohorts):
        row = _base_row(f"s{index}", cohort)
        for feature_index, feature in enumerate(COMPOSITION_SYMMETRY_PCA_FEATURES):
            row[feature] = float(index + feature_index + 1)
        for feature_index, feature in enumerate(MAGNETIC_GEOMETRY_PCA_FEATURES):
            row[feature] = float((index + 1) * (feature_index + 1))
        rows.append(row)
    not_applicable = _base_row("s_not_applicable", cohorts[0], geometry_status="not_applicable")
    for feature_index, feature in enumerate(COMPOSITION_SYMMETRY_PCA_FEATURES):
        not_applicable[feature] = float(feature_index + 3)
    rows.append(not_applicable)
    return rows


def test_analysis_v2_pca_feature_lists_are_fixed_and_exclude_enrichment_fields():
    assert COMPOSITION_SYMMETRY_PCA_FEATURES == (
        "transition_3d_fraction",
        "selected_4d_5d_fraction",
        "configured_lanthanide_fraction",
        "n_transition_3d_species",
        "n_selected_4d_5d_species",
        "n_configured_lanthanide_species",
        "contains_3d_and_configured_lanthanide",
        "n_symmetry_unique_sites",
        "symmetry_unique_site_fraction",
        "n_symmetry_unique_magnetic_sites",
        "site_multiplicity_entropy",
    )
    assert MAGNETIC_GEOMETRY_PCA_FEATURES == (
        "magnetic_site_nearest_neighbor_distance_min",
        "magnetic_site_nearest_neighbor_distance_mean",
        "magnetic_site_nearest_neighbor_distance_std",
        "magnetic_site_nearest_magnetic_neighbor_distance_min",
        "magnetic_site_nearest_magnetic_neighbor_distance_mean",
        "magnetic_site_nearest_magnetic_neighbor_distance_std",
        "magnetic_site_coordination_mean",
        "magnetic_site_coordination_std",
        "magnetic_site_magnetic_coordination_mean",
        "magnetic_site_magnetic_coordination_std",
        "magnetic_site_magnetic_neighbor_fraction_mean",
        "magnetic_site_magnetic_neighbor_fraction_std",
        "symmetry_unique_magnetic_site_fraction",
    )
    all_features = COMPOSITION_SYMMETRY_PCA_FEATURES + MAGNETIC_GEOMETRY_PCA_FEATURES
    assert not any("energy" in feature for feature in all_features)
    assert not any("magnetism_predicted" in feature for feature in all_features)


def test_analysis_v2_pca_selection_and_shapes_are_deterministic():
    import pandas as pd

    df = pd.DataFrame(_synthetic_rows())
    composition, magnetic_geometry = build_analysis_v2_pca_spaces(
        df,
        expected_total_rows=None,
        expected_geometry_rows=None,
    )

    assert len(composition.scores) == len(df)
    assert len(magnetic_geometry.scores) == 8
    assert tuple(composition.scores.columns[-2:]) == ("PC1", "PC2")
    assert tuple(magnetic_geometry.scores.columns[-2:]) == ("PC1", "PC2")
    assert tuple(composition.loadings["feature"]) == COMPOSITION_SYMMETRY_PCA_FEATURES
    assert tuple(magnetic_geometry.loadings["feature"]) == MAGNETIC_GEOMETRY_PCA_FEATURES
    assert composition.loadings.shape == (11, 3)
    assert magnetic_geometry.loadings.shape == (13, 3)


def test_analysis_v2_pca_does_not_impute_missing_values():
    import pandas as pd

    rows = _synthetic_rows()
    rows[0]["transition_3d_fraction"] = ""
    df = pd.DataFrame(rows)

    with pytest.raises(RuntimeError, match="non-finite PCA feature values"):
        build_analysis_v2_pca_spaces(
            df,
            expected_total_rows=None,
            expected_geometry_rows=None,
        )


def test_analysis_v2_pca_geometry_uses_status_ok_rows_only():
    import pandas as pd

    rows = _synthetic_rows()
    rows[0]["magnetic_geometry_status"] = "not_applicable"
    for feature in MAGNETIC_GEOMETRY_PCA_FEATURES:
        rows[0][feature] = ""
    df = pd.DataFrame(rows)

    _, magnetic_geometry = build_analysis_v2_pca_spaces(
        df,
        expected_total_rows=None,
        expected_geometry_rows=7,
    )

    assert len(magnetic_geometry.scores) == 7
    assert "s0" not in set(magnetic_geometry.scores["structure_id"])


def test_analysis_v2_pca_output_paths_are_generated_reproduced_paths():
    assert PCA_OUTPUT_DIR == plotting_v2.ANALYSIS_V2_OUTPUT_DIR / "projections"
    assert plotting_v2.ANALYSIS_V2_PCA_BASENAMES == (
        "05_pca_composition_symmetry_v2",
        "06_pca_magnetic_geometry_v2",
        "07_pca_adaptation_shifts_v2",
        "08_pca_loadings_v2",
    )
