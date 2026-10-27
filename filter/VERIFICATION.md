# Repository verification

This folder is designed to be placed under the parent Git repository as `filter/`. Existing filenames and CLI command names remain unchanged.

## Completed checks (current build)

- 29 tests passed; 2 tests skipped because `pymatgen` was not installed in the build runtime. The skipped tests exercise ordered/disordered CIF extraction and should run in GitHub Actions with the full chemistry stack.
- `cifmagfilter self-test` passed using four reference classes (0.900 synthetic nearest-branch agreement).
- Bundled MP-only model validated: AFM/FM/FiM/NM, 8,000 references (2,000 per class), 45 features, `k=15`, no `ref_MAGNDATA` array.
- Canonical model scoring and the batch orchestrator were smoke-tested from a separate temporary parent-project directory using two synthetic descriptor rows and `--skip-extract`; not claimed as a live CIF parsing test.
- Wheel built offline from the folder and inspected: both model files are included as `cifmagfilter/data/model/reference_filter.npz` and `.json`.
- Historic original `paper/` validations remain analytically separate from the current MP-only model.
- Provided full-run `generator_summary.csv` sanity check: 20,000 input, 18,485 scored; included in `paper/results/mp_generator_summary.csv`. The full individual-level score table and new DFT join are not bundled.
- Figure builder and DFT reassessment scripts are included; end-to-end regeneration of final MP-only figures requires the user's local `results/mp_only/generator_scores.csv` and DFT-audited joined scores. No final figures are invented in this archive.

## After copying into your project

```bash
cd ~/projects/magnetic-crystals
source .venv/bin/activate
python -m pip install -e './filter[paper,dev]'
python -m pytest -q filter/tests
python filter/scripts/check_repository.py
python filter/scripts/run_mp_pipeline.py --project . --skip-extract
python filter/scripts/recalculate_dft_mp_only.py --scores results/mp_only/generator_scores.csv
python filter/scripts/plot_mp_only_publication.py
```

The `--skip-extract` command intentionally reuses the complete extracted feature table; omit it only if you need to recompute descriptors. This avoids an unnecessary expensive rerun.

The optional GitHub Actions template at `ci/filter.yml` must be copied to the **parent** repo's `.github/workflows/filter.yml` to be discovered by GitHub.
