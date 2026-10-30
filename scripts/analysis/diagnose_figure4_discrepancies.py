"""Diagnose saved recalculation results without changing any production statistic."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from scipy.stats import binom

ROOT = Path(__file__).resolve().parents[2]
CONTRAST = "magnetic_reference_vs_NM_contrast"
ORDER = ["mattergen_base", "mattergen_finetuned", "concdvae_base", "concdvae_finetuned",
         "crysjepa_base", "crysjepa_refined", "crystalformer", "crystalformer_finetuned",
         "crystalllm", "crystalllm_finetuned"]


def diagnose(output):
    destination = output / "diagnosis"
    destination.mkdir(parents=True, exist_ok=True)
    result = output / "results/mp_only"
    scores = pd.read_csv(result / "generator_scores.csv")
    features = pd.read_csv(result / "features/structure_features.csv", low_memory=False)
    pdf = pd.read_csv(output / "audit/original_pdf_vs_reproduced.csv")
    differing = pdf.loc[~pdf.matches_pdf_precision]
    records = []
    for ds in differing.loc[differing.panel.eq("A"), "dataset"].unique():
        group = scores.loc[scores.dataset.eq(ds)]
        clusters = group.assign(positive=group[CONTRAST].gt(0)).groupby("formula_reduced", sort=False)
        n, k = clusters.size().to_numpy(), clusters.positive.sum().to_numpy()
        seed = 42+ORDER.index(ds)
        draws = np.random.default_rng(seed).integers(0, len(n), size=(1000, len(n)))
        replicates = np.sort(k[draws].sum(axis=1)/n[draws].sum(axis=1))
        for row in differing.loc[differing.panel.eq("A") & differing.dataset.eq(ds)].itertuples():
            p = .025 if row.metric.endswith("low") else .975
            estimate = float(np.quantile(replicates, p))
            np.testing.assert_allclose(estimate, row.reproduced, rtol=0, atol=1e-12)
            low_rank = int(binom.ppf(.025, 1000, p))
            high_rank = int(binom.ppf(.975, 1000, p))+1
            low, high = replicates[max(0, low_rank-1)], replicates[min(999, high_rank-1)]
            records.append({"dataset": ds, "bound": row.metric, "original_pdf": row.original_pdf_readback,
                            "reproduced": estimate, "absolute_difference": abs(estimate-row.original_pdf_readback),
                            "bootstrap": "reduced-formula cluster percentile bootstrap",
                            "seed": seed, "replicates": 1000, "rng": "PCG64",
                            "n_clusters": len(n), "cluster_order": "first appearance in scores; sort=False",
                            "mc_rank_low": low_rank, "mc_rank_high": high_rank,
                            "mc_bound_low": low, "mc_bound_high": high,
                            "original_within_pointwise_mc_range": low <= row.original_pdf_readback <= high,
                            "cause_status": "Compatible with finite-bootstrap Monte Carlo error; exact historical draw/order unknown",
                            "recommendation": "Keep original and recalculated endpoints distinct; do not replace silently"})
    pd.DataFrame(records).to_csv(destination / "bootstrap_discrepancies.csv", index=False)

    group = scores.loc[scores.dataset.eq("crystalformer_finetuned")]
    x = group[CONTRAST].to_numpy(float)
    assert len(x) == 2000 and np.isfinite(x).all() and not group.structure_id.duplicated().any()
    quantiles, supports = [], []
    ordered = group.sort_values([CONTRAST, "structure_id"]).reset_index(drop=True)
    for q in (.75, .95):
        field = f"contrast_q{int(q*100):02d}"
        source = pdf.loc[pdf.dataset.eq("crystalformer_finetuned") & pdf.metric.eq(field)].iloc[0]
        for method in ("linear", "lower", "higher", "midpoint", "nearest"):
            value = float(np.quantile(x, q, method=method))
            quantiles.append({"metric": field, "method": method, "original_pdf": source.original_pdf_readback,
                              "reproduced": value, "difference": value-source.original_pdf_readback,
                              "n_input": 2000, "n_scored": len(x), "nan": int(np.isnan(x).sum()),
                              "production_method": method == "linear"})
        np.testing.assert_allclose(np.quantile(x, q), np.quantile(x[::-1], q), rtol=0, atol=0)
        np.testing.assert_allclose(np.quantile(x, q), group[CONTRAST].quantile(q), rtol=0, atol=1e-12)
        rank = int(np.floor(q*(len(x)-1)))
        for position in range(rank-2, rank+4):
            row = ordered.iloc[position]
            supports.append({"quantile": q, "zero_based_rank": position, "structure_id": row.structure_id,
                             "sha256": row.sha256, "formula_reduced": row.formula_reduced,
                             "contrast": row[CONTRAST]})
    pd.DataFrame(quantiles).to_csv(destination / "crystalformer_ft_quantile_methods.csv", index=False)
    pd.DataFrame(supports).to_csv(destination / "crystalformer_ft_quantile_support.csv", index=False)

    model_dir = ROOT / "filter/src/cifmagfilter/data/model"
    model = np.load(model_dir / "reference_filter.npz", allow_pickle=False)
    metadata = json.loads((model_dir / "reference_filter.json").read_text())
    names = model["feature_names"].astype(str).tolist()
    assert names == metadata["feature_names"] and len(names) == 45
    assert metadata["reference_classes"] == ["AFM", "FM", "FiM", "NM"] and metadata["knn_k"] == 15
    scaler = pd.read_csv(ROOT / "filter/paper/manifests/mp_reference_scaler.csv").set_index("feature").loc[names]
    np.testing.assert_allclose(scaler.center, model["center"], rtol=0, atol=1e-12)
    np.testing.assert_allclose(scaler.scale, model["scale"], rtol=0, atol=1e-12)
    distance_records = []
    from cifmagfilter.model import CIFMagFilter
    canonical = CIFMagFilter.from_pretrained(model_dir)
    original_summary = pd.read_csv(ROOT / "filter/paper/results/mp_generator_summary.csv").set_index("dataset")
    for ds in ("crystalformer", "crystalformer_finetuned"):
        selected = scores.loc[scores.dataset.eq(ds)]
        frame = selected[["dataset", "structure_id"]].merge(features, on=["dataset", "structure_id"], validate="one_to_one")
        raw = frame[names].to_numpy(float)
        matrix = np.where(np.isfinite(raw), raw, model["center"])
        matrix = np.clip((matrix-model["center"])/model["scale"], -metadata["clip_z"], metadata["clip_z"])
        expected, _ = canonical.reference_model.transform(frame)
        np.testing.assert_allclose(matrix, expected, rtol=0, atol=1e-12)
        branch_means = []
        for branch in ("AFM", "FM", "FiM"):
            reference = model["ref_"+branch]
            assert reference.shape == (2000, 45)
            chunks = []
            for start in range(0, len(matrix), 256):
                distances = cdist(matrix[start:start+256], reference, metric="euclidean")
                chunks.append(np.partition(distances, 14, axis=1)[:, :15].mean(axis=1))
            branch_means.append(np.concatenate(chunks))
        independent = np.min(branch_means, axis=0)
        saved = selected.nearest_magnetic_reference_distance.to_numpy()
        np.testing.assert_allclose(independent, saved, rtol=0, atol=1e-10)
        # Reversing the processing order cannot change the median of these values.
        assert np.median(independent) == np.median(independent[::-1])
        distance_records.append({"dataset": ds, "n_scored": len(frame), "features": 45, "k": 15,
                                 "original_median": original_summary.loc[ds, "median_distance_to_magnetic_references"],
                                 "reproduced_median": float(np.median(saved)),
                                 "independent_cdist_median": float(np.median(independent)),
                                 "max_saved_vs_independent_error": float(np.max(np.abs(independent-saved))),
                                 "normalization": "reference median imputation; shipped center/scale; clip +/-8",
                                 "missing_descriptor_values_before_reference_imputation": int((~np.isfinite(raw)).sum())})
    pd.DataFrame(distance_records).to_csv(destination / "independent_distance_audit.csv", index=False)
    print(pd.DataFrame(records)[["dataset", "bound", "absolute_difference", "original_within_pointwise_mc_range"]].to_string(index=False))
    print(pd.DataFrame(distance_records).to_string(index=False))
    print("Diagnosis saved:", destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reproduced/fig04_mp_only_smact402")
    diagnose(parser.parse_args().output.resolve())
