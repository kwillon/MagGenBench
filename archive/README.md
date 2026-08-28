# Archive

This directory contains historical experiment and provenance code that is not
part of the current MagGenBench execution surface.

- `scripts/phase5a3`: one-row real-backend smoke workflow.
- `scripts/phase5a4`: historical batch-manifest helper after active
  enrichment moved to `scripts/enrichment`.
- `scripts/phase5a6`: superseded production-manifest helper.
- `scripts/phase5b`: superseded fine-tuned annotation preparation.
- `scripts/table_building`: historical table and data-preparation helpers.
- `docs`: historical phase/run notes, repository audit and refactor planning
  records, and provenance retained for development history.
- `source_backups`: historical source backups retained because their behavior
  differs from the canonical implementation.

Archive code is not the supported production entry point. Historical names are
intentionally preserved here for provenance. Active reusable code lives under
`src/mvpipeline`, and active script entry points live under semantic
`scripts/` directories. Current contracts and guides live under `docs/`;
historical phase/run notes and refactor records live under `archive/docs/`.
Frozen scientific artifacts are not moved into `archive/`.

## Historical CIF collections

Large historical/generated CIF collections are not retained in the current
source tree.

Their provenance is recorded under:

- `archive/manifests/cif_archive_manifest.csv`
- `archive/manifests/cif_archive_summary.md`

The manifest records original paths, SHA-256 hashes, file sizes, and exact
overlap with current benchmark inputs under `samples/`.

Current code must not depend on historical CIF archives. Large CIF collections
belong in external artifact storage rather than the Git source tree.

## Legacy standalone scripts

Superseded standalone preprocessing, benchmarking, validation, relaxation,
and exploratory helper scripts are retained under:

`archive/scripts/legacy/`

These scripts are preserved for historical provenance only. Some retain old
paths, environment assumptions, or obsolete workflow conventions and are not
part of the supported execution surface.

Current code and tests must not depend on them.

## Legacy configuration files

Superseded configuration files that are no longer consumed by the current
runtime are retained under:

`archive/config/legacy/`

These files document earlier benchmarking, feature, model, and relaxation
workflow conventions. They are provenance-only and are not part of the
supported configuration surface.

Current code, scripts, tests, and run recipes must not depend on them.

## Legacy registry

The former top-level metadata registry is retained under:

`archive/registry/legacy/`

It records historical model, dataset, and generation-run metadata from an
earlier repository organization. The tables contain legacy and
machine-specific paths and are not consumed by the current runtime,
reproduction workflows, or tests.

Current code must not depend on the archived registry.
