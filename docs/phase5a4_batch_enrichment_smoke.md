# Phase 5A-4: real batch enrichment smoke test

Phase 5A-4 extends the one-structure real enrichment validation from
Phase 5A-3 to a deterministic batch of 10 structures.

## Batch selection

The smoke manifest contains the first 10 source-order rows from

`tables/04_magnetic_screening/master_structures_with_enrichment_annotations.csv`

satisfying:

- `status == validated`
- `cif_load_status in {ok, ok_with_warnings}`

The selection is technical and deterministic. It is not a scientific
ranking or magnetic-candidate filter.

## Real backends

Energy:

- backend: CHGNet
- model selector: default
- runtime device for this smoke: CPU
- input rows: 10
- successful rows: 10
- error rows: 0

Magnetism:

- backend: sklearn
- model: dxmag-lightgbm-composition
- feature set: 132 composition Magpie features
- input rows: 10
- successful rows: 10
- error rows: 0

The DXMag backend predicts total magnetization normalized per formula
unit. It is composition-based and therefore does not distinguish
polymorphs with identical composition.

## Strict enrichment join

Inputs:

- 10 annotation rows
- 10 CHGNet result rows
- 10 DXMag result rows

Result:

- energy matched: 10
- energy missing: 0
- unmatched energy results: 0
- magnetism matched: 10
- magnetism missing: 0
- unmatched magnetism results: 0
- output rows: 10
- unique structure IDs: 10
- annotation columns: 44
- joined columns: 70
- added result columns: 26

The strict join completed with:

`PHASE5A4_BATCH_JOIN: PASSED`

## Example joined record

For

`cdvae__eval_gen_FM__eval_gen_FM0.pt__eval_gen_FM0_0000`

the batch smoke produced:

- CHGNet total energy: -59.22713851928711 eV
- CHGNet total energy per atom: -3.7016961574554443 eV/atom
- DXMag predicted moment: 1.3444389979868376 muB/f.u.
- DXMag uncertainty proxy: 0.06482005634171935
- DXMag confidence score: 0.7952380442544946
- DXMag risk level: low

These values are recorded as smoke-test outputs and are not interpreted
here as final scientific validation results.

## Scope

Phase 5A-4 demonstrates that the real CHGNet and DXMag backends can
process the same multi-structure manifest and that their outputs can be
strictly joined back to the annotation table without dropped,
duplicated, or unmatched structure IDs.

Generated Phase 5A-4 CSV artifacts are excluded from version control.
