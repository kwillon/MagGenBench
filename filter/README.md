# CIF Magnetic Reference Filter

A CIF-only, physics-informed workflow for screening generated crystal structures by proximity to empirical magnetic-material reference manifolds.

**Default reference model: Materials Project only — AFM, FM, FiM, NM (2,000 structures per branch, 8,000 total).** MAGNDATA is **not** part of the shipped default reference model or the default fitting configuration. This avoids using MAGNDATA as a reference when it was involved in generation-model fine-tuning. Overlap with training data from Materials Project has not been ruled out and should be assessed separately.

**Scientific meaning:** AFM-like, FM-like and FiM-like indicate reference affinity, **not** magnetic ground-state prediction. A positive `magnetic_reference_vs_NM_contrast` means closer to at least one magnetic reference branch than to NM.

## Install from the parent repository

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e './filter[paper,dev]'
```

## Score a CIF / extracted features

```bash
cifmagfilter score data/candidate.cif --output results/candidate.csv
cifmagfilter score-features --features results/features/structure_features.csv --output results/score_table.csv
```

```python
from cifmagfilter import CIFMagFilter
model = CIFMagFilter.from_pretrained()  # packaged MP-only reference
score = model.score_cif('data/candidate.cif')
```

All existing API names and model filenames are preserved: `reference_filter.npz`, `reference_filter.json`, `CIFMagFilter.from_pretrained()`, `cifmagfilter score`, `extract`, `workflow`, `fit-reference`, and `score-features`.

## Process the organized generator data

Keep generated CIFs **outside** `filter/`, e.g. `data/generators/<generator>/cifs/` with `manifest.csv` at generator level. Copy `configs/generators.example.json` to a config if you prefer using `cifmagfilter extract`; or run the batch orchestrator from the project root:

```bash
python filter/scripts/run_mp_pipeline.py --project . --limit 5   # sanity test
python filter/scripts/run_mp_pipeline.py --project .             # full processing
```

Outputs go to `results/mp_only/` by default. To avoid discarding extraction failures, review `rejected_structures.csv` and `generator_summary.csv` before publication or DFT selection.

## Reassess the historical DFT cohort with MP-only scores

```bash
python filter/scripts/recalculate_dft_mp_only.py \
  --scores results/mp_only/generator_scores.csv \
  --output-dir results/mp_only/dft_validation

python filter/scripts/plot_mp_only_publication.py
```

The recomputation uses SHA256 mapping of 324 DFT entries and 60 overlapping AFM/FM calculations from `paper/data/`; it refuses incomplete matches by default. The historical DFT candidates were originally selected with the previous filter, so this is a **retrospective re-scoring**, not an unbiased test cohort.

Figures and individual panels are generated in `results/mp_only/figures/`. The plotting script does **not** copy a raster DFT panel or reuse numerical DFT fractions from the old reference model.

## What is in the repo

- `src/cifmagfilter/` — unchanged public package structure, extractor, reference math, CLI and bundled MP-only model.
- `configs/` — original filenames retained; MP-only default configuration and generator example.
- `scripts/` — generator processing, MP model construction, DFT re-scoring and plotting.
- `paper/` — original article materials retained for provenance, plus new MP-only audit files and source maps.
- `tests/` — scientific invariants, regression checks, package API tests.
- `FILES_CHANGED.md` — exact added/modified/unchanged file inventory compared with the previous `filter.zip`.

**Historical-analysis note:** existing `paper/manifests/validation_metrics.json`, `paper/results/` and `paper/reproduce.py` continue to represent the original five-branch **MP + MAGNDATA** study. They are retained under the **same filenames** for reproducibility and must not be presented as the new MP-only validation. New validation is in `paper/results/mp_reference_validation_metrics.json` and `results/mp_only/` after executing the scripts.

For environment and data provenance, see `REPRODUCIBILITY.md`, `DATA.md`, and `paper/METHODS.md`. BSD 3-Clause; see `LICENSE`.
