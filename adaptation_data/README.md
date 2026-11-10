# Curated magnetic-domain adaptation datasets

## 1. Overview

This directory publishes **1,426 curated NOVAMAG structures** and their prepared
model-specific representations for magnetic-domain adaptation research.
It is separate from baseline novelty references in [datasets/](../datasets/)
and generated benchmark structures in [samples/](../samples/).

The **15 data artifacts (5,381,813 bytes)** in `prepared/` and
`model_specific/` are included in Git. Their bytes, IDs, CIF strings, saved
numeric precision and split membership are unchanged from the audited prepared
files. SHA256 checksums are in [files.csv](provenance/files.csv).

## 2. Source data and provenance

The applicable source is **Nieves et al., Novamag Database, version 1.0,
7 June 2019**, [DOI 10.5281/zenodo.3241267](https://doi.org/10.5281/zenodo.3241267).
The [official deposit metadata](https://zenodo.org/api/records/3241267) declares
**CC BY 4.0** and identifies `Novamag_Database_Files.zip` with MD5
`3a31735c30f0041ac7ce11942120e405`. This checksum and the file size match
the local source archive.

Every retained record has the original label `Source=novamag`. All 1,426
records match the source archive through identifiers, formulas, CIFs and
cell magnetic/volume properties. This source is the 2019 NOVAMAG consortium
archive, not the distinct [Novomag release 17399362](https://zenodo.org/records/17399362)
linked from the Iowa State portal. No NEMAD or MAGNDATA contribution to this
published selection is claimed.

[Redistribution evidence](provenance/redistribution_review.json) records the
official license field, release identity, archive checksum and lineage checks.
[Source provenance](provenance/sources.json) and
[preparation documentation](preparation/README.md) preserve the scientific
history. Full creator credit and modification notices are in
[ATTRIBUTION.md](ATTRIBUTION.md).

## 3. Preparation and filtering

The shared CSVs retain `material_id`, `cif`, `candidate_mag_density`,
`Formula`, `Source`, `Row_ID` and `matched_cif`. Row_ID is source-local;
it is not a universal index into another raw database. All records match a
5,203-row preparation intermediate. No identifiers or complete CIF texts are
duplicated in the shared collection.

For all 1,426 records, the saved conditioning target matches source cell spin
polarization divided by cell volume, with maximum absolute discrepancy
3.59736671174129614209890e-17. Upstream documentation supports mu_B/Angstrom^3.
The original target-calculation and complete cleaning/deduplication code remain
unavailable. This verified numerical relationship is not a claim that the
historical implementation was recovered.

The CrystalFormer variant excludes five training records under the documented
`n_max=21`, `num_sites < n_max` representation constraint. Its original
[exclusion ledger](model_specific/crystalformer/nmax21/excluded_nmax21.csv)
is included. The ledger's generic assertion errors do not identify the exact
runtime assertion.

## 4. Composition and splitting

| Split | Shared structures | Reduced-composition groups | File |
| --- | ---: | ---: | --- |
| Training | 1,139 | 185 | [train.csv](prepared/train.csv) |
| Validation | 142 | 23 | [val.csv](prepared/val.csv) |
| Test | 145 | 24 | [test.csv](prepared/test.csv) |
| Total | **1,426** | **232** | |

Identifiers and reduced-composition groups are disjoint across splits. The
source export carries seed label **1041**, but the original split-generation
code and RNG configuration were not recovered. Existing assignments are
preserved; replaying the seed has not been verified.

CrystalFormer has **1,421 structures: 1,134/142/145**. Its
[training CSV](model_specific/crystalformer/nmax21/train.csv) is model-specific;
validation and test use the shared files above without duplicate copies.

## 5. Model-specific formats and evidence

| Model | Available representation | Evidence boundary |
| --- | --- | --- |
| MatterGen | No model-ready input recovered. | The shared files are not verified actual MatterGen training inputs. |
| Con-CDVAE | Converted CSVs and graph caches were not recovered. | Production evidence documents VAE adaptation and frozen-VAE conditional-prior training; exact input identities remain unverified. |
| CrystalFormer | Compatible training CSV and five-record exclusion ledger. | Use of these exact files for checkpoint epoch3822 is not established. |
| CrystaLLM | Normalized CIF tuples, normalization ledger/summary, token streams, vocabulary and start offsets. | Prepared-input integrity is verified; use by checkpoint step275 remains unverified. |

CrystalFormer's saved training CSV already has decimal reserialization
differences in 918 retained `candidate_mag_density` strings relative to the
shared training CSV, at most **9.7e-17**. Other identity/source/CIF fields agree.
Those pre-existing differences are preserved rather than repaired.

CrystaLLM normalization retains **1,139/142/145** records with zero failures.
A 371-token vocabulary encodes **830,129 training tokens** and **86,015
validation tokens** as little-endian uint16. Decoded document multisets match
all 1,139/142 normalized CIF texts after comment/whitespace normalization;
training order differs. No production `test.bin` is available.

Pickle-format artifacts contain literal data and are preserved in their
original representation. Verification uses a primitive-opcode allowlist,
without `pickle.load`, `torch.load` or callable/object construction.
Do not use unrestricted deserialization on externally obtained files.

## 6. Repository contents

```text
prepared/
  train.csv
  val.csv
  test.csv
model_specific/
  crystalformer/nmax21/
    train.csv
    excluded_nmax21.csv
  crystallm/
    normalization_manifest.csv
    normalization_summary.json
    normalized/{train,val,test}_normalized_raw.pkl.gz
    tokens/{train.bin,val.bin,meta.pkl,starts.pkl,starts_val.pkl}
provenance/
  files.csv
  sources.json
  verification.json
  redistribution_review.json
preparation/
  README.md
  manifest.json
  local_only/selection_ledger.csv  # private; not included in Git
LICENSE.md
ATTRIBUTION.md
```

[files.csv](provenance/files.csv) lists all 15 published artifacts and hashes.
[verification.json](provenance/verification.json) records measured integrity,
composition and representation checks. [sources.json](provenance/sources.json)
defines the model views, including the shared validation/test references.

Verification code is provided in
[verify_adaptation_data.py](../scripts/analysis/verify_adaptation_data.py).
A public checkout can verify all published data without the private mixed-source
ledger or original source exports.

## 7. Availability and use conditions

The prepared CSVs and listed model-specific artifacts are published under
**[Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/)**,
based on the matched source deposit's explicit license. See
[LICENSE.md](LICENSE.md) and [ATTRIBUTION.md](ATTRIBUTION.md) for scope,
creator credit, source links and changes. Reuse requires appropriate attribution,
a license link and identification of modifications; it must not imply upstream
endorsement. No additional restrictions are imposed.

The main repository's MIT software license is separate and is not the basis
for redistributing these third-party data. Program sources bundled in the
upstream archive are not redistributed here; their software licenses are not
relabelled.

Not published: the full source archive, mixed NovoMag/NEMAD intermediate table,
raw NEMAD records, the 5,203-row mixed-source selection ledger, checkpoints,
training logs, generated benchmark structures, smoke artifacts and duplicate
bundles. Rights for the NEMAD-containing materials are not established by the
NOVAMAG deposit license. `local_only/` remains reserved for private materials.

## 8. Limitations and citations

The original cleaning/splitting implementations, some historical exclusion
reasons and exact training-file/checkpoint links remain unavailable.
Prepared-input verification does not establish actual use by a particular
training job. The intermediate table is not the earlier claimed 7,246-row merge.

Cite the source dataset as **Nieves et al. (2019), Novamag Database, version 1.0,
Zenodo, DOI 10.5281/zenodo.3241267**, and its associated paper:
[Database of novel magnetic materials for high-performance permanent magnet development](https://doi.org/10.1016/j.commatsci.2019.06.007).
Also identify MagGenBench's curated splits and model-format modifications.
The complete deposit creator list is retained in the attribution record.
