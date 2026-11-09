# Figure 4: reproduction and publication design

The publication PDF is **a visual restyling of the original plotted vectors**.
It preserves the original statistical values; it does not publish the
numerically different MP-only recalculation. See the [caption](../../paper/figure_captions.md#figure-4).

## Reproduce the design without scientific calculations

```powershell
python -m pip install pymupdf matplotlib
python scripts/illustrations/restyle_figure4_original_vectors.py --source-from-git
```

The script reads the original PDF from commit
`907d98ffca4f04a9db46363251db8fdd284bbcca` (or a verified local control copy).
Original SHA256: `9ef54af2e79915c2ace5fbde91e7abb10b61187844c4ac78e50d2c7c55881105`.
No extra original PDF needs to be committed. Outputs and PNGs remain under
`reproduced/fig04_mp_only/final_design/`; the selected final PDF is
`paper/figures/fig04_magnetic_reference_dft.pdf`.

Only text and generator-color operators are replaced in the source stream.
Original statistical paths and coordinates survive inside vector Form XObjects;
each panel and its coordinate grid are transformed together. C is rotated
clockwise for horizontal category labels. Hatching and median diamonds are
vector annotations at the original positions. The palette comes from Figure 3's
`src/mvpipeline/analysis/publication_style.py`. B's interval definitions are in
the caption; C keeps a separate AFM/FM/FiM legend and lighter hatching.

The export verifies the preserved source stream, 88 statistical objects encoding
122 plotted values, finite-precision panel transforms, text bounds, and no
embedded images. The 0.02 pt coordinate tolerance bounds PDF matrix serialization,
not a change in scientific values. A's original x-range extends to 1.025;
every upper CI endpoint has positive clearance from the right clipping boundary.
The checked publication export is recorded in
[original_vector_design_audit.json](../../reproduced/figure4/publication_audit/original_vector_design_audit.json).
The design environment is recorded in [design_environment.json](../../reproduced/figure4/publication_audit/design_environment.json).
The selected export passed 31 filter tests, four reproduction-guard tests and
one vector-design integration test; checksums, links and unchanged Figures 3/5
are recorded in [publication_checks.json](../../reproduced/figure4/publication_audit/publication_checks.json).

## MP-only recalculation: sources and environment

Canonical scripts: `filter/scripts/run_mp_pipeline.py`,
`filter/scripts/recalculate_dft_mp_only.py`, and
`filter/scripts/plot_mp_only_publication.py`. The wrapper
`scripts/analysis/reproduce_figure4_mp_only.py` prepares copied CIFs, performs
smoke/full extraction, scores, and joins existing DFT measurements. It never
launches new DFT. The original summary is
`filter/paper/results/mp_generator_summary.csv`; measured DFT maps are
`filter/paper/data/dft_fm_source_map.csv` and `dft_afm_source_map.csv`.
The unchanged model uses 8,000 MP references (2,000 AFM/FM/FiM/NM each),
45 descriptors, k=15, reference-median imputation, saved center/scale and clip ±8.
Historical MP+MAGNDATA results are not substitutes for these inputs.

Two isolated Python 3.12.13 runs were retained. Direct requirements were
`filter/environment/requirements.txt`: NumPy 2.3.5, pandas 2.3.3, SciPy 1.17.0,
scikit-learn 1.9.0, pymatgen 2026.5.4, SMACT 4.0.0, spglib 2.7.0 and
matplotlib 3.10.8. Transitive pymatgen-core resolved to 2026.10.30;
the original PDF's complete runtime lock is unavailable.

- SMACT 4.0.0: 35/90 summary fields differ; see
  [strict_original_vs_reproduced.csv](../../reproduced/figure4/publication_audit/strict_original_vs_reproduced.csv).
- One-factor SMACT 4.0.2 variant: 88/90 summary fields match (absolute tolerance
  1e-9). Explicit overrides are in `filter/environment/figure4-reproduction-overrides.txt`;
  original requirements remain unchanged. Full installed versions:
  [strict_environment.json](../../reproduced/figure4/publication_audit/strict_environment.json) and
  [smact402_environment.json](../../reproduced/figure4/publication_audit/smact402_environment.json).

On 100 identical boundary CIFs the SMACT change altered 79 values in two
SMACT flags and 40 contrasts. Same-environment repeats were exact. Changing
only pymatgen-core to 2026.10.16 did not change features on the tested 20/100
CIF subsets; this does not establish version independence for all structures.

## Scientific checks and remaining recalculation differences

Both runs used 20,000 CIFs: 18,485 scored and 1,515 excluded, matching cohort
counts in the frozen summary. Exclusions: 3 CrystalFormer Base, 423 CrystaLLM
Base and 1,089 CrystaLLM FT, from malformed/invalid CIFs; detailed reasons are in
[exclusion_reasons.csv](../../reproduced/figure4/publication_audit/exclusion_reasons.csv). No selection criteria
or source CIFs changed. The SMACT 4.0.2 run matches all point fractions,
contrast medians, unique-formula counts and magnetic-class fractions.

| Recalculated quantity | Original | Recalculated | Absolute difference |
|---|---:|---:|---:|
| MatterGen Base CI low | 0.878360268 | 0.878620130 | 0.000259862 |
| MatterGen Base CI high | 0.910421641 | 0.911284486 | 0.000862845 |
| MatterGen FT CI low | 0.994104116 | 0.994246177 | 0.000142061 |
| CrystaLLM Base CI low | 0.552563649 | 0.543088170 | 0.009475478 |
| CrystaLLM Base CI high | 0.864551521 | 0.866390790 | 0.001839269 |
| CrystaLLM FT CI low | 0.695698940 | 0.705350941 | 0.009652000 |
| CrystaLLM FT CI high | 0.992801238 | 0.993168666 | 0.000367428 |
| CrystalFormer FT contrast q75 | 2.488816734 | 2.490595287 | 0.001778553 |
| CrystalFormer FT contrast q95 | 3.805582060 | 3.805485849 | 0.000096210 |
| CrystalFormer Base absolute-distance median | 5.874625494 | 5.873793579 | 0.000831915 |
| CrystalFormer FT absolute-distance median | 5.301317145 | 5.296377216 | 0.004939929 |

The first nine differences concern the recalculated figure (113/122 values
match original PDF precision); the last two concern CSV summary values not
plotted in Figure 4. Original PDF readbacks have coordinate-limited precision.
They were **not** used as numerical plotting inputs for the final design.

Bootstrap: 1,000 percentile replicates, PCG64, reduced-formula clusters in
first-appearance order (`sort=False`), cluster resampling with replacement,
ratio of total positives to total selected structures, quantiles .025/.975.
The differing groups use seeds 42/43/50/51 and 1552/463/55/221 clusters.
Original runtime seed/order are unknown. All seven old endpoints fall inside
pointwise Monte Carlo endpoint ranges (binomial ranks [16,36]/[965,985],
coverage ~95.79%); this is compatibility, not proof of identical old inputs
or a replacement for scientific CIs. No seed fitting was performed.

CrystalFormer FT has 2,000 scored records, no contrast NaN/inf and 881 formulas.
Linear pandas/NumPy quantiles agree and are order invariant; lower/higher/
midpoint/nearest do not recover the old q75/q95 either. Support positions are
1499/1500 and 1899/1900 (zero-based). On 72 nearby CIFs the existing project
environment and SMACT 4.0.2 variant have identical features/contrasts.
Independent saved-scaler normalization and SciPy Euclidean 15-NN calculations
confirm all 3,997 CrystalFormer distances to <1.9e-14; reversing order has no
effect. Missing descriptor cells (20,818/16,757) use reference-center imputation.
The remaining deterministic differences cannot be localized without old scores.

All 324 DFT SHA256 joins and the 60-record AFM subset match their measured
source maps. Source order and encoded formula labels were checked (this is
not an independent POSCAR check). D remains four Base groups: 52/55, 54/73,
24/45, 45/58, with original Wilson 95% CIs. The DFT cohort was selected using
the prior model; validation is retrospective. No new DFT was run.

## Audit records and limitations

Compact full-precision [audit tables](../../reproduced/figure4/publication_audit/) retain summary/PDF
comparisons, all 11 assessments, bootstrap ranges, quantile support, independent
distance checks, CIF population/order, DFT identity joins and class counts.
Original scores/features/full lock were not found in 36 research ZIPs, FT
archives, old folders or 145 reachable Git/reflog commits (111 CSV blobs).
Archived 16,000 CIFs and their eight-cohort manifest order match bytewise;
the extra 4,000 FT CIFs match after CRLF/LF normalization, not raw byte SHA256.
Input-order agreement does not establish the lost original scores-row order.

Large extraction outputs, full search protocols and previews remain locally in
`reproduced/fig04_mp_only/` and `reproduced/fig04_mp_only_smact402/`; they are
not committed. Audit code is under `scripts/analysis/`: `audit_figure4_mp_only.py`,
`audit_figure4_pdf_values.py`, `check_figure4_environment.py`, and
`diagnose_figure4_discrepancies.py`. Recalculated previews are explicitly labelled
and generated by the separate `plot_figure4_*preview.py` / `*_draft.py` scripts.

For optional future recalculation, create an isolated environment from the
requirements plus overrides, install `-e ./filter`, then run wrapper stages
`prepare`, `smoke`, `full --jobs 4`, `dft` with a separate `--output` directory.
The two summary/PDF audit commands intentionally fail on the documented
recalculation differences. This scientific gate remains unresolved; it does
not invalidate the separately verified preservation of original PDF vectors.
