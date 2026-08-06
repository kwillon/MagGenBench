# Phase 5A-3 Real Enrichment Smoke Run

## Scope

Phase 5A-3 verifies the real enrichment path for one validated generated
crystal structure:

    Phase 5A-1 annotations
    -> real CHGNet energy prediction
    -> real DXMag composition-based magnetism prediction
    -> strict Phase 5A-2 result join

This is a one-structure deployment smoke run, not a full-dataset scientific
evaluation.

## Verified input

- structure ID:
  `cdvae__eval_gen_FM__eval_gen_FM0.pt__eval_gen_FM0_0000`
- source model: `Con-CDVAE`
- CIF:
  `samples/concdvae_cifs/eval_gen_FM0/eval_gen_FM0__0000.cif`
- reduced formula: `Na6Yb(FeSn2)3`
- number of sites: `16`
- Phase 5A-1 status: `validated`
- magnetic screening status: `candidate`

The CIF-derived composition is Na6 Yb1 Fe3 Sn6.

## Runtime separation

Real energy and magnetism inference use separate conda environments:

- CHGNet:
  `/mnt/tank/scratch/kkapranova/envs/maggenbench-energy`
- DXMag:
  `/mnt/tank/scratch/kkapranova/envs/maggenbench-magnetism`

Verified energy runtime:

- Python 3.11.15
- CHGNet 0.4.2
- PyTorch 2.11.0+cu128
- pymatgen 2026.5.4
- CUDA available

Verified magnetism runtime:

- Python 3.10.20
- LightGBM 4.7.0
- scikit-learn 1.7.2
- matminer 0.8.0
- pymatgen 2023.8.10
- NumPy 1.26.4

The DXMag artifact is:

    models/magnetism/magmom_model_dxmag.pkl

Its verified SHA-256 is:

    a76d22393b4f7a2a32e9d57191ea88788a0e5596f262ee0048cc2a9a0facb936

The loaded artifact is a LightGBM regressor using 132 ordered Magpie
composition features.

## Reproduction

Run from the repository root:

    bash scripts/phase5a3/run_phase5a3_real_enrichment.sh

The orchestrator sequentially runs:

1. CHGNet in the energy environment;
2. DXMag in the magnetism environment;
3. the strict Phase 5A-2 result join.

## Verified CHGNet result

The CHGNet stage completed with `status=ok`.

- resolved checkpoint: CHGNet 0.3.0
- output semantics: `energy_per_atom_eV`
- predicted energy: approximately `-3.7016965 eV/atom`
- predicted total energy: approximately `-59.22714 eV`

Two CUDA smoke runs differed by approximately `2.4e-7 eV/atom`.
Therefore exact CSV hashes are not treated as a reproducibility requirement.
The required checks are successful status, valid schema, matching structure ID,
and numerical agreement within an explicitly selected tolerance.

No isolated-atom reference provider was supplied. Consequently,
`formation_energy_proxy_*` and `stability_energy_proxy_*` are empty.

The CHGNet value is not reported as formation energy, energy above hull,
or DFT validation.

## Verified DXMag result

The DXMag stage completed with `status=ok`.

- model: `dxmag-lightgbm-composition`
- predicted moment: `1.3444389979868376 muB/f.u.`
- uncertainty proxy: `0.06482005634171935`
- confidence score: `0.7952380442544946`
- risk level: `low`

DXMag is composition-only. Its result is not a DFT magnetic moment,
saturation magnetization, magnetic ordering, Curie temperature, or a
structure-sensitive distinction between polymorphs.

## Verified strict join

The strict join completed successfully with:

- 1 Phase 5A-1 annotation row;
- 1 matched CHGNet result;
- 1 matched DXMag result;
- 0 missing results;
- 0 unmatched result IDs;
- 1 output row;
- 44 annotation columns expanded to 70 joined columns.

## Generated outputs

The smoke run writes:

- `tables/06_energy/phase5a3_chgnet_one_row.csv`
- `tables/07_magnetic_descriptors/phase5a3_dxmag_one_row.csv`
- `tables/04_magnetic_screening/phase5a3_real_enrichment_one_row.csv`

These runtime-generated CSV files are excluded from Git. Scripts,
documentation, configuration, and contracts remain version-controlled.
