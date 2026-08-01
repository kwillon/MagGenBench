# Integration Audit Summary

## Current MagGenBench

The working production path is the validation pipeline in `src/mvpipeline`.
It discovers CIF files, parses them with pymatgen, applies sanity, geometry,
charge, novelty, duplicate, and elemental magnetic screening checks, then writes
`all_structures.csv`, `validation_report.json`, and copied validated/rejected
structure trees.

MagGenBench now contains dependency-light energy and magnetism contracts,
lazy real-backend adapters, configuration schemas, and stage runners. Real
model execution remains opt-in and is separated from lightweight package
imports and fake-backend tests.

The existing `src/mvpipeline/validation/magnetism.py` is elemental screening
only. It is intentionally separate from magnetic property prediction.

## Donor Findings

The energy donor provides a simple CLI flow for CIF discovery, ML-potential
total-energy prediction, isolated-atom-reference proxy values, and CSV error
outputs. Its `max(formation_energy_proxy_eV_per_atom, 0)` value is a stability
proxy, not energy above hull.

The magnetic donor predicts a formula-level value from composition-only
Magpie features loaded through a joblib LightGBM model. Historical training
code and the DXMag table establish that the selected target is
`total magnetization (muB/f.u.)`; repeated rows with the same formula are
aggregated by their median before training.

The verified runtime profile therefore reports `moment_unit = "muB"` and
`moment_normalization = "per_formula_unit"`. Generic and fake backends retain
`"unknown"` defaults when equivalent evidence is not available.

The magnetic donor's noisy feature perturbation is an `uncertainty_proxy`, not a
calibrated statistical uncertainty.

## Aichem Runtime Verification

The DXMag artifact was verified on aichem in an isolated Python 3.10
environment with matminer `0.8.0` and pymatgen `2023.8.10`.

The loaded artifact is a `lightgbm.sklearn.LGBMRegressor` with
`n_features_in_ = 132`. The standard Magpie preset in matminer `0.8.0`
produces exactly 132 labels in the externally audited order. Direct
donor-equivalent inference and the MagGenBench sklearn backend produced the
same prediction for `eval_gen_FM1__0000`.

Stage-runner smoke checks also completed successfully:

- `limit=1`: 1 success, 0 failures
- `limit=5`: 5 successes, 0 failures
- observed five-input runtime: approximately 1.17 seconds total

The timing is an environment-specific smoke-test observation, not a performance
benchmark. The binary model and generated smoke CSV files remain outside
version control.

## Windows And Aichem Separation

Local Windows development should be limited to import checks, config/schema
checks, fake-backend tests, and lightweight unit tests. Heavy model execution,
model downloads, CUDA, DFT, relaxation, batch CIF processing, and full donor
backend smoke tests belong on aichem.
