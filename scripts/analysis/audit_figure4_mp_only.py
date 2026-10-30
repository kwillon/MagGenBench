"""Audit the reproduced MP-only Figure 4 before permitting a styled export."""
from __future__ import annotations

import argparse
import hashlib
import json
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CONTRAST = "magnetic_reference_vs_NM_contrast"


def validate_dft_labels(joined, source):
    """DFT labels must remain the measured source labels, independent of scores."""
    measured = source[["dataset", "sha256", "is_magnetic"]].rename(
        columns={"is_magnetic": "measured_is_magnetic"})
    check = joined.merge(measured,
                         on=["dataset", "sha256"], how="outer", validate="one_to_one",
                         indicator=True)
    if len(check) != 324 or not check._merge.eq("both").all():
        raise ValueError("DFT source map and joined population differ")
    expected = check.measured_is_magnetic.str.strip().str.lower().map({"yes": 1, "no": 0})
    if expected.isna().any() or not check.dft_is_magnetic.eq(expected).all():
        raise ValueError("Joined DFT outcomes differ from measured source labels")


def audit_dft(output):
    result = output / "results/mp_only"
    spec = importlib.util.spec_from_file_location("figure4_plot", ROOT / "filter/scripts/plot_mp_only_publication.py")
    plot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plot)
    joined, by_generator, overall, provenance = plot.load_dft(
        result / "dft_validation/dft_joined_mp_only.csv",
        result / "dft_validation/dft_validation_audit.json",
        result / "generator_scores.csv")
    validate_dft_labels(joined, pd.read_csv(ROOT / "filter/paper/data/dft_fm_source_map.csv"))
    if tuple(by_generator.dataset) != tuple(plot.DFT_ORDER):
        raise ValueError("DFT panel must contain exactly four Base cohorts")
    # Independent Wilson implementation, without using the renderer's helper.
    from statistics import NormalDist
    z = NormalDist().inv_cdf(.975)
    for row in by_generator.itertuples():
        subset = joined.loc[joined.dataset.eq(row.dataset) & joined[CONTRAST].gt(0)]
        n, k = len(subset), int(subset.dft_is_magnetic.sum())
        if n != row.n_mp_magnetic_like or k != row.n_dft_magnetic:
            raise ValueError("DFT confirmation numerator or denominator mismatch")
        p = k / n
        den = 1 + z*z/n
        center = (p + z*z/(2*n))/den
        radius = z * np.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
        np.testing.assert_allclose([row.dft_confirmation_fraction, row.ci95_low, row.ci95_high],
                                   [p, max(0, center-radius), min(1, center+radius)], atol=1e-12)
    destination = output / "audit"
    destination.mkdir(parents=True, exist_ok=True)
    by_generator.to_csv(destination / "dft_confirmation_verified.csv", index=False)
    overall.to_csv(destination / "dft_pipeline_class_verified.csv", index=False)
    summary, scores, order = plot.read_data(result / "generator_summary.csv",
                                           result / "generator_scores.csv", False)
    stat = plot.statistics(summary, scores, order, replicates=1000, seed=42)
    for i, ds in enumerate(order):
        group = scores.loc[scores.dataset.eq(ds)]
        # Independent whole-array bootstrap, versus the renderer's 128-draw batches.
        clusters = group.assign(positive=group[CONTRAST].gt(0)).groupby("formula_reduced", sort=False)
        n = clusters.size().to_numpy()
        k = clusters.positive.sum().to_numpy()
        draws = np.random.default_rng(42+i).integers(0, len(n), size=(1000, len(n)))
        ci = np.quantile(k[draws].sum(axis=1)/n[draws].sum(axis=1), [.025, .975])
        row = stat.loc[stat.dataset.eq(ds)].iloc[0]
        np.testing.assert_allclose([row.fmag_ci_low, row.fmag_ci_high], ci, rtol=0, atol=1e-12)
        np.testing.assert_allclose(row[["contrast_q05", "contrast_q25", "contrast_q50", "contrast_q75", "contrast_q95"]].to_numpy(float),
                                   group[CONTRAST].quantile([.05, .25, .5, .75, .95]), rtol=0, atol=1e-12)
        selected = group.loc[group[CONTRAST].gt(0)]
        fractions = selected.nearest_magnetic_reference_branch.value_counts(normalize=True)
        np.testing.assert_allclose([row[f"branch_{b}"] for b in plot.BRANCHES],
                                   [fractions.get(b, 0) for b in plot.BRANCHES], rtol=0, atol=1e-12)
    stat.to_csv(destination / "figure_statistics.csv", index=False)
    print("Bootstrap/quantile/branch audit passed: 1000 formula-cluster replicates, seed 42+i")
    print("DFT audit passed: 324 SHA256 matches, unchanged measured labels, four Base cohorts, Wilson 95% CI")
    print(by_generator.to_string(index=False))
    return by_generator


def compare_summary(expected, actual, atol=1e-9):
    """Return every original/restored statistic, including explicit differences."""
    if expected.dataset.duplicated().any() or actual.dataset.duplicated().any():
        raise ValueError("Duplicate summary cohorts")
    if set(expected.dataset) != set(actual.dataset):
        raise ValueError("Original and reproduced cohort sets differ")
    records = []
    for ds in expected.dataset:
        old = expected.set_index("dataset").loc[ds]
        new = actual.set_index("dataset").loc[ds]
        for field in expected.columns.drop("dataset"):
            a, b = float(old[field]), float(new[field])
            records.append({"dataset": ds, "metric": field, "original": a,
                            "reproduced": b, "difference": b-a,
                            "matches": bool(np.isclose(a, b, rtol=0, atol=atol))})
    return pd.DataFrame(records)


def audit(output):
    result = output / "results/mp_only"
    destination = output / "audit"
    destination.mkdir(parents=True, exist_ok=True)
    expected = pd.read_csv(ROOT / "filter/paper/results/mp_generator_summary.csv")
    actual = pd.read_csv(result / "generator_summary.csv")
    comparison = compare_summary(expected, actual)
    comparison.to_csv(destination / "original_vs_reproduced.csv", index=False)
    failures = comparison.loc[~comparison.matches]
    failures.to_csv(destination / "discrepancies.csv", index=False)
    features = pd.read_csv(result / "features/structure_features.csv", low_memory=False)
    scores = pd.read_csv(result / "generator_scores.csv", low_memory=False)
    manifest = pd.read_csv(output / "input_manifest.csv", low_memory=False)
    if len(features) != 20000 or not features.groupby("dataset").size().eq(2000).all():
        raise ValueError("Full extraction requires exactly 2000 rows per cohort / 20000 total")
    if features.duplicated(["dataset", "structure_id"]).any():
        raise ValueError("Duplicate extracted identities")
    if scores.duplicated(["dataset", "structure_id"]).any():
        raise ValueError("Duplicate scored identities")
    matched = scores.merge(manifest[["dataset", "structure_id", "sha256"]],
                           on=["dataset", "structure_id"], how="left",
                           suffixes=("_scored", "_manifest"), validate="one_to_one")
    if not matched.sha256_scored.eq(matched.sha256_manifest).all():
        raise ValueError("Scored identities do not match source-manifest SHA256")
    if scores.formula_reduced.isna().any() or scores.formula_reduced.str.strip().eq("").any():
        raise ValueError("Formula-cluster bootstrap requires nonempty reduced formulas")
    if not np.isfinite(scores[CONTRAST]).all():
        raise ValueError("Non-finite scored contrast")
    excluded = features.loc[~features.parse_success.eq(1)]
    excluded.groupby(["dataset", "parse_error"], dropna=False).size().rename("n").to_csv(
        destination / "exclusion_reasons.csv")
    scores.groupby("dataset")[CONTRAST].quantile([.05, .25, .5, .75, .95]).to_csv(
        destination / "contrast_quantiles.csv")
    positive = scores.loc[scores[CONTRAST].gt(0)]
    counts = pd.crosstab(positive.dataset, positive.nearest_magnetic_reference_branch).reindex(
        columns=["AFM", "FM", "FiM"], fill_value=0)
    counts.to_csv(destination / "magnetic_branch_counts.csv")
    counts.div(counts.sum(axis=1), axis=0).to_csv(destination / "magnetic_branch_fractions.csv")
    provenance = json.loads((output / "input_provenance.json").read_text())
    for name, expected_hash in provenance["model_sha256"].items():
        if hashlib.sha256((ROOT / "filter/src/cifmagfilter/data/model" / name).read_bytes()).hexdigest() != expected_hash:
            raise ValueError(f"Reference model changed: {name}")
    if hashlib.sha256((output / "original/fig04_magnetic_reference_dft.pdf").read_bytes()).hexdigest() != provenance["original_pdf_sha256"]:
        raise ValueError("Original Figure 4 control copy changed")
    for name, expected_hash in provenance["protected_figures"].items():
        if hashlib.sha256((ROOT / "paper/figures" / name).read_bytes()).hexdigest() != expected_hash:
            raise ValueError(f"Protected figure changed: {name}")
    report = {"input_rows": len(features), "scored_rows": len(scores),
              "excluded_rows": len(excluded), "summary_mismatches": len(failures),
              "summary_matches": failures.empty}
    (destination / "audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if len(failures):
        print(failures.to_string(index=False))
        raise RuntimeError("Reproduction differs from the historical summary; report written before styling")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reproduced/fig04_mp_only")
    parser.add_argument("--dft", action="store_true", help="Also verify the completed historical DFT join")
    args = parser.parse_args()
    mismatch = None
    try:
        audit(args.output.resolve())
    except RuntimeError as exc:
        # Still complete the requested DFT/CI diagnosis, while preserving a
        # failing exit status and the failed publication gate.
        mismatch = exc
    if args.dft:
        audit_dft(args.output.resolve())
    if mismatch is not None:
        raise mismatch


if __name__ == "__main__":
    main()
