# Standardized enrichment reference run

This post-Analysis-v1 checkpoint exists because the frozen Analysis v1
provenance stores baseline energy/magnetism differently from the newer
fine-tuned and Crys-JEPA cohorts. The scientific results are already present
in Analysis v1, but the artifact layout is visually asymmetric.

The standardized enrichment run evaluates all eight current cohorts through
the same current CHGNet and DXMag workflow and publishes symmetric
per-cohort artifacts plus one convenient master table:

`tables/08_standardized_enrichment/standardized_enrichment.csv`

Analysis v1 is not replaced or rewritten. Descriptor v1 is unchanged, and
Descriptor v2 has not been added. The standardized master is the
human-readable post-v1 interface for per-structure energy and magnetism
inspection; stage/source artifacts remain provenance.

## Cohorts

| Cohort | Rows |
| --- | ---: |
| `mattergen_baseline` | 1657 |
| `mattergen_finetuned` | 1376 |
| `concdvae_baseline` | 1864 |
| `concdvae_finetuned` | 1299 |
| `crystalformer_baseline` | 1083 |
| `crystallm_baseline` | 98 |
| `crysjepa_base` | 1764 |
| `crysjepa_refined` | 1543 |

Total rows: `10684`.

`structure_id` and `sample_uid` are unique for all rows, and
`sample_uid == structure_id` for every row. `formula_reduced` and
`formula_full_canonical` are populated for all `10684` rows.

## Status Contract

CHGNet:

- rows: `10684`
- `ok`: `10680`
- `error`: `4`

The four CHGNet error structure IDs are exactly:

- `cf__cf_repr_v1__cf_repr_v1_s19_000095`
- `cf__cf_repr_v1__cf_repr_v1_s20_000074`
- `cf__cf_repr_v1__cf_repr_v1_s20_000093`
- `cllm__crystallm_benchmark_30x100_seed1337_t08_k10__Nd2Fe14B__sample_88`

DXMag:

- rows: `10684`
- `ok`: `10684`
- `error`: `0`

Reference master SHA-256:

`8a62cc9720de9249cdb2c6ce929fa3f98e065ef93c881c1c1160d330940db02d`

Exact SHA identity is the reference snapshot contract. Future CHGNet reruns
on other hardware/runtime environments may show small floating-point drift.
The observed standardized-vs-frozen tolerance in this run was:

- max absolute total-energy delta: `0.000152587890625 eV`
- max absolute per-atom-energy delta: `7.62939453125e-06 eV/atom`
- status identities matched exactly
- CHGNet error IDs matched exactly

DXMag reproduced exactly for all rows:

- max absolute moment delta: `0.0`

## Scientific Caveats

CHGNet values are ML-predicted total energies. They are not DFT formation
energies, energy above hull, or proof of thermodynamic stability. Fields named
`formation_energy_proxy` or `stability_energy_proxy` remain proxies only.

DXMag is a composition-based ML magnetic-moment prediction. It does not
establish FM, AFM, FIM, or other magnetic ordering.

Crys-JEPA remains a comparator cohort, not a fifth core baseline model family.

## Reproduction Recipe

`run.sh` writes generated outputs under:

`reproduced/standardized_enrichment/`

Override paths with:

- `MAGGENBENCH_ROOT`
- `MAGGENBENCH_ENERGY_PY`
- `MAGGENBENCH_MAGNETISM_PY`
- `MAGGENBENCH_OUTPUT_ROOT`
- `MAGGENBENCH_CHECKPOINT_EVERY`

The recipe prepares deterministic manifests, splits the baseline master by
model, snapshots current production manifests into the generated output area,
runs CHGNet and DXMag batch stages, performs strict joins, builds the
87-column master table, validates invariants, and emits an output
`SHA256SUMS.txt`.

Tracked reference artifact hashes are recorded in `final_sha256.txt`.
