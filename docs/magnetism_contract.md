# Magnetism Prediction Contract

## Scope

The magnetism module defines prediction contracts and backend adapters. It is
separate from `src/mvpipeline/validation/magnetism.py`, which remains elemental
screening.

The module does not import matminer, sklearn, joblib, or model artifacts during
package import.

The verified DXMag profile uses composition-only Magpie features via
`ElementProperty.from_preset("magpie")`. The sklearn backend preserves that
behavior through the `composition_magpie` feature set. It does not claim that
the model uses structure geometry.

## Input

Required fields:

- `structure_id`: shared identifier used across pipeline stages
- `structure`: in-memory structure object supplied by existing MagGenBench IO
- `composition`: mapping from element symbol to amount
- `features`: optional explicit feature vector from a later feature builder

## Output

Every `MagnetismResult` contains:

- `structure_id`
- `status`
- `error_code`
- `error_message`
- `backend`
- `model_name`
- `predicted_moment_value`
- `moment_unit`
- `moment_normalization`
- `uncertainty_proxy`
- `confidence_score`
- `risk_level`

`moment_unit` and `moment_normalization` default to `"unknown"` until model
metadata proves the target and units. `predicted_moment_value` must not be
presented as magnetic ordering, saturation magnetization, Curie temperature, or
DFT magnetic moment unless a backend documents that target.

`uncertainty_proxy` is a proxy, not calibrated statistical uncertainty.

## Verified DXMag Runtime Profile

The optional sklearn profile in `config/magnetism.yaml` documents the verified
DXMag model deployment:

- model class: `lightgbm.sklearn.LGBMRegressor`
- donor commit: `1b29ec689054ef51fe739607d63fa0f57e6f6bb8`
- artifact path: `models/magnetism/magmom_model_dxmag.pkl`
- artifact SHA-256:
  `a76d22393b4f7a2a32e9d57191ea88788a0e5596f262ee0048cc2a9a0facb936`
- feature set: 132 ordered Magpie composition features from matminer `0.8.0`
- feature-order SHA-256:
  `8fdff659a05332499424f1f81e4817dd332cc60f2c8bd04b5b9620b66fd88344`
- target: median DXMag `total magnetization (muB/f.u.)` grouped by formula
- output unit: `muB`
- output normalization: `per_formula_unit`

This is a composition-only ML prediction of a formula-level target. It is not
a structure-dependent DFT magnetic moment, saturation magnetization, magnetic
ordering label, Curie temperature, or moment per atom.

The binary artifact is excluded from Git. The verified sklearn profile is also
not selected by default: prediction remains disabled and the configured
default backend remains the deterministic fake backend. Negative finite
regression outputs are preserved as raw model predictions rather than silently
clipped.

## Backend Metadata

Production backends must carry model metadata:

- `model_name`
- `model_version`
- `artifact_path`
- `artifact_sha256`
- `feature_set`
- `feature_labels`
- `feature_count`
- `target_name`
- `moment_unit`
- `moment_normalization`
- `sklearn_version`
- `matminer_version`

`artifact_path` must come from configuration or runtime settings and must be a
relative path. Binary model artifacts are not stored in Git.

If metadata does not provide the exact feature order, the sklearn backend must
return a structured error unless `allow_unsafe_compatibility` was explicitly
enabled after external verification.

## Sklearn Backend

The sklearn backend accepts `MagnetismInput` and returns `MagnetismResult`.
Model loading is injectable and lazy; the default loader imports `joblib` only
when prediction is attempted. Featurization is injectable and lazy; the default
composition feature provider imports matminer only when features are built.

Before `model.predict`, the backend checks that the model exposes `predict`,
the feature vector is non-empty, the feature count matches metadata or
`model.n_features_in_` when available, and all feature values are finite. Model
prediction output must be convertible to one finite scalar.

The prediction is reported only as `predicted_moment_value` with explicit
`moment_unit` and `moment_normalization`. Defaults remain `"unknown"` until
metadata proves otherwise.
