# MagGenBench Repository Audit

## Executive Summary

This audit inspected the tracked repository on branch `codex/analysis-v1-refactor` for duplication, unclear ownership, legacy workflow residue, generated artifacts, and refactor opportunities. No source, test, data, or result files were modified during the audit.

The tracked repository is dominated by scientific data artifacts: `18,721` tracked files were found, including `18,432` CIF files. Only `154` tracked files are Python. The main maintainability issue is not one broken module, but multiple historical workflow generations coexisting: the original validation pipeline, legacy table/figure scripts, Phase 5A/5B enrichment scripts, Descriptor v1, unified analysis v1, and paper plotting outputs.

The highest-value refactor is to centralize cohort definitions and plotting group definitions without changing scientific identities, row counts, or Descriptor v1/unified-analysis semantics. The second is to move reusable batch/checkpoint orchestration from scripts into `src/mvpipeline`. The third is to separate source, provenance manifests, runtime outputs, and generated figures more clearly.

## Current Repository Architecture

- `src/mvpipeline`: reusable pipeline package. This contains CIF I/O, validation, deduplication, novelty, report writing, Descriptor v1, energy and magnetism contracts/backends, enrichment annotations/results joins, stage runners, and unified analysis.
- `src/cli`: Typer CLI entry point for validation.
- `src/ui`: Streamlit UI helpers and views for validation outputs.
- `scripts`: operational scripts and historical scripts. Current generations include `phase5a3`, `phase5a4`, `phase5a6`, `phase5b`, `crysjepa`, `analysis`, and `illustrations`; older scripts live under `scripts/legacy`.
- `config`: YAML settings for paths, models, validation thresholds, descriptors, energy, magnetism, relaxation, and benchmark behavior.
- `tests`: unit tests around Descriptor v1, energy/magnetism contracts and backends, enrichment, stage runners, stage-table resume logic, and unified analysis.
- `docs`: current contract/provenance docs plus older architecture docs.
- `registry`, `datasets`, `samples`, `archive/cifs`, `tables`, `figures`, `runs`: tracked metadata, reference data, generated CIF cohorts, historical CIF archives, CSV tables, generated figures, and run provenance.

## Inventory

Tracked top-level counts:

| Area | Count | Notes |
|---|---:|---|
| `samples` | 16000 | Tracked generated CIFs. |
| `archive` | 2432 | Tracked archived CIFs. |
| `src` | 84 | Main reusable code. |
| `scripts` | 46 | Mixed current wrappers, plotting, and legacy scripts. |
| `tables` | 43 | Many generated/runtime CSVs plus table-building scripts. |
| `figures` | 32 | Generated plots in Git. |
| `tests` | 23 | Active unit tests. |
| `docs` | 11 | Mixed current and older docs. |
| `config` | 9 | Split runtime configuration. |
| `runs` | 13 | Run scripts/checksums/README files. |
| `registry` | 8 | Registry CSV metadata; `registry/artifacts.csv` is zero-byte. |
| `datasets` | 11 | Train-reference CSVs and raw-data scripts. |

Extension counts:

| Extension | Count |
|---|---:|
| `.cif` | 18432 |
| `.py` | 154 |
| `.csv` | 49 |
| `.md` | 24 |
| `.png` | 20 |
| `.sh` | 10 |
| `.yaml` | 9 |
| `.pdf` | 6 |
| `.svg` | 6 |

## Duplication Findings

### Cohort And Plot Group Definitions

The same eight unified analysis groups are defined independently in:

- `scripts/illustrations/plot_structural_distributions_v1.py`
- `scripts/illustrations/plot_dxmag_predicted_moment_v1.py`
- `scripts/illustrations/plot_magnetic_screening_fraction_v1.py`
- `scripts/illustrations/plot_3d_4f_fraction_v1.py`
- `scripts/illustrations/plot_compound_class_heatmap_v1.py`
- partly in `scripts/illustrations/plot_unified_analysis_v1.py`

Evidence: each script repeats MatterGen baseline/fine-tuned, Con-CDVAE baseline/fine-tuned, CrystalFormer baseline, CrystaLLM baseline, Crys-JEPA Base, and Crys-JEPA Refined group labels. The scripts also repeat `INPUT = ROOT / "runs" / "analysis_v1" / "unified_analysis_v1.csv"`, `OUTDIR = ROOT / "figures" / "unified_analysis_v1"`, `len(df) != 10684` checks, subset-by-`analysis_cohort`/`analysis_family`, and summary CSV output patterns.

Classification: `NEEDS REVIEW`, because labels and ordering are scientific/reporting semantics.

### Production Cohort Manifest

`scripts/analysis/build_unified_analysis_v1.py` hard-codes the production cohort specs and expected counts. `src/mvpipeline/analysis/unified.py` owns the merge semantics but not the production cohort registry.

Evidence: the script contains `AnalysisCohortSpec(...)` entries for `baseline_master`, `mattergen_finetuned`, `concdvae_finetuned`, `crysjepa_base`, and `crysjepa_refined`, plus `EXPECTED_ROWS = 10684` and per-status counts. Tests exercise the generic `AnalysisCohortSpec` machinery, not a shared production registry.

Classification: `NEEDS REVIEW`, because centralization must preserve exact identities and counts.

### Fine-Tuned And Crys-JEPA Annotation Preparers

The four scripts below are near copies with only cohort-specific constants changed:

- `scripts/phase5b/prepare_mattergen_finetuned_annotations.py`
- `scripts/phase5b/prepare_concdvae_finetuned_annotations.py`
- `scripts/crysjepa/prepare_crysjepa_base_annotations.py`
- `scripts/crysjepa/prepare_crysjepa_refined_annotations.py`

Evidence: `git diff --no-index` between MatterGen fine-tuned and Con-CDVAE fine-tuned shows changes only in input/output paths, stable-ID prefix, `model_name`, `model_short`, `run_uid`, and final PASS label. The same pattern holds for Crys-JEPA Base.

Classification: `NEEDS REVIEW`, because stable `sample_uid`, `model_short`, and `run_uid` rules are scientific/provenance invariants.

### Batch Energy And Magnetism Scripts

`scripts/phase5a4/run_batch_chgnet.py` and `scripts/phase5a4/run_batch_dxmag.py` duplicate resume/checkpoint orchestration, pending-row selection, manifest-order validation, checkpoint merging, status summaries, and output logging. Only backend construction and fieldnames differ.

Evidence: both scripts call `load_manifest_rows`, `prepare_records`, `success_ids_from_records`, `merge_stage_records_incremental`, chunk through `--checkpoint-every`, write with `write_stage_csv_atomic`, and assert final order.

Classification: `SAFE` to consolidate orchestration into a shared helper if backend construction and fieldnames remain explicit and tests preserve resume behavior.

### CSV Loading And Validation

CSV readers and validators appear in several places:

- `src/mvpipeline/io/stage_tables.py`
- `src/mvpipeline/descriptors/batch.py`
- `src/mvpipeline/pipeline/enrichment_annotations.py`
- `src/mvpipeline/pipeline/enrichment_results_join.py`
- `scripts/phase5a4/batch_common.py`
- `scripts/phase5a4/prepare_batch_manifest.py`
- `scripts/phase5a4/run_batch_join.py`
- tests that reimplement `csv.DictWriter`/`csv.DictReader` fixtures

Evidence: multiple functions independently open CSVs with `encoding="utf-8-sig"`, materialize `DictReader` rows, validate unique IDs, and enforce `sample_uid == structure_id`.

Classification: `NEEDS REVIEW`, because some validators enforce different table-specific contracts.

### Legacy Benchmark/Table Logic

`scripts/legacy/build_benchmarking_table.py`, `scripts/legacy/build_benchmarking_baseline_table.py`, and `scripts/legacy/make_benchmark_ready_table.py` overlap in model-label normalization, model ordering, Materials Project/reference matching, duplicate metrics, and table output.

Evidence: repeated `MODEL_LABELS`/`MODEL_ORDER`, repeated `near_duplicate_percent`, and hard-coded historical input/output paths.

Classification: `NEEDS REVIEW`, because these scripts may be historical provenance for existing tables even though no tracked caller was found by filename search.

## Legacy Or Obsolete-File Findings

- `scripts/legacy/*`: no tracked callers found by filename search for the inspected legacy scripts. They contain older absolute `/mnt/tank/...` paths and several generate now-superseded tables. Classification varies by file; see action table.
- `src/mvpipeline/validation/chemistry copy.py.bak`: tracked backup-like file. It differs from `chemistry.py` in charge-neutrality behavior, so it is not a byte-for-byte duplicate. It is suspicious because it is a `.bak` file in source and no imports were found. Classification: `NEEDS REVIEW`.
- Older illustration scripts `plot_model_stats_paper.py`, `plot_spacegroup_distribution.py`, `plot_compound_classes_stats_paper.py`, and `group_bar_chart.py` are not called by tracked files by filename search. Some produced tracked figures, so classify as provenance-sensitive.

## Zero-Byte And Empty-Directory Findings

Zero-byte tracked files:

| Path | Evidence | Classification |
|---|---|---|
| `registry/artifacts.csv` | Tracked file length is zero. Referenced in `config/paths.yaml` as artifact registry. | `NEEDS REVIEW` |
| `src/cli/__init__.py` | Zero-byte package marker. | `DO NOT TOUCH` |
| `src/ui/__init__.py` | Zero-byte package marker. | `DO NOT TOUCH` |

Empty/suspicious local directory:

- `.pytest_cache`: local directory scan reported it and then hit permission denied. Git does not track empty directories, so this is not a tracked-repository issue. It should remain ignored/untracked.

## Hard-Coded Path Findings

Hard-coded machine paths were found in:

- `scripts/legacy/make_clean_compound_class_table.py`
- `scripts/legacy/make_clean_compound_class_table_v2.py`
- `scripts/legacy/make_benchmark_ready_table.py`
- `scripts/legacy/make_benchmarking_baseline_pdf.py`
- `scripts/legacy/debug_mp_hits.py`
- `scripts/legacy/build_mp_ref_for_benchmark.py`
- `scripts/legacy/build_benchmarking_table.py`
- `scripts/legacy/build_benchmarking_baseline_table.py`
- `scripts/legacy/add_validation_status_to_master.py`
- `scripts/legacy/add_compound_class.py`
- `scripts/illustrations/plot_spacegroup_distribution.py`
- `scripts/illustrations/plot_compound_classes_stats_paper.py`
- `scripts/illustrations/plot_model_stats_paper.py`

Evidence: these files contain `/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench` or equivalent split absolute path construction.

Other path concerns:

- `scripts/config.py` appends `../crystalformer/src` to `sys.path`, implying an external checkout.
- Phase 5B/Crys-JEPA annotation preparers insert both `src` and `scripts/legacy` into `sys.path`, because they import `classify_formula` from `scripts/legacy/add_compound_class.py`.
- `scripts/phase5a3/run_phase5a3_real_join.py` writes an intermediate annotation row to `/tmp/phase5a3_annotations_one_row.csv`. This is portable on Unix but not Windows-native.

## Generated-Artifact Placement Findings

Generated artifacts are mixed with source and docs:

- `samples/` and `archive/cifs/` contain `18,432` tracked CIFs.
- `tables/` contains production and legacy CSVs, generated energy and magnetism outputs, generated annotation/join tables, cache JSON, and table-building scripts.
- `figures/` contains generated PNG/PDF/SVG outputs.
- `runs/` contains shell scripts, READMEs, and checksum files. Some referenced generated CSVs are not tracked, while checksums are tracked.

This may be intentional provenance, but it makes source review noisy and makes contributor onboarding harder. Future cleanup should separate immutable release/provenance artifacts from runtime outputs and reusable source.

## Naming And Organization Problems

- `CrystalLLM` and `CrystaLLM` both appear in docs/config comments. Current analysis scripts use `CrystaLLM`.
- `Con-CDVAE`, `concdvae`, `cdvae`, `con-cdvae`, and `con_cdvae` all appear in different contexts.
- `model_short` values vary: `mg_ft`, `cdvae_ft`, `crysjepa_base`, `crysjepa_refined`.
- `structure_id`, `sample_uid`, source IDs, and CIF filenames are repeatedly adapted in scripts instead of coming from one manifest schema helper.
- `tables/legacy/*` and root-level legacy table names coexist with numbered table directories.
- Some docs and comments are mojibake, especially `ARCHITECTURE.md`, `src/README.md`, `src/mvpipeline/io/*.py`, and `src/mvpipeline/report/records.py`.

## Plotting And Analysis Duplication

Current unified-analysis plotting scripts should share:

- canonical group registry and display labels;
- `baseline_master` family subsetting;
- unified row-count and required-column guards;
- common output directory and file naming conventions;
- Matplotlib style;
- summary CSV writer helpers;
- boolean parsing and numeric coercion helpers.

The scripts should remain thin, metric-specific wrappers. The shared utility must not change the plotted quantities, cohorts, row counts, or display ordering.

## Scientific-Risk Areas

- Descriptor v1 is frozen. Do not change `src/mvpipeline/descriptors/schema.py`, `records.py`, extraction semantics, missing-value policy, units, or field order except under a separate Descriptor v2 process.
- Unified analysis v1 semantics are row-preserving and join Descriptor v1 rows to downstream annotations by `sample_uid == structure_id`. Do not alter identity rules or row counts.
- CHGNet outputs are model energies/proxies, not DFT stability or energy above hull. `config/energy.yaml` correctly labels `max(formation_energy_proxy_eV_per_atom, 0)` as a stability proxy, while README still lists `tables/06_energy/e_above_hull_results.csv` as a main output.
- DXMag outputs are raw composition-model predictions in `muB` per formula unit for the verified profile. They must not be renamed to magnetic ordering, saturation magnetization, Curie temperature, or DFT magnetic moment.
- Crys-JEPA is a comparator cohort in common unified-analysis infrastructure, not a fifth core baseline model.
- Existing production checksums under `runs/*/final_sha256.txt` should not be rewritten to hide changes.

## Proposed Actions

| Path | Problem | Evidence | Proposed Action | Classification |
|---|---|---|---|---|
| `scripts/illustrations/plot_*_v1.py` | Repeated group registry, input/output paths, row-count checks, style, summary writing. | Repeated `GROUPS`, `INPUT`, `OUTDIR`, `10684` checks. | Add shared plotting/unified-analysis utility and migrate one script at a time. | `NEEDS REVIEW` |
| `scripts/analysis/build_unified_analysis_v1.py` | Production cohort specs live only in script. | Hard-coded `AnalysisCohortSpec` list and expected counts. | Move specs and expected counters into canonical registry module/config consumed by script and tests. | `NEEDS REVIEW` |
| `src/mvpipeline/analysis/unified.py` | Generic merge logic is good but lacks production registry boundary. | Tests exercise generic specs; production specs are external. | Keep semantics unchanged; add adjacent `cohorts.py` or config loader, not merge changes. | `DO NOT TOUCH` for semantics |
| `scripts/phase5b/prepare_*_annotations.py`, `scripts/crysjepa/prepare_*_annotations.py` | Four near-copy manifest adapters. | Diffs show mostly cohort constants changed. | Replace with parameterized source adapter using explicit cohort config and regression tests for IDs/counts. | `NEEDS REVIEW` |
| `scripts/phase5a4/run_batch_chgnet.py`, `scripts/phase5a4/run_batch_dxmag.py` | Duplicated resumable checkpoint loop. | Both scripts share pending/chunk/merge/write/order validation. | Move shared batch runner into `src/mvpipeline/pipeline/batch_stage.py`; keep scripts as backend wrappers. | `SAFE` |
| `scripts/phase5a4/batch_common.py` | Reusable manifest preparation lives under scripts. | Imported by two batch scripts; does structure loading and ID validation. | Move reusable parts to `src/mvpipeline/pipeline` or `src/mvpipeline/io`; keep script import shim temporarily. | `SAFE` |
| `scripts/phase5a4/run_batch_join.py` | Duplicates CSV read and annotation ID checks already enforced in join module. | Reads rows, validates `sample_uid == structure_id`, then calls `run_enrichment_results_join`. | Keep as thin CLI; consider moving only CLI parsing and preflight to shared helper if still useful. | `NEEDS REVIEW` |
| `src/mvpipeline/io/stage_tables.py` | Two merge functions share validation/indexing internals. | `merge_stage_records_for_resume` and `merge_stage_records_incremental` duplicate `index_records`. | Extract private index helper with tests unchanged. | `SAFE` |
| `src/mvpipeline/pipeline/enrichment_results_join.py` | Robust CSV validation is local to one module. | `_read_csv_table`, `_validate_fieldnames`, `_materialize_rows`. | Consider moving generic CSV schema validation into `io/stage_tables.py` only if callers need exact behavior. | `NEEDS REVIEW` |
| `src/mvpipeline/descriptors/batch.py` | Manifest validation overlaps with batch/enrichment validation. | `_validate_manifest_rows` enforces unique IDs and `sample_uid == structure_id`. | Keep Descriptor v1 contract local unless extracting a no-semantics shared helper. | `DO NOT TOUCH` for semantics |
| `scripts/legacy/add_compound_class.py` | Legacy module is imported by current Phase 5B/Crys-JEPA scripts via `sys.path`. | Preparers insert `scripts/legacy` and import `classify_formula`. | Move `classify_formula` into `src/mvpipeline` with compatibility import or wrapper. | `NEEDS REVIEW` |
| `scripts/legacy/build_benchmarking_table.py` | Large historical benchmark implementation with duplicated model labels/order and MP matching. | No tracked caller found by filename search; hard-coded root path. | Archive as provenance or replace with documented modern benchmark module after table equivalence check. | `NEEDS REVIEW` |
| `scripts/legacy/build_benchmarking_baseline_table.py` | Similar legacy benchmark logic. | No tracked caller found; duplicates model order and near-duplicate metrics. | Same as above. | `NEEDS REVIEW` |
| `scripts/legacy/make_benchmark_ready_table.py` | Legacy table builder with absolute paths and bespoke CIF path resolution. | Hard-coded `/mnt/tank/...`; duplicate model labels. | Preserve until modern source of equivalent table is documented; then archive/remove. | `NEEDS REVIEW` |
| `scripts/legacy/e_above_hull.py`, `scripts/legacy/e_above_hull_alex.py` | Deprecated naming conflicts with current proxy terminology. | Files compute/label `e_above_hull`; current docs prohibit relabeling proxy as e_above_hull. | Do not use in current pipeline; remove only after provenance decision. | `NEEDS REVIEW` |
| `scripts/legacy/mlff_relax.py`, `scripts/legacy/relax_from_cif_path.py` | Heavy relaxation scripts outside current controlled architecture. | Use pandas, relaxation outputs, CLI defaults; no tracked callers found. | Keep out of current local workflows; archive/remove after confirming no reproduction dependency. | `NEEDS REVIEW` |
| `scripts/legacy/debug_mp_hits.py`, `build_mp_ref_for_benchmark.py`, `make_benchmarking_baseline_pdf.py`, `make_clean_compound_class_table*.py` | Historical one-off scripts with absolute paths and generated outputs. | No tracked callers found; hard-coded `/mnt/tank/...`. | Archive/remove after matching generated tables/figures to provenance docs. | `NEEDS REVIEW` |
| `src/mvpipeline/validation/chemistry copy.py.bak` | Backup-like tracked source file. | `.bak` suffix; no imports found; diff from current `chemistry.py` shows older behavior. | Decide whether it is provenance. If not, remove in a dedicated cleanup PR. | `NEEDS REVIEW` |
| `registry/artifacts.csv` | Zero-byte registry file. | File length zero; referenced in `config/paths.yaml`. | Either populate with schema/header or remove/update config if unused. | `NEEDS REVIEW` |
| `src/cli/__init__.py`, `src/ui/__init__.py` | Zero-byte files. | Package markers. | Leave unchanged. | `DO NOT TOUCH` |
| `config/paths.yaml` | Contains stale root-level table paths and paths to untracked/generated dirs. | `current_master` points to `tables/master_structures...`, while tracked current table is under `tables/01_master`. | Reconcile path config with current numbered-table layout after caller audit. | `NEEDS REVIEW` |
| `config/models.yaml` | Core model list lacks comparator cohorts. | Lists only four enabled models, which is correct for baselines but incomplete for unified analysis comparisons. | Keep baseline config; add separate analysis cohort registry for fine-tuned/Crys-JEPA cohorts. | `DO NOT TOUCH` baseline semantics |
| `README.md` | Outdated output paths and duplicate section headings. | Lists `tables/06_energy/e_above_hull_results.csv`; repeated `## Basic usage` and `## Run magnetic screening`. | Update docs after refactor to reflect proxy terminology and current directories. | `NEEDS REVIEW` |
| `ARCHITECTURE.md`, `src/README.md`, comments in `src/mvpipeline/io/*`, `report/records.py` | Mojibake and stale architecture references. | Text displays mojibake; mentions modules like `report.aggregator`/`report.schema` not present. | Rewrite/replace docs without changing code behavior. | `SAFE` for docs only |
| `scripts/config.py` | Adds external `../crystalformer/src` to `sys.path`. | Direct `sys.path.append(os.path.join(testdir, "../crystalformer/src"))`. | Remove or quarantine if unused; otherwise document external dependency. | `NEEDS REVIEW` |
| `tables/add_cifs_back*.py`, `tables/build_unified_master_dataset.py`, `tables/downsample_mattergen_balanced.py` | Source scripts live inside generated table area. | Python files tracked under `tables/`. | Move to `scripts/legacy` or `scripts/data_prep` after caller/provenance check. | `NEEDS REVIEW` |
| `samples/**`, `archive/cifs/**` | Large generated/scientific data mixed in source repo. | `18,432` tracked CIF files. | Do not remove in code refactor; decide separately whether to move to release artifact/data package. | `DO NOT TOUCH` |
| `tables/03_features`, `tables/04_magnetic_screening`, `tables/06_energy`, `tables/07_magnetic_descriptors` | Generated production CSVs tracked. | Current unified analysis inputs/results live here. | Keep unchanged during refactor; document source vs runtime artifact boundary. | `DO NOT TOUCH` for current production outputs |
| `figures/**` | Generated plots tracked. | 32 tracked PNG/PDF/SVG figure files. | Keep unchanged; regenerate only in explicit figure reproduction phase. | `DO NOT TOUCH` |
| `runs/*/final_sha256.txt` | Production checksum provenance. | Tracked checksum files under run directories. | Never rewrite as cleanup; only update through explicit reproduction procedure. | `DO NOT TOUCH` |

## Files Investigated And Explicitly Left Unchanged

- `src/mvpipeline/descriptors/*`: Descriptor v1 is frozen; schema/records/extraction semantics must remain unchanged.
- `src/mvpipeline/analysis/unified.py`: current row-preserving unified merge semantics are covered by tests and must remain unchanged.
- `src/mvpipeline/energy/*` and `src/mvpipeline/magnetism/*`: contracts correctly distinguish proxies and raw predictions from DFT stability/magnetic ordering.
- `src/mvpipeline/pipeline/enrichment_annotations.py`: current docs and tests establish row-preserving recomputation/annotation semantics.
- `src/mvpipeline/pipeline/enrichment_results_join.py`: strict join behavior is well tested and should not be broadened casually.
- `tests/*`: tests intentionally encode invariants and should not be changed during cleanup except to add new regression coverage.
- `config/magnetism.yaml`: contains verified DXMag metadata and feature labels; do not reformat casually.
- `config/descriptors.yaml`: Descriptor v1 runtime configuration; frozen semantics.
- `tables/04_magnetic_screening/*`, `tables/06_energy/*`, `tables/07_magnetic_descriptors/*`: production/runtime scientific outputs.
- `samples/**` and `archive/cifs/**`: scientific data/provenance, not cleanup targets in this refactor.

## Classification Counts

- `SAFE`: 4
- `NEEDS REVIEW`: 19
- `DO NOT TOUCH`: 8

