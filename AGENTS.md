# MagGenBench agent instructions

## Repository contract

MagGenBench is the writable project repository.

Reusable Python implementation belongs under `src/mvpipeline`.
User-facing scripts should remain thin wrappers around package code.
`runs/` contains reproducible execution recipes, checksum contracts, and
scientific provenance.

Current code must not depend on `archive/`. Files under `archive/` are retained
for historical provenance only.

## Safety

Do not:

- install or upgrade dependencies without explicit approval;
- modify shared Conda or other runtime environments without explicit approval;
- automatically download models or large datasets;
- run GPU, CUDA, DFT, relaxation, training, or full-production workloads unless
  explicitly requested;
- use destructive Git operations such as `git reset --hard` or `git clean`;
- stage unrelated files with broad commands when an explicit file list is known;
- commit or push without explicit approval;
- add secrets, credentials, user-specific absolute paths, virtual environments,
  caches, generated logs, or runtime outputs to Git.

## Repository organization

- `src/mvpipeline/`: reusable implementation.
- `scripts/`: thin workflow and compatibility wrappers.
- `runs/`: execution recipes, checksums, and provenance.
- `config/`: active scientific and runtime configuration.
- `datasets/`: reference datasets required by supported workflows.
- `samples/`: versioned benchmark CIF inputs retained in the repository.
- `tables/`: accepted canonical or frozen scientific table artifacts.
- `paper/`: manuscript-selected publication artifacts.
- `reproduced/`: regenerated analyses, audits, projections, and figures.
- `outputs/`: generated execution outputs.
- `archive/`: historical provenance only.
- `tests/`: unit and regression tests.

Large or machine-specific frozen artifacts should be externalized with explicit
logical paths and checksum/provenance contracts rather than duplicated in the
source tree.

## Development rules

- Keep reusable behavior under `src/mvpipeline`.
- Keep scripts and run recipes thin and explicit.
- Preserve stable structure and sample identifiers across scientific stages.
- Keep backend environments separate when model dependencies conflict.
- Add dependency-light tests using fixtures, mocks, or fake backends.
- Do not silently rename frozen artifacts whose paths participate in checksum or
  provenance contracts.
- Generated reproduction outputs must not overwrite accepted canonical tables by
  default.
- Current code must not import from historical `archive/` paths.

## Scientific integrity

- CHGNet outputs are ML-predicted total energies. Do not describe them as DFT
  formation energies, energy above hull, or proof of thermodynamic stability.
- DXMag outputs are composition-based predicted magnetic moments in `muB/f.u.`.
  They do not establish FM, AFM, FIM, saturation magnetization, Curie
  temperature, or structure-dependent DFT magnetic moments.
- Composition-based magnetic screens indicate chemical plausibility rather than
  a verified magnetic ground state.
- Descriptor v1 and Analysis v1 are frozen provenance contracts.
- Magnetically informed Descriptor v2 describes composition, magnetic-site
  geometry, and symmetry proxies; it does not establish magnetic order.
- PCA projections are descriptive. Centroid arrows summarize set-level shifts
  and do not represent paired structure trajectories or causal effects.
- Crys-JEPA Refined is a generatively refined comparator set, not a geometry
  relaxation of individual Crys-JEPA Base structures.

## Git and review workflow

Before committing a cleanup or refactor:

1. inspect `git status --short`;
2. stage only intended files;
3. run `git diff --cached --check`;
4. inspect the staged diff and diff stat;
5. run relevant focused tests and broader regression tests when shared behavior
   may be affected;
6. verify that unrelated local or generated files were not staged.

Scientific results, units, status semantics, checksums, and frozen contracts must
not be changed merely for stylistic cleanup.
