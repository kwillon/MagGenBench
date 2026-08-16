# Archive

This directory contains historical experiment and provenance code that is not
part of the current MagGenBench execution surface.

- `scripts/phase5a3`: one-row real-backend smoke workflow.
- `scripts/phase5a4`: historical batch-manifest helper after active
  enrichment moved to `scripts/enrichment`.
- `scripts/phase5a6`: superseded production-manifest helper.
- `scripts/phase5b`: superseded fine-tuned annotation preparation.
- `scripts/table_building`: historical table and data-preparation helpers.
- `source_backups`: historical source backups retained because their behavior
  differs from the canonical implementation.

Archive code is not the supported production entry point. Historical names are
intentionally preserved here for provenance. Active reusable code lives under
`src/mvpipeline`, and active script entry points live under semantic
`scripts/` directories. Frozen scientific artifacts are not moved into
`archive/`.
