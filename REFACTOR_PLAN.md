# MagGenBench Staged Refactor Plan

## Refactor Principles

This plan favors small, reviewable phases. Each phase must preserve scientific outputs unless it explicitly declares a documentation-only or source-only cleanup. Production CSVs, generated figures, run checksums, model artifacts, CIF datasets, and donor paths are not to be rewritten as part of cleanup.

## Final Repository Goal

MagGenBench should become a self-explanatory, reproducible scientific repository with a minimal number of entry points. A new contributor should be able to understand the repository structure, scientific scope, data/artifact boundaries, and ordinary workflows from `README.md` without inspecting implementation files.

The final architecture should make these roles explicit:

- Current reusable code lives under `src/mvpipeline`.
- Public commands are small, documented, and consistent.
- Current scripts are thin wrappers or reproduction helpers, not independent scientific implementations.
- Legacy scripts are separated from current workflows and cannot be imported by current code.
- Generated tables, generated figures, run artifacts, scientific data, and provenance records have documented locations and retention rules.
- Backup, copy, temporary, obsolete, or zero-purpose files are absent from current-code areas unless they are required Python package markers or explicitly documented provenance.
- Machine-specific absolute paths are absent from current reusable code and current scripts.
- Frozen analysis outputs can eventually be reproduced from frozen required inputs with one command after installation, for example `maggenbench reproduce analysis-v1`.

## Target Public Execution Surface

The current console script is `mvp`, and the existing Typer CLI exposes `validate`. The smallest compatible design is to keep `mvp validate` working during transition, add a clearer `maggenbench` console script as the preferred interface, and route both to the same implementation until old command names can be deprecated.

Recommended target commands:

- `maggenbench validate`: run lightweight CIF validation.
- `maggenbench descriptors`: run Descriptor v1 extraction from an explicit manifest.
- `maggenbench energy`: run configured energy stage, defaulting to fake/lightweight backends unless real backends are explicitly selected.
- `maggenbench magnetism`: run configured magnetism stage, defaulting to fake/lightweight backends unless real backends are explicitly selected.
- `maggenbench build-analysis`: build frozen unified analysis tables from frozen inputs.
- `maggenbench figures`: regenerate approved analysis/statistics/figure outputs from an analysis table.
- `maggenbench reproduce analysis-v1`: one documented target for the frozen paper-analysis bundle.

Do not implement these names blindly. First map each command to an existing tested function or script, then add only the smallest wrapper needed. Commands that can trigger model downloads, GPU execution, CHGNet, DXMag, relaxation, DFT, or large CIF processing must require explicit backend/config selection and environment documentation.

## Data And Artifact Policy

Artifacts that cannot reasonably live in Git should be supplied through documented external locations, release assets, checksummed downloads, or mounted directories. This includes:

- raw or full generated CIF collections beyond approved tracked fixtures/releases;
- model checkpoints and binary artifacts such as `models/magnetism/magmom_model_dxmag.pkl`;
- dependency caches, model download caches, Conda environments, virtual environments, and package caches;
- large generated runtime CSVs not selected as frozen release/provenance artifacts;
- full relaxation/DFT outputs, logs, checkpoints, and temporary files;
- donor repository data, donor CIF collections, donor virtual environments, donor logs, and donor generated CSVs.

Required external artifacts should have:

- a stable logical name;
- expected mount path or environment variable;
- checksum or provenance record where practical;
- version/source description;
- explicit statement of whether the artifact is required for lightweight analysis reproduction, real backend execution, or historical provenance only.

## Required Scientific Invariants

- Descriptor v1 schema and semantics unchanged.
- Unified analysis v1 semantics unchanged.
- `sample_uid` identity rules unchanged.
- Core four-model baseline definition unchanged.
- Fine-tuned cohort identities unchanged.
- Crys-JEPA Base/Refined identities unchanged.
- Crys-JEPA remains in common analysis infrastructure.
- CHGNet outputs are not reinterpreted as DFT stability.
- DXMag outputs remain raw model predictions.
- No clipping or silent transformation of scientific outputs.
- No cohort row loss.
- Existing production checksums are not rewritten to hide changes.
- Generated runtime artifacts are not silently promoted into source control.

## Phase 0: Freeze Baseline Evidence

Affected files:

- No source changes required.
- Optional new docs/checklist only if explicitly approved later.

Intended behavior:

- Establish current tracked state, expected row counts, cohort counts, and test baseline before refactor work.

Scientific invariants:

- All required invariants listed above.

Tests that must pass:

- `pytest tests/test_unified_analysis.py`
- `pytest tests/test_descriptor_*`
- `pytest tests/test_energy_* tests/test_magnetism_*`
- `pytest tests/test_enrichment_*`
- `pytest tests/test_stage_*`

Regression checks:

- `git diff --stat` before and after each phase.
- Confirm no tracked CSV/figure/checksum changes unless phase explicitly allows them.
- Confirm `scripts/analysis/build_unified_analysis_v1.py` expected counts remain `10684` total rows and current cohort/status counts.

Rollback boundary:

- Documentation/checklist only; revert that file if needed.

## Phase 0B: Repository Map And Boundary Design

Affected files:

- `README.md` design outline only in this phase if approved.
- `REFACTOR_PLAN.md` follow-up notes if the plan is updated.
- No source, data, table, figure, or checksum changes.

Intended behavior:

- Define the intended top-level directory map before moving files.
- Decide which locations are current source, current scripts, legacy scripts, frozen provenance, generated runtime outputs, external scientific data, and tests.
- Establish that every top-level directory must have a documented purpose in the final README.

Proposed final top-level role model:

- `src/`: reusable package code only.
- `tests/`: lightweight automated tests and fixtures.
- `config/`: portable YAML configuration, no machine-specific absolute paths.
- `scripts/`: thin current wrappers only, or retire in favor of CLI commands.
- `scripts/legacy/` or `archive/scripts/`: historical scripts not imported by current workflows.
- `data/`, `samples/`, `archive/cifs/`, or equivalent: clearly labeled scientific input data/provenance, not active source.
- `tables/`: frozen tracked tables only if intentionally part of provenance/release; runtime outputs go elsewhere.
- `figures/`: frozen tracked figures only if intentionally part of provenance/release; regenerated outputs go to a documented output directory.
- `runs/`: reproducibility manifests, checksums, and run recipes, not ad hoc output dumps.
- `docs/`: detailed contracts and provenance notes referenced from README.

Scientific invariants:

- No files are moved in this phase.
- No generated artifacts are promoted or removed.

Tests that must pass:

- No tests required unless docs tooling is added.

Regression checks:

- Ensure the map explicitly preserves source/provenance/runtime distinctions.
- Ensure current reusable code remains under `src/mvpipeline`.

Rollback boundary:

- Documentation/design-only.

## Phase 1: Centralize Unified Analysis Cohort Registry

Affected files/modules:

- Add `src/mvpipeline/analysis/cohorts.py` or equivalent.
- Update `scripts/analysis/build_unified_analysis_v1.py`.
- Add focused tests, likely `tests/test_unified_analysis.py` or a new cohort-registry test.

Intended behavior:

- Define canonical production `AnalysisCohortSpec` entries in one place.
- Preserve current script behavior, paths, expected row counts, family/state labels, and Crys-JEPA comparator handling.
- Keep baseline four-model semantics distinct from comparator/fine-tuned cohorts.

Scientific invariants:

- `baseline_master`, `mattergen_finetuned`, `concdvae_finetuned`, `crysjepa_base`, and `crysjepa_refined` identities unchanged.
- Crys-JEPA remains in common analysis infrastructure but not in the four core baselines.
- No row loss and no `sample_uid` changes.

Tests that must pass:

- `pytest tests/test_unified_analysis.py`
- New tests asserting registry entries, analysis families/states, and expected cohort count constants.

Regression checks:

- Build command should produce identical `analysis_cohort`, `analysis_family`, `analysis_state`, `descriptor_v1_status`, `energy_status`, and `magnetism_status` counters when run in an approved environment.
- Do not rewrite tracked production output or checksum files in this phase.

Rollback boundary:

- Revert registry module and script import change. Existing generic `run_unified_analysis` remains untouched.

## Phase 2: Shared Unified Plotting Utilities

Affected files/modules:

- Add `src/mvpipeline/analysis/plotting.py` or `scripts/illustrations/common.py`.
- Update one plotting script first, then migrate:
  - `scripts/illustrations/plot_unified_analysis_v1.py`
  - `scripts/illustrations/plot_structural_distributions_v1.py`
  - `scripts/illustrations/plot_compound_class_heatmap_v1.py`
  - `scripts/illustrations/plot_3d_4f_fraction_v1.py`
  - `scripts/illustrations/plot_magnetic_screening_fraction_v1.py`
  - `scripts/illustrations/plot_dxmag_predicted_moment_v1.py`

Intended behavior:

- Centralize group ordering, labels, row-count guards, required-column checks, input/output paths, Matplotlib style, numeric coercion, boolean parsing, and summary writer helpers.
- Keep each script responsible only for the metric-specific calculation and figure shape.

Scientific invariants:

- Unified analysis v1 semantics unchanged.
- Group order unchanged.
- Crys-JEPA Base/Refined still plotted in the same common analysis groups.
- DXMag plotted values remain raw predictions, without clipping.

Tests that must pass:

- Existing tests.
- Add light utility tests for group subsetting and required-column failures.

Regression checks:

- In an approved figure-regeneration environment, compare summary CSV row counts and group labels before/after.
- Manual review of regenerated figures if figure outputs are explicitly regenerated in a separate phase.

Rollback boundary:

- Migrate one script per commit/phaselet. Revert individual script plus utility if a mismatch appears.

## Phase 3: Consolidate Resumable Batch Stage Orchestration

Affected files/modules:

- Add `src/mvpipeline/pipeline/batch_stage.py`.
- Move reusable pieces from `scripts/phase5a4/batch_common.py` as appropriate.
- Update:
  - `scripts/phase5a4/run_batch_chgnet.py`
  - `scripts/phase5a4/run_batch_dxmag.py`
- Add or extend `tests/test_stage_runners.py` and `tests/test_stage_tables_resume.py`.

Intended behavior:

- Keep backend construction explicit in thin scripts.
- Share checkpoint chunking, resume success detection, pending selection, final order checks, and status summaries.

Scientific invariants:

- CHGNet output fields and semantics unchanged.
- DXMag output fields and semantics unchanged.
- Existing successful rows remain immutable during resume.
- Failed/missing rows are recalculated exactly as before.

Tests that must pass:

- `pytest tests/test_stage_runners.py tests/test_stage_tables_resume.py`
- `pytest tests/test_energy_* tests/test_magnetism_*`

Regression checks:

- Fake-backend tests for full run, full resume, partial checkpoint resume, failed-row replacement, unknown-ID rejection, duplicate-ID rejection.
- Do not run real CHGNet/DXMag locally.

Rollback boundary:

- Scripts can return to current local loops because shared helper should be additive.

## Phase 4: Parameterize Cohort Annotation Preparation

Affected files/modules:

- Add `src/mvpipeline/pipeline/cohort_manifest.py` or `scripts/prepare_cohort_annotations.py`.
- Update or replace:
  - `scripts/phase5b/prepare_mattergen_finetuned_annotations.py`
  - `scripts/phase5b/prepare_concdvae_finetuned_annotations.py`
  - `scripts/crysjepa/prepare_crysjepa_base_annotations.py`
  - `scripts/crysjepa/prepare_crysjepa_refined_annotations.py`
- Move `classify_formula` out of `scripts/legacy/add_compound_class.py` into `src/mvpipeline` or provide a compatibility wrapper.

Intended behavior:

- One reusable adapter converts MVP `all_structures.csv` rows into canonical enrichment manifests.
- Cohort-specific values become explicit config/spec data: source path, output paths, expected count, sample UID transform, `model_name`, `model_short`, `run_uid`, and pass label.

Scientific invariants:

- Stable `sample_uid` rules unchanged for all four cohorts.
- Fine-tuned cohort identities unchanged.
- Crys-JEPA Base/Refined identities unchanged.
- No cohort row loss.
- Compound-class classification unchanged.

Tests that must pass:

- Existing enrichment annotation tests.
- New fixture tests for each cohort spec's ID mapping and metadata fields.

Regression checks:

- Dry/fake manifest adaptation over small synthetic rows.
- In an approved environment, compare output headers, row counts, first/last IDs, and class/status counters against current generated tables.

Rollback boundary:

- Keep old scripts as wrappers until equivalence is proven. Remove wrappers only in a later cleanup phase.

## Phase 5: Configuration And Path Boundary Cleanup

Affected files/modules:

- `config/paths.yaml`
- `config/models.yaml` only if adding non-baseline analysis registry references elsewhere is insufficient.
- Possibly new `config/analysis_cohorts.yaml`.
- Docs that describe path conventions.

Intended behavior:

- Separate baseline model configuration from analysis cohort configuration.
- Reconcile numbered table directories with stale root-level table paths.
- Avoid absolute paths and machine-specific paths in active workflows.

Scientific invariants:

- Core four-model baseline definition unchanged.
- Crys-JEPA remains comparator, not fifth core baseline.
- Runtime path cleanup must not change generated file contents.

Tests that must pass:

- Config-loading tests.
- `pytest tests/test_descriptor_config.py tests/test_dxmag_runtime_metadata.py`
- Any new analysis-cohort config tests.

Regression checks:

- Search for `/mnt/tank`, `C:\Users`, `C:/Users`, `/home/`, `D:\`, and `../crystalformer/src` in active source/scripts.
- Ensure legacy files are either quarantined/documented or excluded from active checks.

Rollback boundary:

- Revert config/docs changes; source modules should still accept explicit paths.

## Phase 5B: Public CLI Consolidation

Affected files/modules:

- `pyproject.toml`
- `src/cli/app.py` or a new `src/mvpipeline/cli.py`
- Thin script wrappers only where backward compatibility is needed.
- Tests for CLI command parsing and dry/lightweight execution.

Intended behavior:

- Preserve existing `mvp validate` behavior.
- Add a preferred `maggenbench` console script with a small command surface.
- Route CLI commands to reusable functions under `src/mvpipeline`, not to duplicated script logic.
- Keep dangerous or expensive backend execution opt-in and clearly configured.

Smallest compatible design:

- Keep `mvp = "cli.app:app"` temporarily.
- Add `maggenbench = "cli.app:app"` or migrate to `mvpipeline.cli:app` with compatibility shims.
- Add commands incrementally only after their underlying reusable functions exist:
  - `validate`
  - `descriptors`
  - `energy`
  - `magnetism`
  - `build-analysis`
  - `figures`
  - `reproduce analysis-v1`

Scientific invariants:

- CLI refactor must not alter validation, Descriptor v1, enrichment, energy, magnetism, or unified-analysis semantics.
- Commands must preserve existing default lightweight behavior and must not download models by default.

Tests that must pass:

- Existing test suite.
- New CLI smoke tests using Typer's test runner or subprocess import checks.
- Dry-run/fake-backend checks for `descriptors`, `energy`, `magnetism`, and `build-analysis` once commands exist.

Regression checks:

- `mvp validate --help` still works during compatibility period.
- `maggenbench --help` shows only documented commands.
- `maggenbench reproduce analysis-v1 --help` documents required frozen inputs and external mounts.

Rollback boundary:

- CLI command additions should be one command per reviewable change. Revert the new command without touching underlying scientific modules.

## Phase 5C: One-Command Frozen Analysis Reproduction

Affected files/modules:

- `src/mvpipeline/analysis/cohorts.py`
- `src/mvpipeline/analysis/unified.py` only for additive orchestration helpers, not semantics.
- `src/mvpipeline/analysis/plotting.py`
- CLI command for `maggenbench reproduce analysis-v1`.
- `runs/analysis_v1/README.md` or a new reproduction manifest.
- Tests for reproduction planning and path validation.

Intended behavior:

- Provide one documented command that regenerates analysis tables, statistics, and approved figures from frozen required inputs without rerunning expensive generation.
- The command must not run MatterGen, Con-CDVAE, CrystalFormer, CrystaLLM, Crys-JEPA generation, DFT, relaxation, CHGNet, or DXMag unless explicitly using already-frozen outputs as inputs.
- It should validate required inputs, report missing artifacts, build the unified analysis table, run figure/statistic generation, and verify row counts/checksums.

Expected shape:

- `maggenbench reproduce analysis-v1 --input-root <path> --output-root <path>`
- Defaults may point to repository-relative frozen inputs when present.
- Output should go to a clean reproduction directory, not silently overwrite tracked production files.

Scientific invariants:

- Unified analysis v1 semantics unchanged.
- No cohort row loss.
- Existing production checksums are not rewritten to hide changes.
- Generated runtime artifacts are not silently promoted into source control.

Tests that must pass:

- Unit tests with tiny fake frozen inputs.
- Existing unified-analysis and plotting utility tests.

Regression checks:

- Reproduction command reports exact expected cohort counts.
- Reproduction command fails loudly when required frozen inputs are missing or checksums mismatch.
- Generated outputs are byte-identical where byte identity is expected; otherwise summary counters and figure source tables match exactly.

Rollback boundary:

- Additive command and manifest; revert without changing generic analysis code.

## Phase 5D: One-Command Paper Reproduction Target

Affected files/modules:

- CLI reproduction command group.
- `runs/paper` or `runs/analysis_v1` manifest files.
- README reproducibility section.
- Docker/Compose files introduced in the Docker phase.

Intended behavior:

- Define a paper reproduction target that regenerates analysis tables, statistics, and figures from frozen required inputs without rerunning expensive generation or model inference.
- It should use frozen generated CIF manifests, Descriptor v1 outputs, CHGNet outputs, DXMag outputs, and annotation/join tables as inputs.
- It should produce a clean output bundle containing regenerated analysis CSVs, summary CSVs, figures, logs, and a provenance report.

Example target:

- `maggenbench reproduce analysis-v1`
- or `maggenbench reproduce paper`

The final name should be chosen after the analysis-v1 and paper scope are clearly separated. If the paper target is exactly analysis-v1, prefer one command and one documented alias rather than two near-identical commands.

Scientific invariants:

- Frozen generated inputs are treated as inputs, not regenerated.
- CHGNet and DXMag outputs are consumed as frozen model predictions, not recomputed by the paper target.
- No silent clipping/transformation of scientific outputs.

Tests that must pass:

- Lightweight reproduction test with minimal fixture inputs.
- Existing analysis and plotting tests.

Regression checks:

- A fresh clone plus mounted frozen artifacts can run the reproduction target.
- Missing large artifacts produce clear errors naming the logical artifact and expected mount/source.

Rollback boundary:

- Reproduction target is additive and can be reverted independently.

## Phase 5E: Docker Reproducibility Layer

Affected files/modules:

- Existing `Dockerfile`
- New Dockerfiles if needed, for example:
  - `docker/analysis/Dockerfile`
  - `docker/chgnet/Dockerfile`
  - `docker/dxmag/Dockerfile`
- Optional `docker-compose.yml`
- `environment*.yml` or lock/requirements files for separate environments.
- README Docker section.

Intended behavior:

- Provide a lightweight analysis/figure reproduction container that can run tests, build unified analysis from frozen inputs, and regenerate figures/statistics.
- Do not force MatterGen, Con-CDVAE, CrystalFormer, CrystaLLM, Crys-JEPA, CHGNet, and DXMag into one monolithic Python environment.
- Use separate model/backend containers only where appropriate, because generation/model dependencies may conflict.

Recommended Docker/Compose architecture:

- `analysis` service: installs MagGenBench lightweight dependencies, pandas, plotting stack, pymatgen if needed for lightweight validation/descriptor tests, and runs `maggenbench reproduce analysis-v1`.
- `test` service: same or narrower environment for lightweight unit tests.
- `chgnet` service: optional real CHGNet environment, CPU/GPU explicitly configured, no automatic downloads unless mounted/cache policy is documented.
- `dxmag` service: optional DXMag/sklearn/matminer environment with mounted model artifact and metadata checks.
- `generation-*` services: only if future reproduction requires model-specific generation; not part of paper reproduction by default.
- Shared mounted volumes:
  - read-only frozen inputs;
  - read-only model artifacts;
  - writable reproduction output directory;
  - optional package/model caches outside Git.

Scientific invariants:

- Analysis/figure reproduction must not rerun expensive generation or real model inference.
- Backend containers must preserve backend-specific scientific contracts and metadata checks.
- Docker must not hide checksum or row-count changes.

Tests that must pass:

- Containerized lightweight tests.
- Containerized `maggenbench --help`.
- Containerized dry/fake reproduction fixture.

Regression checks:

- `docker compose run --rm analysis maggenbench reproduce analysis-v1 ...` works with documented mounted inputs.
- Running the analysis container without required artifacts fails with clear missing-artifact messages.
- No Docker build copies local virtual environments, caches, secrets, donor repos, or generated temporary outputs.

Rollback boundary:

- Docker layer is additive. If backend-specific images are problematic, keep only the lightweight analysis image and document manual backend execution separately.

## Phase 6: Legacy Quarantine Or Removal

Affected files/modules:

- `scripts/legacy/*`
- `tables/*.py`
- older illustration scripts:
  - `scripts/illustrations/plot_model_stats_paper.py`
  - `scripts/illustrations/plot_spacegroup_distribution.py`
  - `scripts/illustrations/plot_compound_classes_stats_paper.py`
  - `scripts/illustrations/group_bar_chart.py`
- `src/mvpipeline/validation/chemistry copy.py.bak`
- `registry/artifacts.csv`

Intended behavior:

- For each legacy file, decide: keep as provenance, move to documented archive, replace with modern module, or delete.
- Remove accidental backup files only after confirming they are not needed to reproduce historical results.
- If `registry/artifacts.csv` remains, give it a schema/header or remove stale config reference.

Scientific invariants:

- Historical provenance remains recoverable.
- Existing production tables, figures, and checksums unchanged.
- No hidden reinterpretation of old `e_above_hull` scripts as current stability proxy.

Tests that must pass:

- Full lightweight test suite.
- Search-based checks that no active source imports removed legacy modules.

Regression checks:

- `rg` for each removed filename before deletion.
- `git ls-files` audit showing no accidental removal of CSV/CIF/figure provenance unless explicitly approved.

Rollback boundary:

- One cleanup group per commit. If provenance concern arises, restore that group only.

## Phase 7: README Rewrite And Documentation Refresh

Affected files/modules:

- `README.md`
- `ARCHITECTURE.md`
- `src/README.md`
- Selected docs under `docs/`
- Comments/docstrings with mojibake in `src/mvpipeline/io/*.py` and `src/mvpipeline/report/records.py` if desired.

Intended behavior:

- Rewrite `README.md` so a new contributor understands the repository without inspecting implementation files.
- Align docs with the current pipeline: validation, Descriptor v1, enrichment annotations, energy/magnetism contracts, unified analysis v1, and plotting.
- Remove stale output names such as `e_above_hull_results.csv` unless explicitly documenting legacy files.
- Clarify source/provenance/runtime artifact boundaries.
- Ensure every top-level directory has a documented purpose.

README sections to include:

- scientific scope;
- core models vs comparator cohorts;
- pipeline diagram;
- quick start;
- repository map;
- data/artifact policy;
- reproducibility;
- tests;
- Docker;
- adding a model;
- adding a descriptor;
- scientific interpretation caveats;
- provenance.

Scientific invariants:

- Documentation must keep proxy and prediction terminology precise.
- No generated outputs changed.

Tests that must pass:

- Full lightweight tests if code comments/docstrings only.
- Link/path spot checks for documented commands.

Regression checks:

- Search docs for forbidden or misleading terms:
  - `e_above_hull` for current CHGNet proxy outputs
  - `saturation magnetization`
  - `DFT magnetic moment`
  - `Curie`
  where not explicitly negated or contextualized.

Rollback boundary:

- Documentation-only changes are independently revertible.

## Phase 8: Repository Cleanliness Acceptance Pass

Affected files/modules:

- Current-code directories only after prior phases establish the source/provenance/runtime boundaries.
- No scientific data, generated tables, figures, or checksums unless explicitly approved.

Intended behavior:

- Enforce that current-code areas contain no unexplained backup, copy, temporary, obsolete, or zero-purpose files.
- Ensure no Python source remains under generated-data directories.
- Ensure no current code imports from `scripts/legacy`.
- Ensure current reusable logic lives under `src/mvpipeline`.
- Ensure machine-specific absolute paths do not exist in current reusable code.

Scientific invariants:

- All required invariants remain unchanged.
- Provenance files are retained or explicitly documented.

Tests that must pass:

- Full lightweight test suite.
- CLI help and dry-run smoke tests.
- Reproduction fixture test.

Regression checks:

- `git ls-files` scan for suspicious names in current-code areas: `*.bak`, `* copy*`, `tmp`, `old`, `debug`, `experimental`, zero-byte non-package files.
- `rg` scan proving current code does not depend on `scripts/legacy`.
- `rg` scan for machine-specific absolute paths in current source/scripts/config.
- `git ls-files` scan proving no `.py` files under generated-data directories such as `tables/` after migration.
- README repository map matches real top-level directories.

Rollback boundary:

- Cleanliness changes should be grouped by directory and reverted independently if provenance concerns arise.

## Highest-Value Opportunities

1. Canonical analysis/cohort registry shared by unified analysis and plotting.
2. Shared unified-analysis plotting utilities with stable group order and row-count guards.
3. One documented public analysis/reproduction entry point.
4. Shared resumable batch-stage orchestration for CHGNet and DXMag scripts.
5. Dockerized lightweight analysis/figure reproduction with separate optional backend environments.

## Highest-Risk Areas

1. Accidentally changing `sample_uid`/`structure_id` identity rules or cohort row counts.
2. Reclassifying Crys-JEPA as a core baseline rather than a comparator in common analysis.
3. Renaming or transforming CHGNet/DXMag outputs in ways that imply DFT stability, energy above hull, magnetic ordering, or saturation magnetization.
4. Collapsing incompatible generator/backend dependencies into one fragile environment.
5. Moving or deleting provenance artifacts before their role is documented.

## Final Definition Of Done

- No unexplained files/directories remain in current-code areas.
- No Python source lives under generated-data directories.
- No current code depends on `scripts/legacy`.
- Current reusable code lives under `src/mvpipeline`.
- Every top-level directory has a clearly documented purpose.
- Machine-specific absolute paths are absent from current reusable code and current scripts.
- Public execution surface is small, consistent, and documented.
- Canonical cohort registry exists and is used by unified analysis and plotting.
- Plotting conventions, group ordering, labels, and output conventions are centralized.
- One documented analysis entry point exists.
- `maggenbench reproduce analysis-v1` or the chosen equivalent is documented and tested on frozen inputs.
- Docker or Docker Compose reproduction path is documented and tested for lightweight analysis/figure reproduction.
- Large data/model artifacts that do not live in Git have documented supply/mount/checksum policy.
- All lightweight tests pass.
- Frozen scientific invariants are unchanged.
- README accurately matches the real repository.
- Fresh clone reproducibility is documented and tested with required mounted artifacts.
