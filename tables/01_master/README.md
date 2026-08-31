# Stage 01 — Master benchmark snapshot

The original master benchmark snapshot was intentionally externalized after verification that all 8000 rows and all 102 source columns are preserved unchanged in Stage 02.

Stage 02 additionally provides the structural-validation fields `status`, `status_source`, and `rejection_reason`.

The original Stage 01 CSV remains recoverable through the external-artifact manifest and Git history.

See:
`archive/manifests/master_01_externalization_manifest.csv`

The accepted downstream workflow therefore continues with `tables/02_validation/` without duplicating the redundant ~79 MB upstream snapshot in the current source tree.
