# Integration Audit Summary

## Current MagGenBench

The working production path is the validation pipeline in `src/mvpipeline`.
It discovers CIF files, parses them with pymatgen, applies sanity, geometry,
charge, novelty, duplicate, and elemental magnetic screening checks, then writes
`all_structures.csv`, `validation_report.json`, and copied validated/rejected
structure trees.

MagGenBench does not yet have a production energy module. `config/energy.yaml`
was previously empty, and energy-related behavior only existed in legacy scripts
or in donor code.

The existing `src/mvpipeline/validation/magnetism.py` is elemental screening
only. It is intentionally separate from magnetic property prediction.

## Donor Findings

The energy donor provides a simple CLI flow for CIF discovery, ML-potential
total-energy prediction, isolated-atom-reference proxy values, and CSV error
outputs. Its `max(formation_energy_proxy_eV_per_atom, 0)` value is a stability
proxy, not energy above hull.

The magnetic donor predicts a magnetic-moment-like value from composition-only
Magpie features loaded through a joblib model. The donor code does not establish
the exact target normalization or unit, so MagGenBench records
`moment_unit = "unknown"` and `moment_normalization = "unknown"` by default.

The magnetic donor's noisy feature perturbation is an `uncertainty_proxy`, not a
calibrated statistical uncertainty.

## Windows And Aichem Separation

Local Windows development should be limited to import checks, config/schema
checks, fake-backend tests, and lightweight unit tests. Heavy model execution,
model downloads, CUDA, DFT, relaxation, batch CIF processing, and full donor
backend smoke tests belong on aichem.
