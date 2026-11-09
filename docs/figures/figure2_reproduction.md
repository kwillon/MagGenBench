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

Local real-source export and audit on 2026-10-12:

| Set | Retained after QC | Population | Retention | Source/status |
|---|---:|---:|---:|---|
| MatterGen Base | 1657 | 2000 | 82.85% | baseline validation CSV |
| MatterGen FT | 1376 | 2000 | 68.80% | `tables/03_features/phase5b_mattergen_finetuned_with_classes.csv` |
| Con-CDVAE Base | 1864 | 2000 | 93.20% | baseline validation CSV |
| Con-CDVAE FT | 1299 | 2000 | 64.95% | `tables/03_features/phase5b_concdvae_finetuned_with_classes.csv` |
| CrystalFormer Base | 1083 | 2000 | 54.15% | baseline validation CSV |
| CrystalFormer FT | 1380 | 2000 | 69.00% | `tables/03_features/phase5b_crystalformer_finetuned_with_classes.csv` |
| CrystaLLM Base | 98 | 2000 | 4.90% | baseline validation CSV |
| CrystaLLM FT | 217 | 2000 | 10.85% | `tables/03_features/phase5b_crystallm_finetuned_with_classes.csv` |
| Crys-JEPA Base | 1764 | 2000 | 88.20% | `tables/03_features/crysjepa_base_with_classes.csv` |
| Crys-JEPA Ref. | 1543 | 2000 | 77.15% | `tables/03_features/crysjepa_refined_with_classes.csv` |

All ten QC sources match the verification targets and sum to 12281.
The original eight sets sum to 10684; structural retention is independent
of coverage in the frozen analysis table.
Crys-JEPA Base has 236 rejected structures: 154 charge-balance failures,
77 implausible interatomic distances and 5 duplicate primary reasons.
Panel D normalizes these counts by 236; every baseline profile sums to 100%.

Final visual refinements label the row "Crys-JEPA Base (n=236)" and use
"Charge-balance failure" and "Implausible interatomic distance".
These are display-only changes: source reason codes, data, category/model
order and 0-100 scales are unchanged. Panel D cell values, categories,
row labels and colorbar ticks use 9 pt instead of 8 pt. Numerical QC and
rejection tables were compared with the pre-refinement results and match.

## Native and local QC inputs

The following server paths are confirmed and remain the CLI defaults;
they do not exist in the local checkout:

- `outputs/crystalformer_finetuned/all_structures.csv`
- `outputs/crystallm_finetuned/all_structures.csv`

The local export instead uses the full QC annotation tables listed above,
available after merging origin/main. Both contain 2000 records, including
rejected rows. No synthetic rows are used in the scientific export.
A 2016-row raw-generation table fails validation; select
the recorded benchmark population using its original harmonization
manifest upstream. Do not truncate rows or divide raw retained counts by
2000.

## Commands

From the repository root, with pandas, matplotlib and the local package
available, reproduce the complete local figure:

```bash
PYTHONPATH=src python scripts/illustrations/plot_manuscript_figure2_v2.py \
  --crystalformer-finetuned tables/03_features/phase5b_crystalformer_finetuned_with_classes.csv \
  --crystallm-finetuned tables/03_features/phase5b_crystallm_finetuned_with_classes.csv \
  --check-expected
```

Add --audit-only to check counts without plotting. An incomplete audit
prints missing paths and exits with status 2. Windows PowerShell:

```powershell
$env:PYTHONPATH = 'src'
uv --cache-dir .uv-cache run --no-project --python 3.11 --with pandas --with matplotlib --with pytest --with pyyaml python scripts/illustrations/plot_manuscript_figure2_v2.py --crystalformer-finetuned tables/03_features/phase5b_crystalformer_finetuned_with_classes.csv --crystallm-finetuned tables/03_features/phase5b_crystallm_finetuned_with_classes.csv --check-expected
uv --cache-dir .uv-cache run --no-project --python 3.11 --with pandas --with matplotlib --with pytest --with pyyaml python -m pytest tests/test_manuscript_figure2_v2.py tests/test_validation_figures_v2.py tests/test_paper_pipeline_v3.py tests/test_manuscript_figure3_v2.py -q
```

Full server reproduction using the confirmed native QC inputs:

```bash
cd /mnt/tank/scratch/kkapranova/MagGenBench-current
PYTHONPATH=src /mnt/tank/scratch/kkapranova/envs/maggenbench-magnetism/bin/python scripts/illustrations/plot_manuscript_figure2_v2.py \
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
The selected `paper/figures/fig02_structural_overview.pdf` now contains the
complete ten-set export. PNG and PDF renders were visually checked, and
only the Figure 2 entry in `SHA256SUMS.txt` was updated. Figures 1 and 3
and all frozen scientific tables are unaffected.

The manuscript source is not present in this checkout. The ready caption
is in `paper/figure_captions.md` (Figure 2); it describes the complete ten-set figure and
accompanies the selected artifact with the updated rejection terminology.
Layout tests use explicitly watermarked synthetic FT rows and are not
scientific results or a replacement manuscript artifact.
