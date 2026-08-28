# Historical legacy-table manifest

During repository cleanup, the remaining historical tables under
`tables/legacy/` were removed from the current source tree.

These files were not part of the canonical numbered table stages and were not
referenced by current reusable code.

The removed snapshots were:

- `master_structures.downsampled.with_status.classes.clean.csv`
- `master_structures.downsampled.with_status.classes.csv`
- `mattergen_structures.downsampled.csv`

Their original paths, SHA-256 hashes, sizes, and physical line counts are
recorded in:

`archive/manifests/legacy_tables_manifest.csv`

The historical bytes remain recoverable from Git history and separately
retained external artifact storage.

Canonical scientific tables live under `tables/01_*` through `tables/10_*`.
