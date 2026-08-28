# Runs

`runs/` contains lightweight execution recipes, checksums, acceptance facts, and
scientific provenance. Reusable implementation belongs under `src/mvpipeline`.

Supported run areas are organized by workflow:

- `validation/`: structural-validation recipes for generated sets.
- `annotations/`: annotation and manifest preparation.
- `enrichment/`: CHGNet, DXMag, join, and standardized-enrichment recipes.
- `descriptors/v1/`: frozen Descriptor v1 provenance and reproduction support.
- `descriptors/magnetic/`: Magnetically informed Descriptor v2 recipe and
  checksum contract.
- `analysis_v1/`: frozen Analysis v1 reproduction provenance.
- `analysis_v2_magnetic/`: deterministic integration of standardized enrichment
  and Magnetic Descriptor v2 into the accepted Analysis v2 table.

Run recipes may generate outputs under `reproduced/` or `outputs/`. Generated
outputs are not automatically canonical. Accepted or frozen scientific artifacts
are explicitly retained under `tables/` and, where applicable, protected by
checksum contracts.

Historical experiment material may retain older names under `archive/` for
provenance. Current workflows must not depend on archived scripts or paths.
