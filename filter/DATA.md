# Data and model artifacts

The bundled model at `src/cifmagfilter/data/model/reference_filter.npz` and `reference_filter.json` uses Materials Project AFM/FM/FiM/NM reference cohorts (2,000 each). Its feature order and reference scaler are in the NPZ; the MP-only human-readable scaler and reference audit are `paper/manifests/mp_reference_scaler.csv` and `paper/manifests/mp_reference_feature_selection_audit.csv`. MP-only internal validation metrics are `paper/results/mp_reference_validation_metrics.json`.

**Existing historical files are preserved under their previous names.** `paper/manifests/features.csv`, `paper/manifests/scaler.csv`, `paper/manifests/validation_metrics.json` and older `paper/results/*` refer to the original five-branch MP+MAGNDATA study. Although both workflows use the same descriptor names, robust-scaler coordinates and distances are **not interchangeable**.

## Generator data outside Git

Put flattened CIFs in `data/generators/<dataset>/cifs/` and retain provenance in `manifest.csv` and raw generation settings outside the Git repository. Do not check in private/raw generator archives or DFT calculation folders. The ten configured generator groups and their exact dataset names are in `configs/generators.example.json`.

`paper/data/dft_fm_source_map.csv` and `paper/data/dft_afm_source_map.csv` preserve SHA256 mappings and measured DFT labels for 324 unique FM-initiated calculations and 60 overlapping AFM comparisons. Those DFT labels are historical and have **not** been fabricated or re-evaluated. SHA-to-current-CIF matching and MP-only contrast reassignment run locally using `scripts/recalculate_dft_mp_only.py`.

## Scientific limitations

- AFM/FM/FiM are reference labels, not demonstrated magnetic ground states.
- DFT historical selection used the old filter and is not an unbiased independent cohort.
- Occupancy disorder/partial site occupancy is not supported in canonical ordered-CIF extraction.
- A successful CIF parse does not establish crystal thermodynamic stability.
- Scored fraction and chemical diversity must be considered alongside magnetic-reference enrichment, especially for target-conditioned generators.
- Materials Project may overlap with a generator's training data; no proof of complete independence is claimed.
