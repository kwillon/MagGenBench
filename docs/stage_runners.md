# Stage Runners

## Scope

Phase 4 adds a dependency-light orchestration layer for prepared records:

prepared records -> energy stage -> magnetism stage -> structured result records
-> deterministic tabular output.

The runners do not load CIF files, parse structures, download models, or run
real MatGL, CHGNet, sklearn, or matminer predictions. Real structure loading is
left to a later deployment phase and must be injected into the runner as a
typed input preparation step.

## Inputs And Outputs

The energy stage uses `EnergyInput`, `EnergyResult`, `EnergyBackend`, and
`create_energy_backend`.

The magnetism stage uses `MagnetismInput`, `MagnetismResult`,
`MagnetismBackend`, and `create_magnetism_backend`.

Input rows must provide `structure_id`. The stage layer preserves input order
as `input_order` and carries provenance fields such as `source_model`,
`source_path`, `run_id`, and `sample_id` as metadata columns.

## Stage Independence

Energy and magnetism are independent by default. Running the energy stage first
does not make magnetism scientifically dependent on the energy result, and an
energy failure is not automatically converted into a magnetism failure.

## Limit

`limit=None` means all records after resume filtering. `limit=0` produces an
empty planned run. Negative limits are invalid. Limit is applied after resume
filtering so it counts planned new work.

## Dry Run

Dry-run validates runner settings, required identifiers, selected stages,
selected backends, resume filtering, duplicate `structure_id`, and planned
record counts. It does not call `backend.predict`, load models, or create
prediction result rows.

## Resume

Resume accepts known successful `structure_id` values. Only confirmed success
IDs are skipped. Failed IDs are not skipped unless the caller incorrectly marks
them successful, so failed records can be rerun. Duplicate `structure_id` in the
input is rejected because safe deduplication is not defined in this layer.

## Error Policy

The default policy is `continue_on_record_error` (`fail_fast=False`): expected
per-record preparation or backend contract errors become structured failure
records and the batch continues. `KeyboardInterrupt` and `SystemExit` are never
caught. With `fail_fast=True`, record errors are raised immediately.

## Atomic Output

Stage CSV output uses the standard library `csv` module. Files are written to a
temporary path next to the target and atomically replaced after a successful
write. Empty result sets still write a header. Python object repr values are not
serialized.

## Scientific Names

Energy proxy fields keep the `formation_energy_proxy_*` and
`stability_energy_proxy_*` names. They are not energy above hull, DFT energy, or
true formation energy.

Magnetism output keeps `predicted_moment_value`, `moment_unit`,
`moment_normalization`, and `uncertainty_proxy`. It is not reported as Ms,
saturation magnetization, DFT magnetic moment, or magnetic ordering.

## Verified DXMag Magnetism Run

The magnetism runner has been exercised with the real optional sklearn backend
after external input preparation. The verified profile uses the DXMag
LightGBM artifact, 132 ordered Magpie composition features, and strict
compatibility checking with `allow_unsafe_compatibility = false`.

Verified smoke runs:

- one CIF through direct donor-equivalent and backend inference, with identical
  scalar predictions
- `run_magnetism_stage(..., limit=1)`: 1 successful result
- `run_magnetism_stage(..., limit=5)`: 5 successful results and 0 failures
- atomic CSV output containing the expected provenance, prediction, unit,
  normalization, uncertainty proxy, confidence, risk, and model details

The runner preserves finite negative model outputs. It does not silently clip
them to zero. Interpretation or physical filtering belongs to an explicit
downstream policy rather than the backend contract.

## Fake Backend Example

```python
from mvpipeline.pipeline.enrichment import run_enrichment

records = [
    {
        "structure_id": "s1",
        "n_atoms": 2,
        "composition": {"Fe": 1, "O": 1},
        "features": [1.0, 2.0],
        "source_model": "demo",
    }
]

report = run_enrichment(records)
```
