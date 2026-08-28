# Legacy Tables

This directory contains historical table snapshots that are not part of the
current canonical scientific pipeline.

Current canonical tables live under the numbered `tables/01_*` through
`tables/10_*` stage directories.

During repository cleanup, three byte-for-byte duplicate legacy tables were
removed after SHA-256 verification:

- `master_structures.downsampled.csv`
  -> canonical: `tables/01_master/master_structures_downsampled.csv`
- `master_structures.downsampled.with_status.csv`
  -> canonical: `tables/02_validation/master_structures_with_validation_status.csv`
- `master_structures.downsampled.with_status.classes.clean_v2.fixed_paths.csv`
  -> canonical: `tables/03_features/master_structures_with_classes.csv`

The remaining files are historical snapshots with content that differs from
the current canonical tables. They are retained temporarily pending a separate
provenance/content audit.

Current code must not depend on files under `tables/legacy/`.
