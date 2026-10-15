# Figure 3 definitions, audit and reproduction

## Implementations and sources

- Plot entry point: `scripts/illustrations/plot_manuscript_figure3_v2.py`.
- Plot implementation: `src/mvpipeline/analysis/manuscript_figure3_v2.py`.
- FT preparation/computation: `scripts/descriptors/run_figure3_ft_descriptors.py`
  and `src/mvpipeline/descriptors/figure3_ft.py`.
- Existing calculator: `scripts/descriptors/run_descriptor_v2_magnetic.py`,
  `src/mvpipeline/descriptors/batch_v2.py` and `extractor_v2.py`.
- Unchanged configuration: `config/descriptors_v2_magnetic.yaml` and
  `config/magnetism.yaml`. The accepted old run is documented in
  `runs/descriptors/magnetic/README.md`, `run.sh`, and `final_sha256.txt`.

After merging origin/main, the existing
`tables/08_standardized_enrichment/standardized_enrichment.csv` has 12281
rows. No enrichment is recalculated. The shared
`tables/09_descriptor_v2_magnetic/descriptor_v2_magnetic.csv` and
`tables/10_analysis_v2_magnetic/analysis_v2_magnetic.csv` remain frozen at
10684 rows. The plotted columns and geometry status agree exactly across
these two old tables. The old descriptor SHA256 is
`7667aad820f859a13b326c1b6d3c76c258ca4b63bc55ef20066ce99d79e11980`.

No separate ready Descriptor v2 FT artifacts were found in the merged
checkout or tracked origin/main files. The DXMag tables are not a substitute.
The new wrapper selects the two FT populations from the ready enrichment
and invokes the same existing batch calculator, with its full 41-column
v2-magnetic schema and row-preserving error handling. It does not change
the scientific calculator, element groups, CIF parser, or neighbor settings.

QC sources for the original eight cohorts:

- Four Base models: `tables/03_features/master_structures_with_classes.csv`,
  filtered by model_name and then status=validated.
- MatterGen FT: `tables/03_features/phase5b_mattergen_finetuned_with_classes.csv`.
- Con-CDVAE FT: `tables/03_features/phase5b_concdvae_finetuned_with_classes.csv`.
- Crys-JEPA: `tables/03_features/crysjepa_base_with_classes.csv` and
  `tables/03_features/crysjepa_refined_with_classes.csv`.

Confirmed server-native QC sources for the two new FT sets:

- `outputs/crystalformer_finetuned/all_structures.csv`: 2000 rows, 1380 validated.
- `outputs/crystallm_finetuned/all_structures.csv`: 2000 rows, 217 validated.

These native files are not in the local checkout. The local real computation
used the corresponding full QC annotation tables, now present after merge:
`tables/03_features/phase5b_crystalformer_finetuned_with_classes.csv` and
`tables/03_features/phase5b_crystallm_finetuned_with_classes.csv`.
All 1597 retained FT CIFs are available locally.

## Identity and reproducibility checks

Each QC source must contain all 2000 harmonized records, validated and
rejected. Raw 2016-row generation tables are rejected. Expected retained
counts are assertions, never substituted for counts from sources.

Native QC structure_id is mapped to canonical sample_uid through the
existing enrichment source_sample_id. The annotation adapter in
`src/mvpipeline/annotations/finetuned.py` preserves the original native
structure_id in this field. For example, CrystalFormer source IDs contain
the run subdirectory, whereas CrystaLLM IDs are CIF filenames. No prefix
guessing, basename-only matching, row-order join or count-only join is used.
Canonical QC annotation IDs are matched directly.

Preparation requires exact retained-ID set equality with enrichment,
unique IDs, sample_uid=structure_id, validated status, expected populations,
and an existing recorded CIF path for every selected row. It resolves
cif_path_original relative to the checkout before falling back to cif_path;
the recorded source paths are not inferred from IDs.

Generated files under `reproduced/figure3_ft_descriptors/`:

- `manifests/{cohort}.csv`: selected existing enrichment, resolved CIF path,
  and qc_structure_id.
- `manifests/{cohort}_qc_ids.csv`: native/canonical ID mapping.
- `{cohort}_descriptor_v2_magnetic.csv`: separate outputs for
  crystalformer_finetuned and crystallm_finetuned; canonical IDs preserved.
- `provenance.json`: input/config/scientific-code/manifest SHA256 values,
  element sets, neighbor settings, runtime Python and dependency versions.

The Figure 3 loader checks unique IDs, out-of-QC IDs, schema, cohort and
fraction ranges, then left-joins descriptors to retained QC populations.
Missing rows remain missing, not zero. With --require-complete-descriptors
every retained ID must have a descriptor row; individual metric failures
are still represented and audited rather than filtered from the population.

## Exact metric definitions

Composition comes from `src/mvpipeline/descriptors/magnetic_composition.py`.
For group G, fraction = sum of elemental compositional amounts in G /
sum of all compositional amounts. Fractional occupancies are included;
this is not a fraction of distinct species or a count of lattice sites.

- A, transition_3d_fraction: Sc, Ti, V, Cr, Mn, Fe, Co, Ni, Cu (not Zn).
- B, configured_lanthanide_fraction: Ce, Pr, Nd, Sm, Eu, Gd, Tb, Dy, Ho,
  Er, Tm, Yb (not La, Pm, Lu).
- A/B prevalence = 100 * positive finite count / available finite count
  within the retained QC population. Genuine zeros remain in this
  denominator. The conditional boxplots contain only positive fractions.
  No available values means undefined prevalence (NA), not 0%.

Geometry comes from `magnetic_geometry.py`; `magnetic_sites.py` classifies
a site as magnetic if any of its species belongs to the configured union
of the A/B groups and Mo, Ru, Rh, Pd, Re, Os, Ir. Site membership is not
occupancy-weighted and does not establish an actual magnetic moment.

C, magnetic_site_magnetic_neighbor_fraction_mean, is the equal mean over
central magnetic sites of unweighted magnetic-neighbor count / total
unweighted coordination. It is not a ratio of mean coordination numbers.
Periodic neighbor images participate. MinimumDistanceNN uses cutoff=10 A,
tolerance=0.1, get_all_sites=false, use_weights=false. Symmetry settings
remain symprec=0.01 and angle_tolerance=5.

A zero total coordination contributes zero in the implementation.
Preliminary checks require both any neighbor and a magnetic neighbor
within cutoff for every central magnetic site before geometry returns ok.
No magnetic sites produces magnetic_geometry_status=not_applicable and
null geometry values. Failures produce error; the extractor also supports
not_computed. C selects only status=ok and a finite fraction, including
genuine zeros. not_applicable, error, not_computed, missing status and
ok-but-missing values are audited separately; finite C values with non-ok
status fail input validation. CHGNet/DXMag success is not a selection rule.

## Real ten-set audit, 2026-10-12

All values below were calculated from real sources, not expected targets.
A/B available counts are listed independently. Percentages are rounded
here; the exported CSV retains full precision.

| Set | QC | A available | A nonzero | A prevalence | B available | B nonzero | B prevalence | C applicable | C not-applicable | C true zero |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MatterGen Base | 1657 | 1657 | 1248 | 75.32% | 1657 | 500 | 30.18% | 1588 | 69 | 714 |
| MatterGen FT | 1376 | 1376 | 1374 | 99.85% | 1376 | 1 | 0.07% | 1376 | 0 | 45 |
| Con-CDVAE Base | 1864 | 1864 | 686 | 36.80% | 1864 | 541 | 29.02% | 1168 | 696 | 977 |
| Con-CDVAE FT | 1299 | 1299 | 1299 | 100.00% | 1299 | 7 | 0.54% | 1299 | 0 | 99 |
| CrystalFormer Base | 1083 | 1083 | 288 | 26.59% | 1083 | 214 | 19.76% | 584 | 499 | 279 |
| CrystalFormer FT | 1380 | 1380 | 1291 | 93.55% | 1380 | 8 | 0.58% | 1310 | 70 | 252 |
| CrystaLLM Base | 98 | 98 | 98 | 100.00% | 98 | 8 | 8.16% | 98 | 0 | 68 |
| CrystaLLM FT | 217 | 217 | 216 | 99.54% | 217 | 4 | 1.84% | 216 | 1 | 21 |
| Crys-JEPA Base | 1764 | 1764 | 653 | 37.02% | 1764 | 477 | 27.04% | 1141 | 623 | 756 |
| Crys-JEPA Ref. | 1543 | 1543 | 142 | 9.20% | 1543 | 341 | 22.10% | 502 | 1041 | 154 |

QC, descriptor rows and A/B available each sum to 12281. A has 7295
positive and 4986 zero values; B has 2101 positive and 10180 zeros.
C has 9282 applicable and 2999 not-applicable records; 3365 applicable
values are genuine zeros. For every cohort, absent descriptor rows,
A/B missing values, geometry errors, not-computed, missing status and
ok-but-missing geometry values are all zero. Both new descriptor tables
have descriptor_v2_status=ok for every row.

The local environment used Python 3.11.15, pymatgen 2026.9.24,
pymatgen-core 2026.10.2, numpy 2.4.6, spglib 2.8.0 and pandas 3.0.6.
The old run does not provide a complete
frozen dependency lock. A compatibility check recalculated three real
structures from each old cohort (24 total): all three Figure 3 fields
matched the old artifact within 1e-12, with identical geometry statuses.
This is a sampled compatibility check, not a full recalculation of the
old artifact. Runtime versions are recorded again for each server run.

The unchanged pymatgen CIF parser emitted coordinate-rounding and
CIF-reported/computed composition warnings for some FT structures.
They were not converted into zeros or missing values; all calculated
fractions use the parsed structure composition, as in the existing v2
calculator. No CIF repairs or scientific-setting changes were introduced.

## Server commands

Run from the updated working branch in the server checkout:

```bash
cd /mnt/tank/scratch/kkapranova/MagGenBench-current
export PYTHONPATH="$PWD/src"
PY=/mnt/tank/scratch/kkapranova/envs/maggenbench-magnetism/bin/python

"$PY" scripts/descriptors/run_figure3_ft_descriptors.py \
  --standardized-input tables/08_standardized_enrichment/standardized_enrichment.csv \
  --config config/descriptors_v2_magnetic.yaml \
  --crystalformer-qc outputs/crystalformer_finetuned/all_structures.csv \
  --crystallm-qc outputs/crystallm_finetuned/all_structures.csv

"$PY" scripts/illustrations/plot_manuscript_figure3_v2.py \
  --input tables/10_analysis_v2_magnetic/analysis_v2_magnetic.csv \
  --qc-input crystalformer_finetuned=outputs/crystalformer_finetuned/all_structures.csv \
  --qc-input crystallm_finetuned=outputs/crystallm_finetuned/all_structures.csv \
  --descriptor-input crystalformer_finetuned=reproduced/figure3_ft_descriptors/crystalformer_finetuned_descriptor_v2_magnetic.csv \
  --descriptor-input crystallm_finetuned=reproduced/figure3_ft_descriptors/crystallm_finetuned_descriptor_v2_magnetic.csv \
  --require-complete-descriptors
```

--prepare-only on the first command validates inputs and writes manifests
without descriptor computation. To call the original calculator directly,
for each cohort pass its manifest to
`scripts/descriptors/run_descriptor_v2_magnetic.py --input MANIFEST --output CSV --config config/descriptors_v2_magnetic.yaml --repo-root .`.
The wrapper uses this same batch implementation.

For local reproduction, replace the two native QC paths in both commands
with `tables/03_features/phase5b_crystalformer_finetuned_with_classes.csv`
and `tables/03_features/phase5b_crystallm_finetuned_with_classes.csv`.
Native-file validation itself must still run on the server; those files
were not fabricated locally.

Exports: PNG (450 dpi), PDF and SVG under
`reproduced/analysis_v2_magnetic/figures/`, basename
`manuscript_figure3_magnetic_domain_v2_preview`, and
`figure3_availability_audit.csv`. --audit-only performs the identity and
availability audit without plotting. The selected manuscript PDF is
`paper/figures/fig03_magnetic_domain.pdf`; PNG and PDF renders were
visually checked. Caption: `figure3_caption.md`.
The manuscript text is outside this checkout.

Figures 1 and 2, shared Descriptor v2/analysis tables, and Figures 4-6
are not recalculated or replaced by this change. Updating other
analytical figures remains a separate task.

Regression verification: 63 tests passed across FT preparation, Figure 3,
Descriptor v2, analysis, Figure 2 and Figure 1 pipeline modules. Coverage
includes native-to-canonical IDs, 2016-row rejection, missing versus zero,
geometry applicability, exact descriptor coverage and fractional occupancy.
The canonical-input test now distinguishes ten-set enrichment from the
unchanged eight-set descriptor artifact; the shared analysis implementation
is not expanded or rebuilt here.
