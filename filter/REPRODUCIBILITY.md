# Reproducibility

Two analytical contexts are **deliberately separate**.

## Current MP-only screening model

The model loaded by `CIFMagFilter.from_pretrained()` from `src/cifmagfilter/data/model/` contains 8,000 reference structures (AFM/FM/FiM/NM), 45 coordinates, a robust-scaled reference space and 15-neighbor distances. No MAGNDATA reference arrays are bundled in the current default model. MP-only reference validation is at `paper/results/mp_reference_validation_metrics.json`, with scaler and selection audit at `paper/manifests/mp_reference_*.csv`.

Model construction can be repeated from the original extracted MP reference feature table (not included due to size and source-data provenance):

```bash
python filter/scripts/build_reference_mp.py --features path/to/structure_features.csv --output path/to/model_output
```

Validation is internal leave-one-out nearest-neighbor consistency after fitting the scaler to the reference cohort; it is **not** an independent holdout accuracy estimate. DFT re-scoring uses the original historical cohort and retains selection limitations.

The complete WSL workflow:

```bash
python -m pip install -e './filter[paper,dev]'
python filter/scripts/run_mp_pipeline.py --project .
python filter/scripts/recalculate_dft_mp_only.py --scores results/mp_only/generator_scores.csv
python filter/scripts/plot_mp_only_publication.py
```

## Original five-branch publication benchmark (retained files)

All previously existing filenames in `paper/` are retained. `paper/reproduce.py`, `paper/figures.py`, `paper/manifests/validation_metrics.json`, and existing `paper/results/` files reproduce the **historical MAGNDATA+MP** benchmark. Those numbers (9,283 references; 5-branch agreement) are **not** scores of the current bundled model. Do not combine them with current MP-only results as if they came from one reference construction.

## Tests

Run `pytest -q` inside `filter/`. Tests requiring `pymatgen`, `SMACT` and `spglib` require the full installation; the limited local environment may skip CIF extraction tests. CI should run with all dependencies. For external source verification and unprocessed datasets, see `DATA.md`.
