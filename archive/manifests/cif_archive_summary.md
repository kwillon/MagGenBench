# Historical CIF archive manifest

This manifest records CIF files that were removed from the current source tree during repository cleanup.

The CIF files were historical/generated artifacts and were not part of the active execution surface.

- Total archived CIFs: 2432
- Exact duplicates already present under `samples/`: 1631
- Archive-only CIFs: 801

## Archive groups

| Group | Total | Duplicate in samples | Archive-only |
| --- | ---: | ---: | ---: |
| `concdvae_finetuned_extras_2000_2015` | 16 | 0 | 16 |
| `mattergen_cifs_archived_2400` | 2400 | 1631 | 769 |
| `mattergen_finetuned_extras_2000_2015` | 16 | 0 | 16 |

The manifest preserves original relative paths, SHA-256 hashes, file sizes, and exact-overlap information.

The removed CIF bytes remain recoverable from repository history and from separately retained external artifact storage.

Current benchmark code must not depend on historical archive CIFs.
