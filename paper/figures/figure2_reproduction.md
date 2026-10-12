# Figure 2 provenance and reproduction

The implementation is `src/mvpipeline/analysis/manuscript_figure2_v2.py`;
the entry point is `scripts/illustrations/plot_manuscript_figure2_v2.py`.
The previous implementation calculated its eight cohort sizes by counting
`analysis_cohort` rows in `tables/10_analysis_v2_magnetic/analysis_v2_magnetic.csv`.
Its baseline QC counts and rejection profiles were calculated from
`tables/02_validation/master_structures_with_validation_status.csv` and
`tables/03_features/crysjepa_base_with_classes.csv`. No retained counts or
rejection percentages were hardcoded in that implementation.

The updated implementation counts structural QC statuses directly, without
joining CHGNet, DXMag or descriptor tables. Verification targets are kept
separately and never supply plotted values. The baseline validation CSV is
ragged; the existing dedicated parser reads its trailing status fields.
All other inputs must be rectangular CSVs containing unique `sample_uid`
or `structure_id` and `status` (`validated` or `rejected`). The Crys-JEPA
Base table also supplies `rejection_reason` for panel D.

Local audit on 2026-10-10:

| Set | Retained after QC | Population | Retention | Source/status |
|---|---:|---:|---:|---|
| MatterGen Base | 1657 | 2000 | 82.85% | baseline validation CSV |
| MatterGen FT | 1376 | 2000 | 68.80% | `tables/03_features/phase5b_mattergen_finetuned_with_classes.csv` |
| Con-CDVAE Base | 1864 | 2000 | 93.20% | baseline validation CSV |
| Con-CDVAE FT | 1299 | 2000 | 64.95% | `tables/03_features/phase5b_concdvae_finetuned_with_classes.csv` |
| CrystalFormer Base | 1083 | 2000 | 54.15% | baseline validation CSV |
| CrystalFormer FT | unverified (target 1380) | unverified | target 69.00% | missing QC input |
| CrystaLLM Base | 98 | 2000 | 4.90% | baseline validation CSV |
| CrystaLLM FT | unverified (target 217) | unverified | target 10.85% | missing QC input |
| Crys-JEPA Base | 1764 | 2000 | 88.20% | `tables/03_features/crysjepa_base_with_classes.csv` |
| Crys-JEPA Ref. | 1543 | 2000 | 77.15% | `tables/03_features/crysjepa_refined_with_classes.csv` |

The eight verified sets sum to 10684, matching the frozen analysis table.
The ten verification targets sum to 12281; the difference is 1597 = 1380 +
217 from the two unavailable FT cohorts. There is no observed count
discrepancy among the eight available sets. The new FT targets remain
unverified, and their inclusion in downstream analysis is not implied.
Crys-JEPA Base has 236 rejected structures: 154 charge imbalance, 77
impossible distance and 5 duplicate primary reasons. Panel D normalizes
these counts by 236; every available baseline profile sums to 100%.

## Missing inputs

The following are explicitly configured expected paths, not confirmed
server filenames. They do not exist in the local checkout:

- `outputs/crystalformer_finetuned/all_structures.csv`
- `outputs/crystallm_finetuned/all_structures.csv`

Provide the full post-harmonization benchmark QC tables (2000 rows each),
including rejected rows. Use the CLI path options if the actual server
filenames differ. A 2016-row raw-generation table fails validation; select
the recorded benchmark population using its original harmonization
manifest upstream. Do not truncate rows or divide raw retained counts by
2000. The missing benchmark manifests cannot be reconstructed here.

## Commands

From the repository root, with pandas, matplotlib and the local package
available, audit existing sources without generating an incomplete figure:

```bash
PYTHONPATH=src python scripts/illustrations/plot_manuscript_figure2_v2.py \
  --audit-only --check-expected
```

An incomplete audit prints the missing paths and exits with status 2.
Windows PowerShell (temporary dependencies managed by uv):

```powershell
uv --cache-dir .uv-cache run --with pandas --with matplotlib --with pytest python scripts/illustrations/plot_manuscript_figure2_v2.py --audit-only --check-expected
uv --cache-dir .uv-cache run --with pandas --with matplotlib --with pytest python -m pytest tests/test_manuscript_figure2_v2.py tests/test_validation_figures_v2.py tests/test_paper_pipeline_v3.py -q
```

Full server reproduction, after supplying the two benchmark QC inputs:

```bash
cd /mnt/tank/scratch/kkapranova/MagGenBench-current
PYTHONPATH=src python scripts/illustrations/plot_manuscript_figure2_v2.py \
  --crystalformer-finetuned outputs/crystalformer_finetuned/all_structures.csv \
  --crystallm-finetuned outputs/crystallm_finetuned/all_structures.csv \
  --check-expected
```

Outputs are PNG (450 dpi), PDF and SVG in
`reproduced/analysis_v2_magnetic/figures/`, with basename
`manuscript_figure2_structural_overview_v2_preview`. The same directory
contains `figure2_structural_qc_audit.csv` (counts, denominators, source
paths and verification results) and `figure2_primary_rejection_percent.csv`.
The full scientific export is withheld when any cohort source is missing.
The existing `paper/figures/fig02_structural_overview.pdf` is consequently
preserved until all ten sources are available and the new export is checked.
After inspecting the complete figure, replace only that manuscript PDF
with the reproduced PDF and update only its entry in `SHA256SUMS.txt`.
Figure 1 and all frozen scientific tables are unaffected.

The manuscript source is not present in this checkout. The ready caption
is in `figure2_caption.md`; it describes the complete ten-set figure and
should accompany the replacement artifact, not the old three-panel PDF.
Layout tests use explicitly watermarked synthetic FT rows and are not
scientific results or a replacement manuscript artifact.
