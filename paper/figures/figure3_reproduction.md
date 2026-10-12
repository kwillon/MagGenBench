# Figure 3 definitions, audit and server reproduction

## Implementation and source provenance

Entry point: `scripts/illustrations/plot_manuscript_figure3_v2.py`.
Implementation: `src/mvpipeline/analysis/manuscript_figure3_v2.py`.
The original figure consumed
`tables/10_analysis_v2_magnetic/analysis_v2_magnetic.csv`, using shared
eight-cohort plotting helpers in `figures_v2_magnetic.py`. It calculated
prevalence and distributions from data; no outcome values were hardcoded.

The three columns come from
`tables/09_descriptor_v2_magnetic/descriptor_v2_magnetic.csv`.
`src/mvpipeline/analysis/magnetic_v2.py` joins them by structure identity
into the analysis table. A local audit on 2026-10-12 confirmed exact equality
of all three plotted columns and magnetic_geometry_status between these
tables for all 10684 records. All descriptor_v2_status values are ok; this
does not mean that magnetic geometry is applicable to every record.

The updated generator keeps the analysis table as its default descriptor
source and also accepts the primary descriptor table through --input.
Two supplemental descriptor CSVs and per-cohort QC tables can be supplied
without changing frozen eight-cohort data or shared plotting constants.
It does not filter by CHGNet, DXMag or overall descriptor success: each
metric is selected by its own finite value and, for C, geometry status.

QC populations are independently read from:

- Four Base sets: `tables/03_features/master_structures_with_classes.csv`,
  selected by model_name; only status=validated identifiers are retained.
- MatterGen FT:
  `tables/03_features/phase5b_mattergen_finetuned_with_classes.csv`.
- Con-CDVAE FT:
  `tables/03_features/phase5b_concdvae_finetuned_with_classes.csv`.
- Crys-JEPA Base/Refined:
  `tables/03_features/crysjepa_base_with_classes.csv` and
  `tables/03_features/crysjepa_refined_with_classes.csv`.

Each QC input must represent all 2000 harmonized benchmark records
(validated and rejected), not the raw generation population of 2016.
Descriptor IDs are checked against the retained QC IDs. Duplicate or
out-of-population IDs fail validation. Missing descriptor records remain
in the QC population through a left join and count as missing, not zero.
No row-order matching, filename-prefix guessing or count-only join is used.
sample_uid is preferred; structure_id is accepted when it is already
the same identifier used by the descriptor table.

## Exact definitions

The composition implementation is
`src/mvpipeline/descriptors/magnetic_composition.py`.
For group G, the fraction is sum of compositional amounts of elements in
G divided by sum of all compositional amounts. This uses occupancies,
not the number of distinct chemical species.

- A: transition_3d_fraction, with G = Sc, Ti, V, Cr, Mn, Fe, Co, Ni, Cu.
  Zn is not in the configured group.
- B: configured_lanthanide_fraction, with G = Ce, Pr, Nd, Sm, Eu, Gd, Tb,
  Dy, Ho, Er, Tm, Yb. La, Pm and Lu are not included.
- A/B prevalence = 100 * nonzero count / available finite count among
  QC-retained structures. The lower boxplots use only fraction > 0.
  If no finite values are available, prevalence is undefined (NA), not 0%.
  True zero values contribute to the prevalence denominator.

The geometry implementation is
`src/mvpipeline/descriptors/magnetic_geometry.py`, with magnetic-site
selection in `magnetic_sites.py`. Settings come from
`config/descriptors_v2_magnetic.yaml` and `config/magnetism.yaml`.

- Configured magnetic elements are the union of the A/B groups and
  Mo, Ru, Rh, Pd, Re, Os, Ir. A site is classified as magnetic if any
  of its species belongs to this union; site membership is not
  occupancy-weighted and does not assert an actual magnetic moment.
- C: magnetic_site_magnetic_neighbor_fraction_mean =
  mean over configured central magnetic sites of
  (unweighted magnetic-neighbor count / unweighted total coordination).
  It is a mean of site-level ratios, not the ratio of two mean coordination
  numbers. Periodic neighbor images participate.
- MinimumDistanceNN uses cutoff=10 A, tolerance=0.1,
  get_all_sites=false and use_weights=false. The nearest-neighbor shell
  uses the nearest distance and its relative tolerance. A zero total
  coordination contributes 0 in the implementation.
- No configured magnetic sites yields magnetic_geometry_status=not_applicable
  and null geometry descriptors. Geometry computation failures yield error;
  the extractor also supports not_computed. Its preliminary nearest-neighbor
  checks require both any neighbor and a magnetic neighbor within cutoff
  for every central magnetic site before returning ok.
- C includes status=ok and finite fraction, including true zeros.
  not_applicable, error, not_computed, missing status and ok-but-missing
  fractions are audited separately. Finite geometry fractions associated
  with non-ok statuses are rejected as inconsistent input.

## Local verification table

A/B available is shown separately even where both counts equal QC count.
Percentages are rounded here; exported audit CSV retains full precision.
A dash means no verified source, not zero. The previous expected QC
targets for the two new FT cohorts do not populate this table.

| Set | QC | A available | A nonzero | A prevalence | B available | B nonzero | B prevalence | C applicable | C not-applicable | C true zero |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MatterGen Base | 1657 | 1657 | 1248 | 75.32% | 1657 | 500 | 30.18% | 1588 | 69 | 714 |
| MatterGen FT | 1376 | 1376 | 1374 | 99.85% | 1376 | 1 | 0.07% | 1376 | 0 | 45 |
| Con-CDVAE Base | 1864 | 1864 | 686 | 36.80% | 1864 | 541 | 29.02% | 1168 | 696 | 977 |
| Con-CDVAE FT | 1299 | 1299 | 1299 | 100.00% | 1299 | 7 | 0.54% | 1299 | 0 | 99 |
| CrystalFormer Base | 1083 | 1083 | 288 | 26.59% | 1083 | 214 | 19.76% | 584 | 499 | 279 |
| CrystalFormer FT | - | - | - | - | - | - | - | - | - | - |
| CrystaLLM Base | 98 | 98 | 98 | 100.00% | 98 | 8 | 8.16% | 98 | 0 | 68 |
| CrystaLLM FT | - | - | - | - | - | - | - | - | - | - |
| Crys-JEPA Base | 1764 | 1764 | 653 | 37.02% | 1764 | 477 | 27.04% | 1141 | 623 | 756 |
| Crys-JEPA Ref. | 1543 | 1543 | 142 | 9.20% | 1543 | 341 | 22.10% | 502 | 1041 | 154 |

For the eight available cohorts: QC and A/B available counts sum to 10684;
C applicable = 7756, not-applicable = 2928, true zero among applicable =
3092. There are no missing composition values, absent descriptor records,
geometry errors, not-computed records or ok-but-missing geometry values.
The generated audit reports these quantities per cohort without merging
them into the zero category.

The previous Figure 3 wrapper removed the C sample-size tick labels and
the old helper displayed absent composition data as 0% prevalence. The
new generator retains C population sizes and displays undefined prevalence
as NA. Shared helpers and Figures 1/2 are unchanged.

## Missing sources

These four configured expected files are absent locally. Their names are
input defaults, not a claim that these exact files exist on the server:

- `tables/03_features/phase5b_crystalformer_finetuned_with_classes.csv`
- `tables/03_features/phase5b_crystallm_finetuned_with_classes.csv`
- `tables/09_descriptor_v2_magnetic/crystalformer_finetuned_descriptor_v2_magnetic.csv`
- `tables/09_descriptor_v2_magnetic/crystallm_finetuned_descriptor_v2_magnetic.csv`

The two QC files need unique sample_uid (or already aligned structure_id)
and status for the entire 2000-row benchmark population. Native validation
outputs can be used only if their IDs already match the descriptor IDs;
otherwise supply the recorded standardized identity mapping upstream.

Each descriptor file must contain analysis_cohort, sample_uid (or aligned
structure_id), the three plotted columns and magnetic_geometry_status.
Use the same Magnetic Descriptor v2 configuration as the frozen sources.
If descriptor_v2_schema_version is present, it must be v2-magnetic.
A descriptor file may be incomplete: missing retained IDs are counted
explicitly. Do not prefilter it to nonzero or applicable rows.
The generator cannot infer descriptor values from the expected QC counts.
If no descriptor outputs exist on the server either, they must first be
computed from correctly standardized FT structure manifests and CIFs via
`scripts/descriptors/run_descriptor_v2_magnetic.py`; those new FT manifests
are also unavailable in this checkout.

## Reproduction

Audit the local checkout without an incomplete figure:

```bash
PYTHONPATH=src python scripts/illustrations/plot_manuscript_figure3_v2.py --audit-only
```

This writes
`reproduced/analysis_v2_magnetic/figures/figure3_availability_audit.csv`,
prints ten rows and the missing sources, and exits with status 2 while
sources are absent. QC counts and A/B counts are nullable integers;
undefined prevalence and unverified cohorts stay missing.

Full server export, after supplying the four inputs (substitute actual
paths in the overrides if server filenames differ):

```bash
cd /mnt/tank/scratch/kkapranova/MagGenBench-current
PYTHONPATH=src python scripts/illustrations/plot_manuscript_figure3_v2.py \
  --input tables/10_analysis_v2_magnetic/analysis_v2_magnetic.csv \
  --qc-input crystalformer_finetuned=tables/03_features/phase5b_crystalformer_finetuned_with_classes.csv \
  --qc-input crystallm_finetuned=tables/03_features/phase5b_crystallm_finetuned_with_classes.csv \
  --descriptor-input crystalformer_finetuned=tables/09_descriptor_v2_magnetic/crystalformer_finetuned_descriptor_v2_magnetic.csv \
  --descriptor-input crystallm_finetuned=tables/09_descriptor_v2_magnetic/crystallm_finetuned_descriptor_v2_magnetic.csv
```

Alternatively, --input can name an already combined ten-cohort analysis
or descriptor table; omit supplemental --descriptor-input arguments for
cohorts already present there. All ten QC populations are still required.

Outputs: PNG at 450 dpi, PDF and SVG under
`reproduced/analysis_v2_magnetic/figures/`, basename
`manuscript_figure3_magnetic_domain_v2_preview`, plus the availability CSV.
No frozen table is modified. The existing selected
`paper/figures/fig03_magnetic_domain.pdf` remains unchanged until all inputs
are supplied and the scientific export is inspected. The updated caption
is in `figure3_caption.md`; the manuscript source is outside this checkout.

Layout tests export only a watermarked synthetic-FT fixture, never a
replacement scientific artifact. Verification on Windows PowerShell:

```powershell
$env:PYTHONPATH = 'src'
uv --cache-dir .uv-cache run --no-project --with pandas --with matplotlib --with pytest python -m pytest tests/test_manuscript_figure3_v2.py tests/test_manuscript_figure2_v2.py tests/test_paper_pipeline_v3.py -q
```

