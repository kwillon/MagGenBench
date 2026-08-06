# Phase 5A-2 Enrichment Result Join

## Scope

Phase 5A-2 performs a deterministic tabular join between:

1. the Phase 5A-1 enrichment annotation table;
2. an energy-stage result table;
3. a magnetism-stage result table.

This stage does not load CIF files, compute descriptors, run CHGNet,
run DXMag, download models, or perform DFT calculations. It only
validates and joins existing result tables.

## Inputs

The Phase 5A-1 table must contain non-empty and unique `sample_uid`
and `structure_id` values. For every row:

`sample_uid == structure_id`

Energy and magnetism result tables must contain a non-empty and unique
`structure_id`.

The join relation is:

`annotations.sample_uid == energy.structure_id`

`annotations.sample_uid == magnetism.structure_id`

## Join Policy

The Phase 5A-1 table is the left-hand canonical table.

The stage:

- preserves every Phase 5A-1 row;
- preserves Phase 5A-1 row order;
- does not remove rows without energy or magnetism results;
- rejects duplicate or empty join keys;
- rejects a mismatch between `sample_uid` and `structure_id`;
- rejects result IDs absent from the annotation table by default.

Unknown result IDs can only be ignored through the explicit
`strict_result_ids=False` option.

## Namespaced Fields

All result fields except `structure_id` are namespaced.

Energy examples:

- `energy_join_status`
- `energy_status`
- `energy_backend`
- `energy_model_name`
- `energy_formation_energy_proxy_eV`
- `energy_stability_energy_proxy_eV_per_atom`

Magnetism examples:

- `magnetism_join_status`
- `magnetism_status`
- `magnetism_backend`
- `magnetism_model_name`
- `magnetism_predicted_moment_value`
- `magnetism_moment_unit`
- `magnetism_moment_normalization`

`*_join_status = matched` means that a stage-result row was found. It
does not mean that inference succeeded. Scientific execution status is
preserved separately in `energy_status` or `magnetism_status`.

A missing result is represented by `*_join_status = missing` and empty
namespaced result fields.

## Scientific Naming

Phase 5A-2 copies result values without reinterpretation.

Energy proxy fields are not renamed to DFT formation energy or energy
above hull. Magnetism output is not renamed to saturation magnetization,
magnetic ordering, or a DFT magnetic moment.

## Output

The intended generated table is:

`tables/04_magnetic_screening/master_structures_with_enrichment_results.csv`

Output is written atomically through the shared stage-table writer.

## Validation

The implementation is tested for:

- deterministic row preservation;
- namespaced field collisions;
- matched, missing, successful, and failed stage results;
- duplicate and empty identifiers;
- Phase 5A-1 key mismatch;
- result IDs absent from the canonical table;
- header-only inputs;
- preservation of an existing output after validation failure;
- atomic CSV output.

The integration smoke test used one real Phase 5A-1 annotation row and
synthetic contract-compatible energy and magnetism rows. Synthetic
numeric values from that smoke test are not scientific predictions.
