from __future__ import annotations

import hashlib
import json

import pandas as pd
import pytest

from mvpipeline.descriptors.figure3_ft import mapped_retained_qc, prepare_figure3_ft_inputs


def native_fixture():
    qc = pd.DataFrame({
        "structure_id": ["run/a.cif", "run/b.cif"] + [f"rejected_{i}.cif" for i in range(1998)],
        "status": ["validated"] * 2 + ["rejected"] * 1998,
    })
    standardized = pd.DataFrame({
        "analysis_cohort": ["crystalformer_finetuned"] * 2,
        "sample_uid": ["canonical_b", "canonical_a"],
        "structure_id": ["canonical_b", "canonical_a"],
        "source_sample_id": ["run/b.cif", "run/a.cif"],
        "status": ["validated"] * 2,
    })
    return qc, standardized


def test_native_qc_mapping_uses_recorded_source_ids():
    qc, standardized = native_fixture()
    mapped = mapped_retained_qc(qc, "crystalformer_finetuned", standardized)
    assert mapped["sample_uid"].tolist() == ["canonical_a", "canonical_b"]
    assert mapped["qc_structure_id"].tolist() == ["run/a.cif", "run/b.cif"]


@pytest.mark.parametrize("defect", ["unknown_native", "duplicate_native", "extra_enrichment", "bad_status", "bad_identity"])
def test_invalid_qc_enrichment_mapping_fails(defect):
    qc, standardized = native_fixture()
    if defect == "unknown_native":
        qc.loc[0, "structure_id"] = "different_run/a.cif"
    elif defect == "duplicate_native":
        qc.loc[1, "structure_id"] = qc.loc[0, "structure_id"]
    elif defect == "extra_enrichment":
        standardized = pd.concat([standardized, pd.DataFrame({
            "analysis_cohort": ["crystalformer_finetuned"], "sample_uid": ["extra"],
            "structure_id": ["extra"], "source_sample_id": ["extra.cif"], "status": ["validated"],
        })])
    elif defect == "bad_status":
        qc.loc[0, "status"] = "success"
    else:
        standardized.loc[0, "structure_id"] = "different"
    with pytest.raises(RuntimeError):
        mapped_retained_qc(qc, "crystalformer_finetuned", standardized)


def test_native_qc_raw_2016_not_accepted():
    qc, standardized = native_fixture()
    with pytest.raises(RuntimeError, match="expected 2000"):
        mapped_retained_qc(pd.concat([qc, qc.iloc[:16]]), "crystalformer_finetuned", standardized)


def test_prepare_real_ft_enrichment_without_recomputing_it(tmp_path):
    source = "tables/08_standardized_enrichment/standardized_enrichment.csv"
    before = hashlib.sha256(open(source, "rb").read()).hexdigest()
    qc_inputs = {
        key: f"tables/03_features/phase5b_{key}_with_classes.csv"
        for key in ("crystalformer_finetuned", "crystallm_finetuned")
    }
    manifests = prepare_figure3_ft_inputs(qc_inputs=qc_inputs, output_dir=tmp_path)
    assert {key: len(pd.read_csv(path)) for key, path in manifests.items()} == {
        "crystalformer_finetuned": 1380, "crystallm_finetuned": 217,
    }
    for cohort, path in manifests.items():
        rows = pd.read_csv(path)
        assert rows["sample_uid"].equals(rows["structure_id"])
        assert rows["qc_structure_id"].equals(rows["sample_uid"])
        assert rows["analysis_cohort"].eq(cohort).all()
        assert rows["status"].eq("validated").all()
        assert (tmp_path / "manifests" / f"{cohort}_qc_ids.csv").is_file()
    assert (tmp_path / "provenance.json").is_file()
    provenance = json.loads((tmp_path / "provenance.json").read_text())
    assert provenance["geometry"] == {
        "method": "MinimumDistanceNN", "cutoff": 10.0, "tolerance": 0.1,
        "get_all_sites": False, "use_weights": False,
    }
    assert provenance["versions"]["python"]
    assert hashlib.sha256(open(source, "rb").read()).hexdigest() == before


def test_native_qc_is_mapped_in_figure3(tmp_path):
    from mvpipeline.analysis.manuscript_figure3_v2 import _read_retained_qc

    qc, standardized = native_fixture()
    qc_path, std_path = tmp_path / "qc.csv", tmp_path / "std.csv"
    qc.to_csv(qc_path, index=False)
    standardized.to_csv(std_path, index=False)
    ids = _read_retained_qc(qc_path, "crystalformer_finetuned", std_path)
    assert ids.tolist() == ["canonical_a", "canonical_b"]
    assert ids.attrs["qc_identity_mapping"] == str(std_path)
