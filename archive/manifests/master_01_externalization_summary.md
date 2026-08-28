# Externalized benchmark master snapshot

During repository cleanup, the tracked upstream benchmark snapshot
`tables/01_master/master_structures_downsampled.csv` was removed from the current source tree.

The file contained 8000 data rows and 102 columns.

After whitespace normalization of the CSV header, all 102 columns were confirmed to be present in
`tables/02_validation/master_structures_with_validation_status.csv`.
All values in those 102 columns were identical for every row.

The validation table adds exactly three fields:

- `status`
- `status_source`
- `rejection_reason`

The original snapshot therefore contains no per-row scientific information absent from the retained validation table.

The original bytes are retained in external artifact storage at the logical path:

`benchmark_assembly/01_master/master_structures_downsampled.csv`

SHA-256:

`a8dc20506458c5ce627b2a9975dc46dcf202627a6e086be2bb0ecc7caa2e48e8`

The external copy was verified byte-for-byte with `cmp` before removal from the current source tree.

The original tracked version also remains recoverable from Git history.
