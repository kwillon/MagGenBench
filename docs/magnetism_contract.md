# Magnetism Prediction Contract

## Scope

The Phase 1 magnetism module defines prediction contracts only. It is separate
from `src/mvpipeline/validation/magnetism.py`, which remains elemental
screening.

The module does not import matminer, sklearn, joblib, or model artifacts during
package import.

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
