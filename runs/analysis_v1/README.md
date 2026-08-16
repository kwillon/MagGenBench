# Unified Analysis v1

This run assembles the current MagGenBench analysis-ready dataset by strict sample_uid join of Descriptor v1 outputs with CHGNet energy and DXMag magnetism results.

## Output

- unified_analysis_v1.csv: 10684 rows, 124 columns
- sample_uid is unique for all 10684 rows
- sample_uid == structure_id for all rows
- no rows are dropped because of partial descriptor or downstream error status

## Cohorts

- baseline_master: 4702
- mattergen_finetuned: 1376
- concdvae_finetuned: 1299
- crysjepa_base: 1764
- crysjepa_refined: 1543

Baseline analysis_family is resolved row-wise from model_name, preserving MatterGen, Con-CDVAE, CrystalFormer, and CrystaLLM as separate model families.
Crys-JEPA is retained as an additional comparator family with base and refined analysis states.

## Status audit

- Descriptor v1: 10681 ok, 3 partial, 0 error
- CHGNet energy: 10680 ok, 4 error
- DXMag magnetism: 10684 ok

The three Descriptor v1 partial rows are crysjepa_refined__0388, crysjepa_refined__1024, and crysjepa_refined__1783.
For all three, descriptor_v1_error_code=partial_descriptor_result and descriptor_v1_error_message=element_property_incomplete_coverage:atomic_radius; atomic_radius_coverage=0 and the affected atomic-radius statistics remain empty.

The four CHGNet error rows are retained with empty energy values while their successful DXMag results are preserved.

## Scientific interpretation

energy_total_energy_eV and energy_total_energy_eV_per_atom are CHGNet-predicted total energies. They are not formation energies, energies above hull, or direct thermodynamic-stability metrics.
magnetism_predicted_moment_value is the raw DXMag regression output in muB per formula unit. Small negative predictions are preserved and are not silently clipped.
DXMag predictions do not establish magnetic order.

## Implementation

- Descriptor v1 implementation checkpoint: 726b1889
- Descriptor v1 production provenance checkpoint: 51d7f1ee
- unified builder: src/mvpipeline/analysis/unified.py
- production CLI: scripts/analysis/build_unified_analysis_v1.py
- tests: tests/test_unified_analysis.py
- targeted unified-analysis tests: 7 passed

The generated unified_analysis_v1.csv is a run artifact and is not intended to be committed to Git.
