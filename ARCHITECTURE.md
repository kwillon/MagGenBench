# MagGenBench Architecture

MagGenBench is organized as a reproducible scientific repository with a small public command surface, reusable package code under `src/mvpipeline`, and explicit separation between current code, generated artifacts, run recipes, and archived provenance.

## Design Goals

- A new contributor should understand the repository structure from `README.md`.
- Current reusable code lives under `src/mvpipeline`.
- Scripts and run recipes are thin orchestration layers.
- Generated tables, figures, run artifacts, scientific data, provenance, current scripts, and legacy scripts have separate roles.
- Current-code areas should not contain unexplained backup, copy, temporary, obsolete, or zero-purpose files.
- Machine-specific absolute paths should not exist in reusable package code.
- The public execution surface should remain small and consistent.

## Data Flow

The current frozen Analysis v1 flow is:

```text
model CIF outputs
  -> validation and annotation manifests
  -> Descriptor v1 results
  -> CHGNet energy enrichment
  -> DXMag magnetism enrichment
  -> unified_analysis_v1.csv
  -> Analysis v1 tables and figures
```

Expensive model generation, descriptor extraction, CHGNet execution, and DXMag execution are not rerun by the Analysis v1 reproducer. The reproducer consumes frozen required inputs, rebuilds the unified analysis table, verifies its checksum, and then regenerates figures/statistics.

The post-v1 standardized enrichment layer keeps the frozen Analysis v1 flow
separate while publishing a symmetric per-structure enrichment interface:

```text
source/annotation artifacts
  -> standardized CHGNet + DXMag per cohort
  -> standardized_enrichment.csv
  -> future Descriptor v2 / Analysis v2
```

The standardized master does not rewrite Analysis v1 or Descriptor v1. It is
the current recommended table for inspecting CHGNet and DXMag outputs across
all eight current cohorts.

## Package Responsibilities

`src/mvpipeline` is the current reusable package root.

| Package | Responsibility |
| --- | --- |
| `analysis` | Canonical production cohort registry, unified-analysis helpers, plotting group definitions, shared figure conventions, and Analysis v1 figure generation. |
| `annotations` | Annotation preparation and production-manifest helpers for active workflows. |
| `descriptors` | Descriptor v1 implementation and descriptor table handling. |
| `enrichment` | Standardized post-v1 enrichment registry, manifest preparation, master-table construction, and invariant checks. |
| `energy` | CHGNet backend adapters and energy-stage result handling. |
| `magnetism` | DXMag backend adapters and magnetism-stage result handling. |
| `io` | Lightweight manifest, CIF, CSV, and table IO helpers. |
| `pipeline` | Shared orchestration primitives for checkpointed batch stages and enrichment run checks. |
| `reproduction` | One-command Analysis v1 reproduction from frozen inputs. |
| `validation` | CIF validation and validation report logic. |
| `dedup`, `novelty`, `report`, `utils` | Supporting duplicate detection, novelty checks, report generation, and shared utilities. |

Generic machinery and production registry data are separated. For example, reusable unified-analysis execution remains distinct from the canonical production cohort registry, and plotting code consumes canonical cohort/group metadata rather than defining scientific cohort identities independently.

## Orchestration Layers

MagGenBench has four orchestration layers:

| Layer | Role |
| --- | --- |
| `maggenbench` | Current reproducibility CLI for Analysis v1 reproduction and figure generation. |
| `mvp` | Existing validation CLI retained for compatibility. |
| `scripts/` | Thin semantic wrappers around reusable package code. |
| `runs/` | Documented active run recipes and provenance for production workflows. |

The supported public commands are:

```bash
maggenbench reproduce analysis-v1
maggenbench figures analysis-v1
mvp
```

Legacy phase names and archived scripts are not part of the public execution surface.

## Analysis V1 Reproduction

`maggenbench reproduce analysis-v1` is the documented one-command paper-reproduction target for Analysis v1. It regenerates analysis tables/statistics/figures from frozen required inputs without rerunning expensive model generation or enrichment.

The reproducer:

1. Resolves required inputs from the repository or an artifact root.
2. Accepts the historical baseline joined table through `--baseline-joined`.
3. Builds `unified_analysis_v1.csv`.
4. Verifies the frozen SHA-256.
5. Generates the 15 Analysis v1 figure/statistics outputs.

Frozen invariants:

- `10684` production rows.
- `124` columns.
- Unique `sample_uid`.
- `sample_uid == structure_id`.
- Canonical cohort identities, order, and counts: `baseline_master = 4702`, `mattergen_finetuned = 1376`, `concdvae_finetuned = 1299`, `crysjepa_base = 1764`, `crysjepa_refined = 1543`.
- Descriptor v1 status counts: `ok = 10681`, `partial = 3`.
- Energy status counts: `ok = 10680`, `error = 4`.
- Magnetism status counts: `ok = 10684`.
- Descriptor v1 schema and semantics.
- CHGNet and DXMag semantics.
- SHA-256: `a559a092755a91ea2c9035a08a61a41b8279a81b8dbe2ba52cb888cb17b4cb6c`.

## Figure Generation

`maggenbench figures analysis-v1` regenerates the current Analysis v1 visual/statistical outputs from an existing unified CSV. Figure behavior is centralized in `mvpipeline.analysis.figures_v1`; cohort grouping and validation are shared with the canonical analysis metadata.

The figure output contract is the 15-file set documented in `README.md`. Existing visual choices, filenames, cohort order, labels, and calculations are treated as regression-sensitive for Analysis v1.

## Artifact And Provenance Boundaries

Current-code areas:

- `src/mvpipeline`
- active semantic wrappers under `scripts/`
- active run recipes under `runs/`
- tests under `tests/`

Generated or externally supplied areas:

- `tables/`
- `reports/`
- `outputs/`
- `reproduced/`
- reproducible analysis outputs and figures under `reproduced/`
- full production CIF collections
- large model/checkpoint artifacts
- local logs and caches

Provenance-only areas:

- `archive/`
- run-specific manifests, checksums, and README files

Publication artifacts selected for a manuscript belong under `paper/figures/`
or `paper/tables/` when they exist; exploratory outputs do not move there
automatically.

Current code should not import from `archive/`. Historical files remain only to explain how earlier artifacts were produced.

## Environment Boundaries

The lightweight analysis and documentation environment should be able to install the package, run unit tests, rebuild Analysis v1 from frozen inputs, and regenerate figures.

Heavy model environments should remain separate when dependencies conflict:

- CHGNet energy enrichment can use a backend-specific environment.
- DXMag magnetism enrichment can use a backend-specific environment and externally supplied model artifact.
- MatterGen, Con-CDVAE, CrystalFormer, CrystaLLM, and Crys-JEPA generation or refinement workflows can use their own environments or future backend-specific containers where appropriate.

The current Docker/Compose layer implements only the lightweight Analysis v1 surface. It installs MagGenBench as a normal package, exposes the `maggenbench` and `mvp` console entry points, and uses a headless Matplotlib backend. It does not include CHGNet, DXMag, generative-model runtimes, checkpoints, training environments, or production data.

The Compose mount contract follows the same boundary:

- one lightweight analysis/figure environment;
- `/workspace` for the repository checkout and frozen contract files;
- `/artifacts` for externally supplied frozen artifacts, including the explicit `--baseline-joined` CSV;
- `/output` for host-visible reproduced outputs.

`MAGGENBENCH_ARTIFACT_ROOT` is required for the `/artifacts` mount so Compose fails clearly instead of creating or mounting a placeholder artifact directory. `MAGGENBENCH_OUTPUT_ROOT` may use the safe generated-output default.

## Backward Compatibility

The repository still retains compatibility entry points and historical references where they are useful for provenance. Compatibility code should stay thin and should call reusable package modules. New scientific behavior should not be implemented in legacy scripts.

## Extension Guidance

When adding a model, descriptor, or analysis stage:

1. Decide whether it is part of the current public surface, an active run recipe, or archived provenance.
2. Put reusable logic under `src/mvpipeline`.
3. Keep wrapper scripts thin.
4. Use canonical registries for cohort and plotting metadata.
5. Document required external artifacts and environment constraints.
6. Add dependency-light tests with fixtures or fake backends.
7. Preserve Analysis v1 invariants unless introducing a new explicitly versioned analysis.
