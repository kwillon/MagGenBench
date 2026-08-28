# Descriptor v1 production run

Production Descriptor v1 extraction for the harmonized MagGenBench cohorts.

## Schema
- Descriptor schema: v1
- Output columns: 84
- Descriptor implementation checkpoint: 726b1889
- Descriptor source: CIF recomputation
- Runtime configuration: config/descriptors.yaml
- Magnetic screening element groups: config/magnetism.yaml

## Cohorts

| Cohort | Rows | ok | partial | error |
|---|---:|---:|---:|---:|
| MatterGen baseline | 1657 | 1657 | 0 | 0 |
| Con-CDVAE baseline | 1864 | 1864 | 0 | 0 |
| CrystalFormer baseline | 1083 | 1083 | 0 | 0 |
| CrystaLLM baseline | 98 | 98 | 0 | 0 |
| MatterGen fine-tuned | 1376 | 1376 | 0 | 0 |
| Con-CDVAE fine-tuned | 1299 | 1299 | 0 | 0 |
| Crys-JEPA Base | 1764 | 1764 | 0 | 0 |
| Crys-JEPA Refined | 1543 | 1540 | 3 | 0 |

Total processed structures: 10684.
Total Descriptor v1 errors: 0.

## Crys-JEPA Refined partial rows
Three rows are partial because pymatgen provides no usable atomic_radius value for Xe:
- crysjepa_refined__0388
- crysjepa_refined__1024
- crysjepa_refined__1783

For all three rows, atomic_radius_coverage = 0. Symmetry and local-geometry descriptors completed successfully.

## Baseline provenance
The four baseline models use the previously validated 4702-structure master cohort:
- MatterGen: 1657
- Con-CDVAE: 1864
- CrystalFormer: 1083
- CrystaLLM: 98

tables/04_magnetic_screening/baseline_master_production_annotations.csv is a local reproducible copy of the existing validated inference cohort. Only cif_path was relocated to the current relative samples/... tree; row order, identity, validation/enrichment fields, and all other provenance fields were verified unchanged.

## Integrity
SHA-256 checksums for production descriptor outputs, the baseline production manifest, and runtime configuration are recorded in final_sha256.txt.

## Artifact location

Production Descriptor v1 CSV files are frozen external artifacts and are not
stored under `runs/`.

For Analysis v1 reproduction they are resolved relative to the supplied
artifact root:

`descriptor_v1/<cohort>_descriptors_v1.csv`

The SHA-256 digests in `final_sha256.txt` define the frozen artifact contract.
The `runs/descriptors/v1/` directory contains provenance and run metadata only.
