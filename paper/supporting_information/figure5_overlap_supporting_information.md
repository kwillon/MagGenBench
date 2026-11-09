# Quantitative comparison of predicted energy–magnetism distributions

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


**Table S7. Pairwise distribution overlap and sliced Wasserstein-1 distances between generator families in the predicted energy–magnetism space.**

| Generator family pair | OVL (15 × 15 grid) | 95% bootstrap CI for OVL | SWD₁ | 95% bootstrap CI for SWD₁ |
|---|---:|---|---:|---|
| MatterGen / Con-CDVAE | 0.629 | [0.600, 0.643] | 0.406 | [0.381, 0.434] |
| MatterGen / CrystalFormer | 0.315 | [0.294, 0.331] | 1.065 | [1.029, 1.101] |
| MatterGen / CrystaLLM | 0.190 | [0.150, 0.215] | 1.172 | [1.087, 1.256] |
| MatterGen / Crys-JEPA | 0.261 | [0.243, 0.274] | 1.131 | [1.107, 1.155] |
| Con-CDVAE / CrystalFormer | 0.438 | [0.416, 0.454] | 0.779 | [0.745, 0.811] |
| Con-CDVAE / CrystaLLM | 0.277 | [0.226, 0.301] | 0.970 | [0.885, 1.052] |
| Con-CDVAE / Crys-JEPA | 0.440 | [0.420, 0.458] | 0.747 | [0.722, 0.770] |
| CrystalFormer / CrystaLLM | 0.436 | [0.361, 0.434] | 0.414 | [0.367, 0.477] |
| CrystalFormer / Crys-JEPA | 0.501 | [0.475, 0.517] | 0.606 | [0.577, 0.638] |
| CrystaLLM / Crys-JEPA | 0.249 | [0.205, 0.263] | 0.877 | [0.823, 0.945] |

**Note.** OVL ranges from 0 to 1, with larger values indicating greater overlap of normalized distributions; smaller SWD₁ values indicate smaller distributional distances. Both metrics were calculated in the common standardized two-dimensional space. Intervals are pointwise 95% percentile bootstrap confidence intervals from 500 within-family replicates. CrystaLLM has a substantially smaller sample (n = 314) than the other families, and comparisons involving this family require cautious interpretation. The CrystalFormer / CrystaLLM OVL estimate (0.436) slightly exceeds its upper percentile bound (0.434); the interval was retained as calculated. Its bootstrap mean was 0.397, consistent with downward bootstrap bias of the nonsmooth histogram-overlap estimator. Percentile intervals are not constrained to contain the original estimate, and their nominal coverage should be interpreted cautiously in this sparse-sample setting.

Median pairwise OVL was 0.388, 0.375, and 0.323 on the 10 × 10, 15 × 15, and 20 × 20 grids, respectively. The largest within-pair range across these resolutions was 0.137 (CrystalFormer / CrystaLLM: 0.479, 0.436, and 0.341). Half-bin shifts changed OVL by at most 0.047 across all pairs and resolutions. MatterGen / Con-CDVAE retained the highest overlap and MatterGen / CrystaLLM the lowest across the three original grids and their shifted versions. The same extreme pairs were retained among the median estimates from equal-size subsampling at all three resolutions; their median OVL values on the 15 × 15 grid were 0.586 and 0.185, respectively, compared with full-sample values of 0.629 and 0.190. These checks support the ordering of these extreme comparisons, while demonstrating sensitivity of absolute overlap values to discretization and sample size. Shared bin mass should not be interpreted as proof of identical distributions, and low OVL alone does not establish complete separability.
