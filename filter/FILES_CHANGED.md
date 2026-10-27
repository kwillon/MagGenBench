# File-by-file changes relative to previous `filter.zip`

**Base archive:** the clean `filter.zip` from the preceding GitHub release in this conversation.

**Compatibility:** all existing file paths have been retained; no existing files were deleted or renamed. The existing commands `cifmagfilter score`, `score-features`, `extract`, `workflow`, and `fit-reference` remain available. The **scientific default model changed** from the five-branch MP+MAGNDATA configuration to the four-branch MP-only configuration; computed contrasts therefore generally change. This is a model/data change, not a backward-compatible numerical continuation.

**Current model:** 8,000 MP references, AFM/FM/FiM/NM, 45 features, 15-NN. **Historical paper results:** five-branch MP+MAGNDATA analyses intentionally preserved in their original files and described as historical.

No large CIF archives or locally generated scores were inserted into the GitHub bundle. Included static `paper/results/mp_generator_summary.csv` is from the user's 20,000-structure MP-only run (18,485 scored). Reproducing current DFT figures still requires full local individual-level scores and SHA verification.


## Modified files (12)

- `DATA.md` — Separated current MP-only datasets from historical five-branch files
- `README.md` — Installation, use and scientific framing for current MP-only model
- `REPRODUCIBILITY.md` — Separated current and historical reproducibility workflows
- `VERIFICATION.md` — Updated to reflect verified checks and limitations
- `ci/filter.yml` — CI template now supports filter/ in parent repository
- `configs/filter.example.json` — Removed MAGNDATA dataset from example config
- `src/cifmagfilter/cli.py` — Default refitting/workflow/reference classes changed to MP-only; existing command names kept
- `src/cifmagfilter/data/model/reference_filter.json` — Default model metadata switched to four reference branches
- `src/cifmagfilter/data/model/reference_filter.npz` — Packaged default model replaced by MP-only reference arrays (same filename)
- `tests/test_model_artifacts.py` — Updated default model expectations and added MP-only artifact tests
- `tests/test_publication_invariants.py` — Updated public-model branches, while keeping historical paper numerical checks
- `tests/test_reference_math.py` — Added MP-only reference-score regression test

## Added files (13)

- `configs/generators.example.json`
- `paper/data/dft_afm_source_map.csv`
- `paper/data/dft_fm_source_map.csv`
- `paper/manifests/mp_reference_feature_selection_audit.csv`
- `paper/manifests/mp_reference_scaler.csv`
- `paper/results/mp_generator_summary.csv`
- `paper/results/mp_reference_validation_metrics.json`
- `scripts/build_reference_mp.py`
- `scripts/check_repository.py`
- `scripts/plot_mp_only_publication.py`
- `scripts/recalculate_dft_mp_only.py`
- `scripts/run_mp_pipeline.py`
- `FILES_CHANGED.md` — this change inventory

## Removed or renamed files (0)

None.


## Unchanged existing files (57)

- `.gitignore`
- `CITATION.cff`
- `CONTRIBUTING.md`
- `DESCRIPTORS.md`
- `LICENSE`
- `configs/paper.example.json`
- `docs/README.md`
- `environment/README.md`
- `environment/requirements.txt`
- `paper/METHODS.md`
- `paper/__init__.py`
- `paper/analysis.py`
- `paper/assets/README.md`
- `paper/export_reference_model.py`
- `paper/figures.py`
- `paper/manifests/benchmark_manifest.example.csv`
- `paper/manifests/descriptor_policy.csv`
- `paper/manifests/feature_selection_audit.csv`
- `paper/manifests/features.csv`
- `paper/manifests/scaler.csv`
- `paper/manifests/validation_metrics.json`
- `paper/reproduce.py`
- `paper/results/ablation_composition_reference_summary.csv`
- `paper/results/ablation_magnetic_topology_reference_summary.csv`
- `paper/results/benchmark_reproduction_manifest.json`
- `paper/results/generator_benchmark.csv`
- `paper/results/generator_query_summary.csv`
- `paper/results/missingness_by_dataset.csv`
- `paper/results/missingness_summary_by_dataset.csv`
- `paper/results/reference_branch_confusion.csv`
- `paper/results/reference_control_generator_metrics.csv`
- `paper/results/reference_control_reference_metrics.csv`
- `paper/results/reference_controls_metadata.json`
- `paper/results/reference_math_equivalence.json`
- `paper/results/reference_validation_scores.csv`
- `paper/results/reference_validation_summary.csv`
- `paper/results/representation_comparison.csv`
- `paper/run_reference_benchmark.py`
- `paper/run_reference_controls.py`
- `paper/sensitivity_magndata_sha_dedup.py`
- `pyproject.toml`
- `requirements-optional.txt`
- `requirements.txt`
- `scripts/prepare_benchmark.py`
- `scripts/visualize_pair_graph.py`
- `src/cifmagfilter/__init__.py`
- `src/cifmagfilter/core.py`
- `src/cifmagfilter/model.py`
- `src/cifmagfilter/reference.py`
- `tests/fixtures/disordered_femn_o.cif`
- `tests/fixtures/feo_ordered.cif`
- `tests/fixtures/gdfe_ordered.cif`
- `tests/fixtures/nacl_ordered.cif`
- `tests/test_cif_only_boundary.py`
- `tests/test_paper_pipeline.py`
- `tests/test_repository_structure.py`
- `tests/test_smoke.py`
