# Figure 5A: quantitative distribution overlap

## Population and provenance

The exact publication CSV is read through `manuscript_figure5_v2.load_paired_predictions`. The publication wrapper is `scripts/illustrations/plot_paper_figures_3_5.py --publish`; the plotting implementation is `src/mvpipeline/analysis/manuscript_figure5_v2.py` (also callable via `scripts/illustrations/plot_manuscript_figure5_v2.py`). Its only property-data input is the frozen CSV below; no Parquet input is used. no publication files were regenerated. Older eight-cohort analysis tables are not substituted.
Source: `paper\tables\figure_sources\fig05_energy_magnetism.csv`; SHA256 `d8a8b0ce43ad3b63fb9c364b0f3d3a8b92ec1849b58a6221999f8c27e3018f77`.
12,281 source rows; exactly 12,277 pairs with both predictions finite. Both structure_id and sample_uid are nonempty and globally unique across all source rows. The exact ten cohort counts are asserted. No CHGNet/DXMag inference or input changes.

| Cohort | Source | Finite | Excluded |
|---|---:|---:|---:|
| mattergen_baseline | 1657 | 1657 | 0 |
| mattergen_finetuned | 1376 | 1376 | 0 |
| concdvae_baseline | 1864 | 1864 | 0 |
| concdvae_finetuned | 1299 | 1299 | 0 |
| crystalformer_baseline | 1083 | 1080 | 3 |
| crystalformer_finetuned | 1380 | 1380 | 0 |
| crystallm_baseline | 98 | 97 | 1 |
| crystallm_finetuned | 217 | 217 | 0 |
| crysjepa_base | 1764 | 1764 | 0 |
| crysjepa_refined | 1543 | 1543 | 0 |

Pooled Base + FT (Crys-JEPA: Base + Refined): MatterGen: 3033; Con-CDVAE: 3163; CrystalFormer: 2460; CrystaLLM: 314; Crys-JEPA: 3307. Total: 12,277.

## Methods

Variables: CHGNet total energy per atom (eV/atom), DXMag predicted moment (mu_B/f.u.). Negative predictions are retained. All finite points, including those beyond the figure's display window, are included.
Standardization uses the pooled, structure-weighted population mean and SD (ddof=0), saved with exact bin edges and software versions in analysis_parameters.json:

- energy_total_energy_eV_per_atom: mean = -5.29760996413; SD = 3.38797790481.
- magnetism_predicted_moment_value: mean = 1.88130215366; SD = 1.55492729991.

OVL = sum(min(P_bin,Q_bin)); each family histogram is normalized to unit probability mass. All families share equal-width edges over the full pooled min-max range. The primary resolution is 15 x 15, with 10 x 10 and 20 x 20 sensitivity analyses. There is no density smoothing or clipping.
SWD is sliced Wasserstein-1 (p=1): the arithmetic mean of exact empirical one-dimensional W1 over 128 uniform random angles in [0,pi), generated once with NumPy default_rng(1984). Each W1 integrates the absolute empirical CDF difference over merged projected supports. This handles unequal sample sizes exactly. SWD is in pooled standardized coordinates, not physical units.
500 nonparametric bootstrap replicates resample structures independently within each family, preserving its original n. Multinomial multiplicities are exactly equivalent to sampling rows with replacement and preserve each energy-moment pair. The same replicate weights are used for all metrics and pairs. 95% percentile intervals (2.5%,97.5%) are pointwise; there is no multiple-comparison coverage claim. Standardization, edges and directions remain fixed, so intervals are conditional on those choices. They describe structure-level sampling uncertainty, not prediction error, seed/batch dependence, or the full generator population.
OVL is a nonsmooth plug-in estimator: finite samples, sparse bins and bootstrap bias can lower estimates; percentile intervals are approximate and need not include the point estimate. Bootstrap means are supplied to expose this effect. No bias correction is claimed.
Size sensitivity: 500 repeated samples without replacement of 314 structures per family. CrystaLLM remains intact; other families are reduced. These subsampling quantiles are diagnostic ranges, NOT population confidence intervals. They separate unequal n effects from full-sample results without discarding data in the main analysis.
Grid-origin sensitivity shifts each axis by half a bin, extending the outer bounds to retain all data. Grid-origin and size checks supplement resolution sensitivity; a coarse-bin OVL is not an estimate of exact continuous support intersection.

## Results

| Resolution | Median OVL | Min | Max |
|---|---:|---:|---:|
| 10 x 10 | 0.387718 | 0.233188 | 0.648540 |
| 15 x 15 | 0.375326 | 0.189837 | 0.628984 |
| 20 x 20 | 0.322945 | 0.171269 | 0.609084 |

| Pair | OVL (15 x 15), 95% CI | SWD1, 95% CI |
|---|---|---|
| MatterGen / Con-CDVAE | 0.6290 [0.6000, 0.6426] | 0.4063 [0.3810, 0.4341] |
| MatterGen / CrystalFormer | 0.3147 [0.2937, 0.3311] | 1.0651 [1.0285, 1.1009] |
| MatterGen / CrystaLLM | 0.1898 [0.1502, 0.2148] | 1.1721 [1.0873, 1.2559] |
| MatterGen / Crys-JEPA | 0.2607 [0.2432, 0.2743] | 1.1308 [1.1067, 1.1551] |
| Con-CDVAE / CrystalFormer | 0.4379 [0.4155, 0.4542] | 0.7789 [0.7453, 0.8111] |
| Con-CDVAE / CrystaLLM | 0.2768 [0.2259, 0.3005] | 0.9697 [0.8853, 1.0524] |
| Con-CDVAE / Crys-JEPA | 0.4397 [0.4204, 0.4576] | 0.7474 [0.7216, 0.7698] |
| CrystalFormer / CrystaLLM | 0.4359 [0.3613, 0.4337] | 0.4137 [0.3669, 0.4767] |
| CrystalFormer / Crys-JEPA | 0.5013 [0.4755, 0.5170] | 0.6055 [0.5775, 0.6382] |
| CrystaLLM / Crys-JEPA | 0.2494 [0.2053, 0.2631] | 0.8769 [0.8234, 0.9447] |

Lowest primary OVL: MatterGen / CrystaLLM: 0.189837; corresponding SWD1 1.172083.

Highest primary OVL: MatterGen / Con-CDVAE: 0.628984; corresponding SWD1 0.406302.

## Robustness

| CrystaLLM pair | OVL 10 / 15 / 20 | Balanced-n median OVL 10 / 15 / 20 |
|---|---|---|
| MatterGen / CrystaLLM | 0.2332 / 0.1898 / 0.1713 | 0.2325 / 0.1847 / 0.1592 |
| Con-CDVAE / CrystaLLM | 0.3422 / 0.2768 / 0.2438 | 0.3344 / 0.2643 / 0.2357 |
| CrystalFormer / CrystaLLM | 0.4788 / 0.4359 / 0.3413 | 0.4650 / 0.4076 / 0.3185 |
| CrystaLLM / Crys-JEPA | 0.2990 / 0.2494 / 0.2157 | 0.2898 / 0.2389 / 0.2038 |

Largest absolute OVL change across 10/15/20 grids: 0.1375.
Largest absolute half-bin-origin change: 0.0467.
Full balanced-n ranges and bootstrap means are in pairwise_overlap.csv; raw resampling distributions are in resampling_distributions.npz. All 30 resolution-specific confidence intervals are supplied.

## Interpretation and suggested manuscript wording

The original statement is only partially supported: the histograms share probability mass, but the results do not support describing every pair as substantially overlapping. In particular, MatterGen / CrystaLLM has the lowest OVL and the largest SWD, whereas MatterGen / Con-CDVAE has the highest OVL and the smallest SWD. Use a qualified pairwise interpretation rather than a categorical claim about separation.

OVL quantifies shared probability mass at a stated resolution; SWD quantifies displacement and shape differences without binning. Neither has a universal threshold for 'substantial'. Positive overlap in coarse cells does not prove continuous support overlap; low overlap does not prove complete separability. No classifier or separability test was performed. The phrase 'do not occupy clearly separated regions' should be qualified by pairwise heterogeneity, grid sensitivity and the small CrystaLLM sample. Pooling Base and adapted variants describes the observed mixture, whose weights differ by family, and may mask differences between variants.

Suggested English text (Section 3.5; not inserted automatically):

> Across the five generator families, pairwise two-dimensional histogram overlap at 15 x 15 resolution ranged from 0.19 to 0.63 (median 0.38), indicating shared regions of the predicted energy-moment landscape but appreciable variation in the degree of overlap. Sliced Wasserstein-1 distances in pooled standardized coordinates ranged from 0.41 to 1.17, indicating differences between the empirical family distributions. These results should be interpreted alongside bin-resolution sensitivity and the smaller CrystaLLM sample, and do not establish either identical distributions or complete separation.

## Reproduction

```powershell
.venv/Scripts/python.exe scripts/analysis/analyze_figure5_overlap.py
.venv/Scripts/python.exe -m pytest -q tests/test_figure5_overlap.py
```

The script validates the publication population before creating outputs. No source CSV, manuscript text, or publication PDF is overwritten.

## Sources

- Repository and publication sources: https://github.com/kwillon/MagGenBench
- Sliced Wasserstein definition (p explicitly selected as 1 here): https://pythonot.github.io/gen_modules/ot.sliced.html
- One-dimensional empirical W1/CDF formulation: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wasserstein_distance.html
