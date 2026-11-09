"""Audit frozen Figure 5A results and format the four SI insertion files.

Run from the repository root. Never calls property inference or overwrites
reproduced/figure5_overlap; all checks precede publication-file writes.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from mvpipeline.analysis.figure5_overlap import (
    COHORTS, ENERGY, FAMILIES, MOMENT, PAIRS, RESOLUTIONS, SlicedW1,
    common_edges, fixed_directions, load_population, standardize,
)
from mvpipeline.analysis.artifact_paths import resolve_artifact_path

INPUT = Path("tables/figure_sources/figure5_overlap")
OUTPUT = Path("paper/supporting_information")
AUDIT_OUTPUT = Path("reproduced/figure5_overlap")
TITLE = ("Table S7. Pairwise distribution overlap and sliced Wasserstein-1 distances "
         "between generator families in the predicted energy–magnetism space.")
HEADERS = ("Generator family pair", "OVL (15 × 15 grid)",
           "95% bootstrap CI for OVL", "SWD₁", "95% bootstrap CI for SWD₁")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mass(points, edges, weights=None):
    h, _, _ = np.histogram2d(points[:, 0], points[:, 1], bins=edges, weights=weights)
    return h.ravel() / h.sum()


def pair_ovl(histograms):
    return np.array([np.minimum(histograms[i], histograms[j]).sum() for i, j in PAIRS])


def read_metrics(path):
    # Python float converts each original decimal once; avoid parser-dependent
    # precision settings and pandas' deprecated float_precision option.
    frame = pd.read_csv(path, dtype=str)
    for column in frame.columns.difference(["family_a", "family_b"]):
        frame[column] = frame[column].map(float)
    return frame


def main():
    import argparse
    global OUTPUT, AUDIT_OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT)
    parser.add_argument('--audit-dir', type=Path, default=AUDIT_OUTPUT)
    args = parser.parse_args()
    OUTPUT, AUDIT_OUTPUT = args.output_dir, args.audit_dir
    params = json.loads((INPUT / "analysis_parameters.json").read_text())
    source = resolve_artifact_path(params["source"])
    protected = sorted(p for p in INPUT.iterdir() if p.is_file()) + [
        source, Path("paper/figures/fig05_energy_magnetism.pdf")]
    before = {p: sha256(p) for p in protected}
    assert before[source] == params["source_sha256"]
    assert before[protected[-1]] == params["publication_pdf_sha256"]
    results = read_metrics(INPUT / "pairwise_overlap.csv")
    shifts = read_metrics(INPUT / "grid_origin_sensitivity.csv")
    audit = pd.read_csv(INPUT / "population_audit.csv", index_col=0)
    raw, paired = load_population(source)
    assert list(zip(results.family_a, results.family_b)) == [(FAMILIES[i], FAMILIES[j]) for i, j in PAIRS]
    assert paired.groupby("family").size().to_dict() == params["family_sizes"]
    assert audit.source_rows.to_dict() == raw.groupby("analysis_cohort").size().reindex(COHORTS).to_dict()
    assert audit.finite_pairs.to_dict() == paired.groupby("analysis_cohort").size().reindex(COHORTS).to_dict()
    np.testing.assert_array_equal(audit.excluded, audit.source_rows - audit.finite_pairs)
    manifest = pd.read_csv(INPUT / "sample_manifest.csv")
    pd.testing.assert_frame_equal(manifest, paired[manifest.columns].reset_index(drop=True))
    z, mean, sd = standardize(paired[[ENERGY, MOMENT]].to_numpy())
    np.testing.assert_allclose(mean, [params["mean"][c] for c in (ENERGY, MOMENT)], rtol=0, atol=1e-14)
    np.testing.assert_allclose(sd, [params["std"][c] for c in (ENERGY, MOMENT)], rtol=0, atol=1e-14)
    groups = [z[paired.family.eq(f)] for f in FAMILIES]
    sizes = [len(g) for g in groups]
    for row, (i, j) in zip(results.itertuples(), PAIRS):
        assert (row.n_a, row.n_b) == (sizes[i], sizes[j])
    directions = fixed_directions(params["projections"], params["seed"])
    np.testing.assert_allclose(directions, np.loadtxt(INPUT / "projection_directions.csv", delimiter=",", skiprows=1), rtol=0, atol=1e-15)
    edges = {b: common_edges(z, b) for b in RESOLUTIONS}
    for b in RESOLUTIONS:
        np.testing.assert_allclose(edges[b], params["edges"][str(b)], rtol=0, atol=1e-14)
        np.testing.assert_allclose(pair_ovl([mass(g, edges[b]) for g in groups]), results[f"ovl_{b}"], rtol=0, atol=1e-14)
        subset = shifts.loc[shifts.bins.eq(b)]
        assert list(zip(subset.family_a, subset.family_b)) == list(zip(results.family_a, results.family_b))
        np.testing.assert_allclose(subset.ovl, results[f"ovl_{b}"], rtol=0, atol=1e-14)
        np.testing.assert_allclose(pair_ovl([mass(g, common_edges(z, b, True)) for g in groups]), subset.shifted_ovl, rtol=0, atol=1e-14)
    solvers = [SlicedW1(groups[i], groups[j], directions) for i, j in PAIRS]
    np.testing.assert_allclose([s() for s in solvers], results.swd, rtol=0, atol=1e-14)
    with np.load(INPUT / "resampling_distributions.npz") as saved:
        for key, prefix in [("swd", "swd")] + [(f"ovl_{b}", f"ovl_{b}") for b in RESOLUTIONS]:
            assert saved[key].shape == (500, 10)
            interval = np.quantile(saved[key], [.025, .975], axis=0, method="linear")
            np.testing.assert_allclose(interval[0], results[f"{prefix}_ci_low"], rtol=0, atol=1e-14)
            np.testing.assert_allclose(interval[1], results[f"{prefix}_ci_high"], rtol=0, atol=1e-14)
            np.testing.assert_allclose(saved[key].mean(axis=0), results[f"{prefix}_bootstrap_mean"], rtol=0, atol=1e-14)
        for b in RESOLUTIONS:
            np.testing.assert_allclose(np.median(saved[f"balanced_{b}"], axis=0), results[f"balanced_{b}_median"], rtol=0, atol=1e-14)
            for q, suffix in ((.025, "q025"), (.975, "q975")):
                np.testing.assert_allclose(np.quantile(saved[f"balanced_{b}"], q, axis=0), results[f"balanced_{b}_{suffix}"], rtol=0, atol=1e-14)
        # Verify all 500 stored OVL bootstrap and balanced samples independently
        # with numpy.histogram2d. Check three weighted SWD replicates as well.
        rng = np.random.default_rng(params["bootstrap_seed"])
        balanced_rng = np.random.default_rng(params["balance_seed"])
        for r in range(500):
            weights = [rng.multinomial(n, np.full(n, 1/n)) for n in sizes]
            selections = [balanced_rng.choice(n, min(sizes), replace=False) for n in sizes]
            for b in RESOLUTIONS:
                np.testing.assert_allclose(pair_ovl([mass(g, edges[b], w) for g, w in zip(groups, weights)]), saved[f"ovl_{b}"][r], rtol=0, atol=1e-14)
                np.testing.assert_allclose(pair_ovl([mass(g[s], edges[b]) for g, s in zip(groups, selections)]), saved[f"balanced_{b}"][r], rtol=0, atol=1e-14)
            if r < 3:
                np.testing.assert_allclose([s(weights[i], weights[j]) for s, (i, j) in zip(solvers, PAIRS)], saved["swd"][r], rtol=0, atol=1e-14)

    # Decimal strings are formatted once, directly from the full-precision CSV.
    rows = []
    for r in results.itertuples():
        rows.append((f"{r.family_a} / {r.family_b}", f"{r.ovl_15:.3f}",
                     f"[{r.ovl_15_ci_low:.3f}, {r.ovl_15_ci_high:.3f}]",
                     f"{r.swd:.3f}", f"[{r.swd_ci_low:.3f}, {r.swd_ci_high:.3f}]"))
    table = "| " + " | ".join(HEADERS) + " |\n|---|---:|---|---:|---|\n"
    table += "\n".join("| " + " | ".join(r) + " |" for r in rows)
    methods = r"""# Quantitative comparison of predicted energy–magnetism distributions

The analysis used the 12,277 structures with finite CHGNet-predicted total energy per atom (eV/atom) and DXMag-predicted magnetic moment (μB/f.u.) included in Figure 5A. Base and fine-tuned structures were pooled within MatterGen (n = 3,033), Con-CDVAE (n = 3,163), CrystalFormer (n = 2,460), and CrystaLLM (n = 314); Base and Refined structures were pooled for Crys-JEPA (n = 3,307). All finite pairs were retained, including points outside the figure's display limits. Predictions were taken from the frozen Figure 5 source table without rerunning either predictor.

For coordinate j (energy or moment), each observation xₖⱼ was standardized using the pooled, structure-weighted mean and population standard deviation:

\[
z_{kj}=\frac{x_{kj}-\bar{x}_j}{s_j},\qquad
\bar{x}_j=\frac{1}{N}\sum_{k=1}^{N}x_{kj},\qquad
s_j=\sqrt{\frac{1}{N}\sum_{k=1}^{N}(x_{kj}-\bar{x}_j)^2},\quad N=12{,}277.
\]

The standard-deviation convention was ddof = 0. The pooled mean and standard deviation were −5.297609964133017 and 3.3879779048097807 eV/atom for energy, and 1.8813021536627903 and 1.5549272999101402 μB/f.u. for magnetic moment, respectively.

Two-dimensional histograms were constructed on a common 15 × 15 grid with equally spaced edges spanning the full pooled minimum-to-maximum range of each standardized coordinate. Each family histogram was normalized by its own number of structures to obtain bin probability masses summing to one. For families P and Q, the overlap coefficient was

\[
\operatorname{OVL}(P,Q)=\sum_{i=1}^{225}\min(p_i,q_i),
\]

where pᵢ and qᵢ denote the normalized probability masses in the same bin i. OVL ranges from 0 (no shared bin probability mass) to 1 (identical binned probability distributions), with larger values indicating greater overlap at the specified resolution. No density smoothing or clipping was applied.

The sliced Wasserstein-1 distance (SWD₁) was calculated in the same standardized two-dimensional space as

\[
\operatorname{SWD}_1(P,Q)=\frac{1}{128}\sum_{\ell=1}^{128}
\int_{-\infty}^{\infty}\left|F_{P,\theta_\ell}(t)-F_{Q,\theta_\ell}(t)\right|\,dt,
\qquad \theta_\ell=(\cos\alpha_\ell,\sin\alpha_\ell),
\]

where F denotes the empirical cumulative distribution function of a projected family distribution. The 128 angles αℓ were sampled independently and uniformly from [0, π) using NumPy default_rng with seed 1984 and then held fixed for all comparisons. Each projected distance was integrated exactly over the merged empirical supports, retaining unequal sample sizes. Smaller SWD₁ values indicate smaller distributional distances; these distances are dimensionless in standardized coordinates and do not retain the original physical units.

Pointwise 95% confidence intervals were estimated from 500 nonparametric bootstrap replicates. Within each family, n structures were sampled with replacement, preserving the original family size and each paired energy–moment observation. The implementation used multinomial multiplicities with probabilities 1/n, equivalent to row resampling, and a separate default_rng stream with seed 1985 (1984 + 1). The same family weights were used across all metrics and pairwise comparisons within a replicate. Intervals were the 2.5th and 97.5th percentiles of the bootstrap estimates, computed with NumPy's linear quantile interpolation, without bias correction. Standardization parameters, bin edges, and projection directions were fixed throughout resampling. These intervals describe structure-level sampling uncertainty conditional on the predictions and analysis settings; they do not quantify predictor error or simultaneous coverage across comparisons.

OVL sensitivity was assessed on common 10 × 10 and 20 × 20 grids in addition to the primary 15 × 15 grid. Grid-origin sensitivity was assessed by shifting the edges by half the original bin width: each axis extended from its pooled minimum minus half a bin to its maximum plus half a bin, with the original bin width retained and one additional bin per axis. Sample-size sensitivity was assessed by 500 repeated draws without replacement of 314 structures per family, using default_rng with seed 1986 (1984 + 2); the CrystaLLM population therefore remained intact. These subsampling quantiles were treated as diagnostic ranges rather than confidence intervals. OVL depends on the selected discretization, whereas SWD₁ does not use histogram bins.
"""
    note = ("**Note.** OVL ranges from 0 to 1, with larger values indicating greater overlap of normalized distributions; "
            "smaller SWD₁ values indicate smaller distributional distances. Both metrics were calculated in the common "
            "standardized two-dimensional space. Intervals are pointwise 95% percentile bootstrap confidence intervals "
            "from 500 within-family replicates. CrystaLLM has a substantially smaller sample (n = 314) than the other "
            "families, and comparisons involving this family require cautious interpretation. The CrystalFormer / "
            "CrystaLLM OVL estimate (0.436) slightly exceeds its upper percentile bound (0.434); the interval was "
            "retained as calculated. Its bootstrap mean was 0.397, consistent with downward bootstrap bias of the "
            "nonsmooth histogram-overlap estimator. Percentile intervals are not constrained to contain the original "
            "estimate, and their nominal coverage should be interpreted cautiously in this sparse-sample setting.")
    sensitivity = ("Median pairwise OVL was 0.388, 0.375, and 0.323 on the 10 × 10, 15 × 15, and 20 × 20 grids, "
                   "respectively. The largest within-pair range across these resolutions was 0.137 "
                   "(CrystalFormer / CrystaLLM: 0.479, 0.436, and 0.341). Half-bin shifts changed OVL by at most "
                   "0.047 across all pairs and resolutions. MatterGen / Con-CDVAE retained the highest overlap "
                   "and MatterGen / CrystaLLM the lowest across the three original grids and their shifted versions. "
                   "The same extreme pairs were retained among the median estimates from equal-size subsampling "
                   "at all three resolutions; their median OVL values on the 15 × 15 grid were 0.586 and 0.185, "
                   "respectively, compared with full-sample values of 0.629 and 0.190. These checks support the "
                   "ordering of these extreme comparisons, while demonstrating sensitivity of absolute overlap "
                   "values to discretization and sample size. Shared bin mass should not be interpreted as proof "
                   "of identical distributions, and low OVL alone does not establish complete separability.")
    # Check every numeric robustness statement used in the publication prose.
    assert [f"{results[f'ovl_{b}'].median():.3f}" for b in RESOLUTIONS] == ["0.388", "0.375", "0.323"]
    assert f"{(shifts.ovl-shifts.shifted_ovl).abs().max():.3f}" == "0.047"
    for b in RESOLUTIONS:
        assert results[f"ovl_{b}"].idxmax() == results[f"balanced_{b}_median"].idxmax() == 0
        assert results[f"ovl_{b}"].idxmin() == results[f"balanced_{b}_median"].idxmin() == 2
        shifted = shifts.loc[shifts.bins.eq(b)].reset_index(drop=True)
        assert shifted.shifted_ovl.idxmax() == 0 and shifted.shifted_ovl.idxmin() == 2
    special = results.iloc[7]
    deficit = special.ovl_15 - special.ovl_15_bootstrap_mean
    assert special.ovl_15 > special.ovl_15_ci_high
    assert f"{special.ovl_15_bootstrap_mean:.3f}" == "0.397"
    assert f"{results[[f'ovl_{b}' for b in RESOLUTIONS]].max(axis=1).sub(results[[f'ovl_{b}' for b in RESOLUTIONS]].min(axis=1)).max():.3f}" == "0.137"

    insert = ("# Proposed insertion in Section 3.5\n\n"
              "> Pairwise histogram overlap in the predicted energy–magnetism space ranged from 0.190 to 0.629 "
              "(median 0.375; 15 × 15 grid), indicating shared regions with appreciable variation between "
              "generator families (Table S7).\n\n"
              "Editorial placement: Table S7 is provisional. Insert this sentence in Section 3.5 only if its "
              "first mention follows the first mention of Table S6 in the full manuscript. No occupied S7 "
              "identifier or S6/S7 first-mention sequence was found in the repository documents available for "
              "this audit; the full manuscript and its editable Supporting Information are not present. "
              "Confirm numbering against the submission files before insertion. No existing references were changed.\n")
    checks = ["# Figure 5 overlap: Supporting Information audit", "",
              "## Scope and source integrity", "",
              "Publication-ready files are derived from the existing frozen results, not replacement analyses. "
              "No property predictor was run and no existing result, source CSV, publication figure, or manuscript "
              "was changed. No editable SI document was found; `paper/README.md` reserves final tables under "
              "`paper/`. The four insertion files are grouped under `paper/supporting_information/`.", "",
              f"Source CSV SHA256: `{params['source_sha256']}`.",
              f"Publication Figure 5 SHA256: `{params['publication_pdf_sha256']}`.",
              "12,281 source rows; 12,277 finite pairs; four exclusions (three CrystalFormer Base, one CrystaLLM Base). "
              "Both structure_id and sample_uid are nonempty and globally unique. Family sizes, all ten cohort "
              "counts, and the saved sample manifest were checked against the publication loader.", "",
              "## Implementation and numerical checks", "",
              "Reviewed `scripts/analysis/analyze_figure5_overlap.py` and "
              "`src/mvpipeline/analysis/figure5_overlap.py`; the former delegates to the latter. "
              "The publication source loader is `src/mvpipeline/analysis/manuscript_figure5_v2.py`.", "",
              "- Verified pooled means and ddof=0 SDs against analysis_parameters.json.",
              "- Verified all common edges and all 30 original-grid OVL values independently using numpy.histogram2d.",
              "- Verified all 30 shifted-grid OVL values; shifted grids have (b+1) × (b+1) bins at the original widths.",
              "- Verified all ten point SWD₁ values using the existing exact empirical weighted-CDF implementation.",
              "- Verified all saved projection directions against default_rng(1984).",
              "- Verified all 500 stored OVL bootstrap replicates and all 500 balanced subsamples at each "
              "resolution independently with numpy.histogram2d and seeds 1985/1986; checked three weighted SWD₁ "
              "replicates against the stored SWD₁ arrays. The full 500 SWD₁ replicates were not rerun.",
              "- Recomputed all 80 bootstrap interval endpoints (30 OVL and ten SWD₁ intervals), all bootstrap "
              "means, and all balanced medians and diagnostic quantiles from resampling_distributions.npz. "
              "Agreement tolerance was 1e-14 absolute; quantiles use method='linear'.",
              "- All ten publication rows are formatted directly from pairwise_overlap.csv at three decimal "
              "places in one step. No intermediate rounding or manual interval adjustment.", "",
              "## CrystalFormer / CrystaLLM percentile interval", "",
              f"Full-precision OVL = {special.ovl_15:.17g}; percentile interval = "
              f"[{special.ovl_15_ci_low:.17g}, {special.ovl_15_ci_high:.17g}]. "
              f"Bootstrap mean = {special.ovl_15_bootstrap_mean:.17g}; mean minus point estimate = {-deficit:.17g}. "
              f"The upper bound is {special.ovl_15-special.ovl_15_ci_high:.17g} below the point estimate.", "",
              "The stored quantiles and all underlying OVL bootstrap replicates match the implementation; "
              "no numerical or transcription error was identified. At fixed edges, "
              "OVL = 1 − ½Σ|pᵢ − qᵢ| is concave in the pair of probability-mass vectors. Conditional bootstrap "
              "bin masses have the observed bin masses as their expectations, so Jensen's inequality gives "
              "E*[OVL*] ≤ OVL(observed). Noise in sparsely populated or similarly weighted bins can therefore "
              "produce a downward-shifted bootstrap distribution. The small CrystaLLM sample contributes "
              "sampling variability; it does not by itself prove the source of every bias component. "
              "Percentile intervals use the raw bootstrap quantiles and need not contain the observed estimate. "
              "This explains the direction of the observed bias; it is not a demonstration of nominal 95% "
              "coverage. The original values are preserved and the table note flags the limitation.", "",
              "## Sensitivity and interpretation", "", sensitivity, "",
              "Underlying checks: `tables/figure_sources/figure5_overlap/pairwise_overlap.csv` (resolution and balanced-n "
              "results), `grid_origin_sensitivity.csv` (origin shifts), and `resampling_distributions.npz` "
              "(replicates). Other pairs may change rank; no claim of complete rank stability is made.", "",
              "## Table numbering and placement", "",
              "The supplied request states that Tables S1–S6 are already used. No existing S7 table or S6/S7 "
              "citation was found by repository-wide searches of available Markdown, LaTeX, reStructuredText, "
              "and text documents (excluding data/archive directories); no editable manuscript or SI document "
              "was found. Thus S7 has no detected local conflict, but its availability in the submission and "
              "the order of first mentions cannot be verified. Keep S7 provisional, and check that the proposed "
              "Section 3.5 citation follows the first S6 citation in the full manuscript. No renumbering is warranted "
              "from the available evidence and no existing reference was changed.", "",
              "## Reproduce this formatting and audit", "", "```powershell",
              ".venv/Scripts/python.exe scripts/analysis/prepare_figure5_overlap_si.py", "```", "",
              "The script reads frozen inputs, audits metrics and saved resampling arrays, formats the four "
              "SI files, and verifies that protected inputs retain their initial SHA256 hashes. "
              "Formatting uses existing NumPy/pandas project dependencies.", "",
              "## Frozen analysis input hashes", "", "| File | SHA256 |", "|---|---|"]
    checks.extend(f"| `{p.as_posix()}` | `{h}` |" for p, h in before.items())
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "figure5_overlap_supporting_information.md").write_text(
        methods + "\n\n**" + TITLE + "**\n\n" + table + "\n\n" + note + "\n\n" + sensitivity + "\n", encoding="utf-8")
    with (OUTPUT / "table_s7_pairwise_overlap.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(HEADERS)
        writer.writerows(rows)
    (OUTPUT / "figure5_overlap_manuscript_insert.md").write_text(insert, encoding="utf-8")
    AUDIT_OUTPUT.mkdir(parents=True, exist_ok=True)
    (AUDIT_OUTPUT / "figure5_overlap_si_audit.md").write_text("\n".join(checks) + "\n", encoding="utf-8")
    for p, digest in before.items():
        assert sha256(p) == digest, f"Protected file changed: {p}"
    with (OUTPUT / "table_s7_pairwise_overlap.csv").open(encoding="utf-8", newline="") as stream:
        assert list(csv.reader(stream)) == [list(HEADERS)] + [list(r) for r in rows]
    print("PASS: population, metrics, saved resampling, publication formatting, and protected hashes")
    for name in ("figure5_overlap_supporting_information.md", "table_s7_pairwise_overlap.csv",
                 "figure5_overlap_manuscript_insert.md"):
        print(OUTPUT / name)
    print(AUDIT_OUTPUT / 'figure5_overlap_si_audit.md')


if __name__ == "__main__":
    main()
