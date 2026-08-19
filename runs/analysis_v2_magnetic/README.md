# Analysis v2 magnetic

Analysis v2 magnetic is a generated, post-v1 integration dataset. It performs
a strict deterministic one-to-one join of two accepted canonical layers:

- `tables/08_standardized_enrichment/standardized_enrichment.csv`
- `tables/09_descriptor_v2_magnetic/descriptor_v2_magnetic.csv`

The output is generated under:

`reproduced/analysis_v2_magnetic/analysis_v2_magnetic.csv`

The accepted canonical Analysis v2 magnetic artifact is:

`tables/10_analysis_v2_magnetic/analysis_v2_magnetic.csv`

Its SHA-256 contract is recorded in `final_sha256.txt`:

`221deb82b2ac3e5442b4930dd9dcf05dc411e46244f1ce80a401a7d6775bc181`

## Contract

The standardized enrichment input has `10684` rows and `87` columns. The
Magnetic Descriptor v2 input has `10684` rows and `41` columns.

The inputs overlap in exactly these ten columns:

- `analysis_cohort`
- `analysis_family`
- `analysis_state`
- `structure_id`
- `sample_uid`
- `model_name`
- `model_short`
- `formula_reduced`
- `formula_full_canonical`
- `cif_path`

The generated Analysis v2 magnetic table has `10684` rows and `118` columns:

`87 + 41 - 10 = 118`

The output keeps the standardized-enrichment version of the ten shared
identity columns and appends only the 31 Descriptor-v2-specific columns. It
does not create `_x`, `_y`, or duplicate identity columns.

Server acceptance confirmed that the first 87 output columns preserve the
standardized enrichment schema and values exactly, and that the appended 31
Descriptor-v2-specific columns preserve Descriptor v2 values exactly.

## Join Semantics

`structure_id` is the primary join key. Both inputs must have unique
`structure_id` and unique `sample_uid`, and `sample_uid == structure_id` for
every row. Both inputs must contain exactly the same `structure_id` and
`sample_uid` sets.

For every matched structure, all ten overlapping columns must agree exactly.
Any mismatch fails loudly. The output preserves the row order of
`standardized_enrichment.csv`.

## Cohort Coverage

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

Total: `10684`.

## Accepted Status Counts

- `descriptor_v2_status`: `ok = 10684`
- `magnetic_geometry_status`: `ok = 7756`, `not_applicable = 2928`
- `magnetic_symmetry_status`: `ok = 10684`
- `energy_status`: `ok = 10680`, `error = 4`
- `magnetism_status`: `ok = 10684`

## Scope

Analysis v1 remains frozen. This run does not rerun structural validation,
Descriptor v1, Magnetic Descriptor v2, CHGNet, DXMag, enrichment, or figure
generation. It does not implement Analysis v2 figures, CHGNet local moments,
DFT, TB2J, VAMPIRE, ranking, or release cleanup.
