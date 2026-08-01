# Magnetism Prediction Contract

## Scope

The magnetism module defines prediction contracts and backend adapters. It is
separate from `src/mvpipeline/validation/magnetism.py`, which remains elemental
screening.

The module does not import matminer, sklearn, joblib, or model artifacts during
package import.

The donor implementation uses composition-only Magpie features via
`ElementProperty.from_preset("magpie")`. The Phase 3 sklearn backend preserves
that behavior through the `composition_magpie` feature set, but it does not
claim that the model uses structure geometry.

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
