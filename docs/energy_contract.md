# Energy Contract

## Scope

The Phase 1 energy module defines contracts only. It does not import MatGL,
CHGNet, torch, or any model package, and it does not run real predictions.

## Input

Required fields:

- `structure_id`: shared identifier used across pipeline stages
- `structure`: in-memory structure object supplied by existing MagGenBench IO
- `n_atoms`: positive atom count
- `composition`: mapping from element symbol to amount

## Output

Every energy result contains:

- `structure_id`
- `status`
- `error_code`
- `error_message`
- `backend`
- `model_name`
- `energy_unit`
- `total_energy_eV`
- `total_energy_eV_per_atom`
- `formation_energy_proxy_eV`
- `formation_energy_proxy_eV_per_atom`
- `stability_energy_proxy_eV_per_atom`

`formation_energy_proxy_*` values are isolated-atom-reference proxies. They are
not true formation energies. `stability_energy_proxy_eV_per_atom` is
`max(formation_energy_proxy_eV_per_atom, 0)` and must not be labeled as
`e_above_hull`.

## Backend Contract

Backends implement `EnergyBackend.predict(item: EnergyInput) -> EnergyResult`.
Backends should return structured error results instead of exposing backend
exceptions to downstream pipeline stages.
