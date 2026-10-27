from pathlib import Path
import pandas as pd
from cifmagfilter.core import numeric_feature_columns, REGISTERED_DESCRIPTORS, MAIN_FEATURES, CANONICAL_MAIN_EXCLUSIONS, MAGNETIC_GRAPH_FEATURES
from paper.analysis import extract_structure_id, _dft_dataset_name, stratified_sample_indices

def test_near_constant_filter():
    df=pd.DataFrame({"chemistry__charge_balance_consistency":[1.0,1.0+1e-14,1.0-1e-14],"structure__n_elements":[2,3,4]})
    cols=numeric_feature_columns(df,min_coverage=0.2,feature_set="main",near_constant_tol=1e-8)
    assert "chemistry__charge_balance_consistency" not in cols
    assert "structure__n_elements" in cols

def test_historical_dft_id_mapping():
    folder="001_FeO_mattergen__benchmark_mgd_2000__mgd_0p10_g_1p2_seed_304__gen_23"
    assert extract_structure_id("mattergen",folder)=="benchmark_mgd_2000__mgd_0p10_g_1p2_seed_304__gen_23"
    assert _dft_dataset_name("mattergen")=="mattergen_base"


def test_canonical_descriptor_policy():
    assert len(REGISTERED_DESCRIPTORS) == 55
    assert len(CANONICAL_MAIN_EXCLUSIONS) == 6
    assert len(MAIN_FEATURES) == 49
    assert "chemistry__fraction_sites_bv_successful" not in MAIN_FEATURES
    for c in [
        "structure__n_sites",
        "magnetic_center__n_magnetic_centers",
        "magnetic_pair__n_supported_centers",
        "magnetic_pair__n_weighted_pairs",
        "magnetic_pair__total_pair_weight",
    ]:
        assert c not in MAIN_FEATURES
    assert len(MAGNETIC_GRAPH_FEATURES) == 25


def test_reference_45_manifest_matches_policy():
    p=Path(__file__).resolve().parents[1]/"paper"/"manifests"/"features.csv"
    canonical=pd.read_csv(p)["feature"].astype(str).tolist()
    expected=[c for c in MAIN_FEATURES if c not in {
        "structure__has_disorder",
        "structure__occupancy_not_1_count",
        "structure__symmetry_failed",
        "chemistry__charge_balance_consistency",
    }]
    assert canonical == expected
    assert len(canonical) == 45


def test_stratified_sample_indices_unique_and_bounded():
    import numpy as np
    meta=pd.DataFrame({"dataset":["a"]*7+["b"]*5+["c"]*4})
    idx=stratified_sample_indices(meta,10,np.random.default_rng(42))
    assert len(idx) == 10
    assert len(set(idx.tolist())) == 10
    assert idx.min() >= 0 and idx.max() < len(meta)


def test_magndata_sha_dedup_is_deterministic_and_branch_local():
    from paper.sensitivity_magndata_sha_dedup import deduplicate_magndata_by_sha
    df=pd.DataFrame({
        "dataset":["magndata","magndata","magndata","afm"],
        "structure_id":["b","a","c","x"],
        "label_order":["MAGNDATA","MAGNDATA","MAGNDATA","AFM"],
        "sha256":["same","same","other","same"],
    })
    out=deduplicate_magndata_by_sha(df)
    mag=out[out["label_order"].eq("MAGNDATA")]
    assert len(mag)==2
    assert set(mag["structure_id"])=={"a","c"}
    assert len(out[out["label_order"].eq("AFM")])==1


def test_public_api_exports_filter():
    import cifmagfilter
    assert hasattr(cifmagfilter, "CIFMagFilter")
