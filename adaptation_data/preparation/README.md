# Preparation provenance for the magnetic-domain adaptation dataset

## Sources and scope

This review links three newly available source artifacts to the existing
1,426-record prepared dataset. Original files were read without modification.
No database archive, merged table, CIF collection or executable from the archive
was copied into the public package.

[manifest.json](manifest.json) records exact filenames, SHA256 hashes, schemas,
counts and measured matches. The analysis implementation is
[audit_adaptation_preparation.py](../../scripts/analysis/audit_adaptation_preparation.py).

| Source artifact | Records | Columns | Observed role |
| --- | ---: | ---: | --- |
| `7dataset_with_lattice_and_positions - 7dataset_with_lattice_and_positions.csv.csv` | 5,203 | 69 | Structure/property preparation intermediate: 2,069 `novamag` and 3,134 `nemad` records. |
| `nemad_magnetic_materials.csv` | 33,668 | 19 | Larger magnetic-property source table; not a verified training input. |
| `Novomag/Novamag_Database_Files.zip` | 2,085 data JSON entries; 2,056 CIF members | Mixed archive | NOVAMAG consortium data and separately packaged database software. Counts include 41 nested data archives, without extraction. |

The intermediate is not the previously asserted 7,246-record merge. Its 69
columns include source-local IDs, formulas, cell properties, magnetic properties,
CIF references and extracted lattice/coordinate fields. It does not contain an
embedded `cif` column; structures are referenced through `wanted_cif` and
`wanted_cif_after`. The larger NEMAD table contains magnetic/property and
lattice fields, but no atomic-coordinate column.

The archive README identifies the 2019 NOVAMAG project and Nieves et al.,
[Database of novel magnetic materials for high-performance permanent magnet development](https://doi.org/10.1016/j.commatsci.2019.06.007).
Its file MD5 is `3a31735c30f0041ac7ce11942120e405`.
The local source label `novamag` is preserved. This archive should not be
conflated with the distinct similarly named Novomag resource discussed in the
earlier source review.

## Confirmed connection to the prepared dataset

All **1,426** prepared records match exactly one intermediate row on the
literal `(Source, Row_ID)` key. Every matched record has `Source=novamag`;
its formula and both intermediate CIF references agree with the prepared CSV.

For every retained record, the intermediate `name` identifies one parsed
archive JSON record. Both its cell spin polarization and cell volume match
the intermediate. All 1,426 CIFs are present in the archive: **1,424 are
byte-identical**, and **all 1,426 match after newline/edge-whitespace
normalization**. The two newline-only differences concern
`novamag_974_Al1Mn1_#123_0` and `novamag_978_Fe1Ni1_#123_0`.
All retained rows have lattice parameters, lattice angles, atomic positions,
finite spin polarization and positive finite cell volume.

This establishes the intermediate's record ancestry relative to the prepared
selection. It does not establish when a training job loaded the table or
recover the original historical preprocessing implementation. A shared record
lineage does not establish whether this exact file was saved before or after
the prepared splits.

## Target calculation evidence

Across all 1,426 retained records, the saved target agrees with:

```text
candidate_mag_density =
    intermediate["unit cell spin polarization"] /
    intermediate["unit cell volume"]
```

At Decimal precision 40, the maximum absolute discrepancy is
**3.59736671174129614209890e-17**. Five zero-spin/zero-target records are retained.

Upstream loader documentation specifies cell volume in cubic angstroms and
total cell magnetization in Bohr magnetons. The observed ratio is therefore
supported as **mu_B / Angstrom^3**, rather than atomic-content density.
Exact archive member and line references are in the manifest. It is not the
same numerical quantity as a field expressed in tesla, and it must not be
identified directly with `Sat_Magnetization` without a conversion/convention
check.

This is a verified numerical identity supported by source-property units.
The original code creating `candidate_mag_density` remains unavailable;
the review does not claim to have reproduced that historical implementation.
No saved target value was rewritten.

## Selection, missingness and ambiguity

| Source | Intermediate records | Retained | Not in recovered splits |
| --- | ---: | ---: | ---: |
| `novamag` | 2,069 | 1,426 | 643 |
| `nemad` | 3,134 | 0 | 3,134 |
| Total | **5,203** | **1,426** | **3,777** |

The local-only `local_only/selection_ledger.csv` contains one row per
intermediate record, original keys, selected split and material ID when
available, archive-member matches, numeric/completeness flags and NEMAD match
multiplicities. Its SHA256 and 5,203-record count are in the manifest.

All 3,777 nonretained records are marked `historical_exclusion_reason =
not_documented`. This is a reconstructed membership ledger, not a recovered
historical exclusion log. Missing fields are observations, not invented causes.

Of the 643 nonretained NovoMag-labelled records, 629 have no recorded cell spin
polarization; 14 have numeric spin values. Those 14 have CIF files in the
extracted pool and are not complete-CIF-text duplicates of retained records.
Their exclusion must not be attributed to missing CIFs, zero spin, duplicate
removal or structural invalidity without further evidence.

All 3,134 intermediate NEMAD rows lack the particular source spin/volume
fields needed for the observed ratio. They match the larger source table by
`(Formula == Material_Name, DOI)`: **2,928 uniquely**, **206 ambiguously**,
with 2-6 candidate matches. Intermediate `Row_ID` is not universally a row
index into the 33,668-record source file. A separate claimed 5,160-record
NEMAD preparation stage has not been recovered.

Lattice/CIF fetch-status columns suggest structure-retrieval steps, but their
code is missing. A fetched candidate structure must not be represented as
the original experimentally characterized structure solely from these fields.
No structural deduplication or selection algorithm is inferred from filenames.

## Availability and licensing

The README and aggregate manifest are the public candidate. The record-level
ledger is ignored by the local `.gitignore`; original source files remain
outside the repository. All existing model-input payloads retain their earlier
license hold. No source archive, merged table or raw NEMAD data is published.

The archive's Java-loader documentation licenses **the program** under GPL
version 2 or later. That notice does not establish redistribution rights for
`Data_files`. No dataset-wide permission notice was identified. The export
also contains a `confidential` field, including TRUE values in intermediate
NEMAD rows; its semantics require clarification and it is not a substitute for
a license. No retained NEMAD record is claimed.

Twenty-two archive data JSON entries could not be parsed under the tested
encodings; none is needed for the verified 1,426-record mapping. No repairs
were performed. Exact original cleaning decisions, split-generator code,
training-input/checkpoint links and dataset redistribution terms remain open.
