# Figure 5 overlap: Supporting Information audit

## Scope and source integrity

Publication-ready files are derived from the existing frozen results, not replacement analyses. No property predictor was run and no existing result, source CSV, publication figure, or manuscript was changed. No editable SI document was found; `paper/README.md` reserves final tables under `paper/`. The four insertion files are grouped under `paper/supporting_information/`.

Source CSV SHA256: `d8a8b0ce43ad3b63fb9c364b0f3d3a8b92ec1849b58a6221999f8c27e3018f77`.
Publication Figure 5 SHA256: `319065067ea45bd189491abca42383e35cd02cc0aade4c691e837461d0aeccfe`.
12,281 source rows; 12,277 finite pairs; four exclusions (three CrystalFormer Base, one CrystaLLM Base). Both structure_id and sample_uid are nonempty and globally unique. Family sizes, all ten cohort counts, and the saved sample manifest were checked against the publication loader.

## Implementation and numerical checks

Reviewed `scripts/analysis/analyze_figure5_overlap.py` and `src/mvpipeline/analysis/figure5_overlap.py`; the former delegates to the latter. The publication source loader is `src/mvpipeline/analysis/manuscript_figure5_v2.py`.

- Verified pooled means and ddof=0 SDs against analysis_parameters.json.
- Verified all common edges and all 30 original-grid OVL values independently using numpy.histogram2d.
- Verified all 30 shifted-grid OVL values; shifted grids have (b+1) × (b+1) bins at the original widths.
- Verified all ten point SWD₁ values using the existing exact empirical weighted-CDF implementation.
- Verified all saved projection directions against default_rng(1984).
- Verified all 500 stored OVL bootstrap replicates and all 500 balanced subsamples at each resolution independently with numpy.histogram2d and seeds 1985/1986; checked three weighted SWD₁ replicates against the stored SWD₁ arrays. The full 500 SWD₁ replicates were not rerun.
- Recomputed all 80 bootstrap interval endpoints (30 OVL and ten SWD₁ intervals), all bootstrap means, and all balanced medians and diagnostic quantiles from resampling_distributions.npz. Agreement tolerance was 1e-14 absolute; quantiles use method='linear'.
- All ten publication rows are formatted directly from pairwise_overlap.csv at three decimal places in one step. No intermediate rounding or manual interval adjustment.

## CrystalFormer / CrystaLLM percentile interval

Full-precision OVL = 0.43592770959556726; percentile interval = [0.36132482781834191, 0.4336655274196054]. Bootstrap mean = 0.39704135984671951; mean minus point estimate = -0.038886349748847748. The upper bound is 0.0022621821759618577 below the point estimate.

The stored quantiles and all underlying OVL bootstrap replicates match the implementation; no numerical or transcription error was identified. At fixed edges, OVL = 1 − ½Σ|pᵢ − qᵢ| is concave in the pair of probability-mass vectors. Conditional bootstrap bin masses have the observed bin masses as their expectations, so Jensen's inequality gives E*[OVL*] ≤ OVL(observed). Noise in sparsely populated or similarly weighted bins can therefore produce a downward-shifted bootstrap distribution. The small CrystaLLM sample contributes sampling variability; it does not by itself prove the source of every bias component. Percentile intervals use the raw bootstrap quantiles and need not contain the observed estimate. This explains the direction of the observed bias; it is not a demonstration of nominal 95% coverage. The original values are preserved and the table note flags the limitation.

## Sensitivity and interpretation

Median pairwise OVL was 0.388, 0.375, and 0.323 on the 10 × 10, 15 × 15, and 20 × 20 grids, respectively. The largest within-pair range across these resolutions was 0.137 (CrystalFormer / CrystaLLM: 0.479, 0.436, and 0.341). Half-bin shifts changed OVL by at most 0.047 across all pairs and resolutions. MatterGen / Con-CDVAE retained the highest overlap and MatterGen / CrystaLLM the lowest across the three original grids and their shifted versions. The same extreme pairs were retained among the median estimates from equal-size subsampling at all three resolutions; their median OVL values on the 15 × 15 grid were 0.586 and 0.185, respectively, compared with full-sample values of 0.629 and 0.190. These checks support the ordering of these extreme comparisons, while demonstrating sensitivity of absolute overlap values to discretization and sample size. Shared bin mass should not be interpreted as proof of identical distributions, and low OVL alone does not establish complete separability.

Underlying checks: `reproduced/figure5_overlap/pairwise_overlap.csv` (resolution and balanced-n results), `grid_origin_sensitivity.csv` (origin shifts), and `resampling_distributions.npz` (replicates). Other pairs may change rank; no claim of complete rank stability is made.

## Table numbering and placement

The supplied request states that Tables S1–S6 are already used. No existing S7 table or S6/S7 citation was found by repository-wide searches of available Markdown, LaTeX, reStructuredText, and text documents (excluding data/archive directories); no editable manuscript or SI document was found. Thus S7 has no detected local conflict, but its availability in the submission and the order of first mentions cannot be verified. Keep S7 provisional, and check that the proposed Section 3.5 citation follows the first S6 citation in the full manuscript. No renumbering is warranted from the available evidence and no existing reference was changed.

## Reproduce this formatting and audit

```powershell
.venv/Scripts/python.exe scripts/analysis/prepare_figure5_overlap_si.py
```

The script reads frozen inputs, audits metrics and saved resampling arrays, formats the four SI files, and verifies that protected inputs retain their initial SHA256 hashes. Formatting uses existing NumPy/pandas project dependencies.

## Frozen analysis input hashes

| File | SHA256 |
|---|---|
| `reproduced/figure5_overlap/analysis_parameters.json` | `1ceccea6d8c62dc6f2d6aea37d830f42c3fb968946624915f48be2ec748f5c4c` |
| `reproduced/figure5_overlap/analysis_summary.md` | `11128fe799484c5eb810a44798c969f9ae7841296a752f48c4c761f266b78640` |
| `reproduced/figure5_overlap/grid_origin_sensitivity.csv` | `08386ef2401f24387e4c345d713b5e187fecfbc3f672cfdfaa383842c54a2229` |
| `reproduced/figure5_overlap/overlap_matrix.pdf` | `d6644b146350d03fc5bd6cb99195085165a4a5d03d78bfe1366484e863c582aa` |
| `reproduced/figure5_overlap/overlap_matrix_preview.png` | `463aec2d44a6f8587d0698992a9b317a053cbfa8132801dbb9f77d13d848e35b` |
| `reproduced/figure5_overlap/pairwise_overlap.csv` | `78bc55c9dfe35d8ee4a8540fde50ebe7cdeb6a366b15f4e367ded7556dfedf37` |
| `reproduced/figure5_overlap/population_audit.csv` | `f1ac6ee531d03250c8da526a7c8dbf8ed29d04717169f6be70aea7fa09fce26f` |
| `reproduced/figure5_overlap/projection_directions.csv` | `90a44ff4276a8f8f42fe06ff03ca970f72ae3cd600f205dbfae803f90e0da096` |
| `reproduced/figure5_overlap/resampling_distributions.npz` | `02e7b1f74b85fdd1f3ade2cb75f27d75057c350ef3149779329113a3f61db61d` |
| `reproduced/figure5_overlap/sample_manifest.csv` | `e2d47967870abbf32f1d502b8981116d6eb273c12459d4646cf31c7192473f92` |
| `reproduced/figure5_overlap/wasserstein_matrix.pdf` | `61e02dc8d0992cf55c6a6b7290e150fd3a33313f081d9273bf4dc56ee7af110a` |
| `reproduced/figure5_overlap/wasserstein_matrix_preview.png` | `43940b1bfb6c23bd07e300d2e2aaffbe5ff29b4b14d5bc2345b183b313cf4b61` |
| `paper/tables/figure_sources/fig05_energy_magnetism.csv` | `d8a8b0ce43ad3b63fb9c364b0f3d3a8b92ec1849b58a6221999f8c27e3018f77` |
| `paper/figures/fig05_energy_magnetism.pdf` | `319065067ea45bd189491abca42383e35cd02cc0aade4c691e837461d0aeccfe` |
