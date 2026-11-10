# Magnetic-domain adaptation dataset

## 1. Overview

This collection documents the prepared magnetic-domain dataset recovered for
MagGenBench. It comprises **1,426 structures** attributed to NovoMag in the
source records and associated model-specific representations. It is separate
from the baseline novelty-reference tables in [datasets/](../datasets/) and the
generated benchmark structures in [samples/](../samples/).

**Availability:** documentation and file-level provenance are prepared for
version control; structure-containing data and derivatives remain in the
Git-ignored `local_only/` directory pending confirmation of redistribution
rights. A public clone does not contain these payloads.

## 2. Source data and provenance

Every recovered record has `Source=novamag`, referred to as NovoMag in the
project audit. The embedded CIF texts of all 1,426 records match files in the
original extracted pool. Their source-local `Row_ID`, `material_id` and
`matched_cif` fields preserve record identity and local provenance.

Newly recovered [preparation evidence](preparation/README.md) links all 1,426
records to a 5,203-row intermediate table and the supplied NOVAMAG consortium
archive. This does not recover its complete download history or historical
selection implementation. Neither NEMAD nor MAGNDATA is established as a
contributor to the final selection.

[Source provenance](provenance/sources.json) records the available evidence and
its limits. The shared CSVs and existing model-specific ledgers provide
record-level provenance without an additional duplicate ID table.

## 3. Data preparation and filtering

The shared prepared CSVs contain `material_id`, `cif`,
`candidate_mag_density`, `Formula`, `Source`, `Row_ID` and `matched_cif`.
Original bytes, including numerical precision, are preserved. No duplicate
identifiers or repeated complete CIF texts occur in the shared collection.

The original cleaning, structural deduplication and target-calculation
implementations are unavailable. For all 1,426 records, `candidate_mag_density`
matches source cell spin polarization divided by cell volume, to a maximum
absolute discrepancy of 3.59736671174129614209890e-17. Upstream property
documentation supports the ratio units mu_B / Angstrom^3. This observed identity
does not recover the historical calculation code; saved targets are unchanged.

The CrystalFormer-compatible variant excludes five training structures under
the documented `n_max=21`, `num_sites < n_max` representation constraint.
Its existing exclusion ledger identifies all five records. Generic assertion
errors in that ledger do not establish the exact failing runtime assertion.

## 4. Dataset composition and splitting

| Split | Structures | Reduced-composition groups |
| --- | ---: | ---: |
| Training | 1,139 | 185 |
| Validation | 142 | 23 |
| Test | 145 | 24 |
| Total | **1,426** | **232** |

The grouped split has no overlap in identifiers or reduced-composition groups
between training, validation and test. These observations support grouping by
reduced formula. The export carries the seed label **1041**, but the original
split-generator implementation and RNG configuration were not recovered;
replaying that seed has not been verified. Existing assignments are preserved.

The CrystalFormer variant contains **1,421 structures**, with **1,134/142/145**
training/validation/test records. Validation and test are byte-identical to the
shared files and are referenced there instead of duplicated.

## 5. Model-specific preprocessing

| Model | Adaptation representation and mechanism | Evidence boundary |
| --- | --- | --- |
| MatterGen | Model-ready adaptation inputs were not recovered. | The shared splits are not established as actual MatterGen training inputs. |
| Con-CDVAE | Production records document VAE adaptation followed by conditional-prior training with a frozen VAE and scalar `candidate_mag_density` conditioning. | The converted CSVs and graph caches are unavailable; exact training-record identities cannot be checked. |
| CrystalFormer | A representation-compatible training CSV retains 1,134 records after five documented exclusions. | Use of these files for the selected epoch3822 checkpoint remains unverified. |
| CrystaLLM | CIF records were normalized to text and represented as autoregressive token sequences. | Prepared inputs are verified; use by the selected step275 checkpoint remains unverified. |

The CrystalFormer training CSV already contains small decimal reserialization
differences relative to the shared training CSV: 918 retained records differ in
`candidate_mag_density` by at most **9.7e-17**. Other identity, source and CIF
fields match. These pre-existing differences are preserved rather than repaired.

CrystaLLM normalization retains **1,139/142/145** records with zero failures in
the existing normalization manifest. A 371-token vocabulary encodes **830,129
training tokens** and **86,015 validation tokens** as little-endian uint16.
The token streams contain all **1,139/142** normalized CIF documents, verified
after comment and whitespace normalization. Training order differs from the
normalized tuple order. No production `test.bin` is available.

Pickle-based representations remain in their original format. Their inspection
used only primitive literal opcodes; no object deserialization or callable
execution was required. Token contents and original numeric strings were not
modified.

## 6. Repository contents

| Version-control candidate | Purpose |
| --- | --- |
| [sources.json](provenance/sources.json) | Source attribution, audit identifiers, model views and unresolved rights. |
| [files.csv](provenance/files.csv) | Selected paths, source-relative locations, sizes, record counts and SHA256 hashes. |
| [verification.json](provenance/verification.json) | Measured composition, representation and integrity checks. |
| [preparation/](preparation/README.md) | New intermediate/archive lineage evidence and an aggregate manifest; the record-level selection ledger remains local. |
| `.gitignore` | Keeps all structure-containing payloads outside Git. |

The local data layout is:

```text
local_only/
  shared/grouped_seed1041/{train,val,test}.csv
  models/
    crystalformer/nmax21/
      train.csv
      excluded_nmax21.csv
    crystallm/
      normalization_manifest.csv
      normalization_summary.json
      normalized/{train,val,test}_normalized_raw.pkl.gz
      tokens/{train.bin,val.bin,meta.pkl,starts.pkl,starts_val.pkl}
```

There are **15 selected payload files (5,381,813 bytes)**. The package excludes
checkpoints, weights, training logs, generated benchmark structures, raw CIF
duplicates, smoke artifacts, duplicate archive bundles and duplicate
CrystalFormer validation/test files. Raw CrystaLLM tuple copies are omitted
because their original ID/CIF pairs are already present in the shared CSVs.

## 7. Data availability

The current public candidate consists of documentation and file-level
provenance only. All structures, normalized CIF tuples, tokens and record-level
ledgers remain local and ignored by Git. No payload is presently cleared for
redistribution. The repository's MIT software license does not grant rights
over these third-party records or their derivatives.

The exact upstream release, applicable data license, attribution requirements
and permission for redistribution must be established before publication.
A future `prepared/` directory is appropriate only for artifacts individually
cleared under those terms. It has not been created or populated. Once rights
are confirmed, approved files can be organized as `prepared/shared/` and
`prepared/models/`, with explicit license and checksum references; unresolved
artifacts must remain local.

## 8. Limitations and citations

The missing historical cleaning/deduplication and target-calculation code,
split-generator implementation and model-input/checkpoint links limit full
training reproducibility. The 5,203-row intermediate is not the earlier claimed
7,246-record merge. Any NEMAD or MAGNDATA contribution to the final selection
remains unestablished. Prepared data integrity does not by itself establish
actual training use. Additional source and selection details are documented in
[preparation provenance](preparation/README.md).

The recorded upstream review identified distinct, similarly named resources:
[Novamag Database, Zenodo 3241267](https://zenodo.org/records/3241267) and
[Novomag magnetic materials database, Zenodo 17399362](https://zenodo.org/records/17399362).
These are source-identification leads, not verified release attributions or
applicable licenses for this export. The latter resource states scientific use
with acknowledgement; that statement is not transferable without identifying
the relevant source release. Source-specific citations and notices must follow
the release ultimately established for the recovered records.
