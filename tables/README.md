# Tables

This directory contains tabular artifacts used as frozen inputs, provenance, or
historical context for MagGenBench workflows. Most CSV files here are generated
artifacts, not hand-curated source data.

## Current Roles

- `01_master/`: master/input tabular artifacts from earlier benchmark assembly.
- `02_validation/`: structural-validation outputs and provenance tables.
- `03_features/`: annotation and compound-classification stage artifacts.
- `04_magnetic_screening/`: canonical joined cohort inputs and production
  annotation tables used by current Analysis v1 and frozen workflows.
- `05_relaxation/`: historical relaxation-input artifacts; these are not part
  of lightweight Analysis v1 reproduction.
- `06_energy/`: frozen CHGNet energy-stage outputs.
- `07_magnetic_descriptors/`: frozen DXMag/magnetism-stage outputs.
- `legacy/`: retained historical artifacts, including some exact duplicates,
  preserved for provenance and compatibility.

## Frozen Names And Duplicates

Some files retain historical names because their exact paths participate in
run recipes, frozen provenance, or checksum contracts. Do not rename these only
for aesthetics before scientific freeze. This includes:

- `phase5b_*_joined.csv`
- `phase5b_*_production_annotations.csv`
- `phase5b_*_chgnet.csv`
- `phase5b_*_dxmag.csv`

Some apparently redundant files remain because they record historical pipeline
stages or preserve compatibility with earlier scripts and provenance records.
For example, the repository currently retains exact duplicate pairs across
active-looking and `legacy/` locations. These duplicates should be removed only
after a dedicated compatibility audit proves they have no independent value.

## Future Naming

New tabular artifacts should use semantic, versioned names:

- semantic role first;
- scientific version where applicable;
- cohort name where applicable;
- no development-phase numbering;
- no `final2`, `copy`, `new`, `updated`, or temporary-style names.

Examples:

- `<cohort>_descriptors_v2.csv`
- `<cohort>_joined.csv`
- `publication_<analysis>_v1.csv`

Frozen v1 artifacts are not renamed retroactively to match this convention.
