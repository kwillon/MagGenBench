# Frozen publication inputs and results

This is the single tracked store for publication numerical inputs, complementing
the unchanged numbered analysis stages under `tables/`.

- `fig05_energy_magnetism.csv`: ten-set energy/moment source (12281 rows,
  12277 finite pairs); loader `manuscript_figure5_v2.py`.
- `crystalformer_finetuned_descriptors.csv`, `crystallm_finetuned_descriptors.csv`:
  the two added FT descriptor populations, used by Figure 8 and publication PCA.
- `fig06_*`: ten-set diversity/class sources used by Figure 6.
- `fig08_*`: original presence-based three-objective results, retained unchanged.
- `figure8/figure08_scenario_*_v2.csv`: S1/S2/S3 metrics, rankings/distributions,
  and pairwise dominance; canonical Figure 8 uses S1 for B–D.
- `figure8/figure08_criteria_*_v2.csv`: original A and four-objective B/C controls.
- `figure8/figure08_ablation_*_v2.csv`: controls dropping only the separate QC
  objective. Remaining yields retain their nominal denominator of 2000.
- `figure8/scenario_sensitivity_publication.csv`: full-precision SI export.
- `figure5_overlap/`: verified OVL/SWD, identities, directions and resampling arrays.
  Stored metadata retains its original path strings and hashes.
- `path_relocations.json`: exact original-to-current path map for historical
  provenance. Use `mvpipeline.analysis.artifact_paths.resolve_artifact_path` when
  reading historical metadata.

CSV/NPZ bytes were preserved during reorganization. Do not overwrite frozen
results when rerunning analyses: use a new directory under `reproduced/`.
Formatted SI prose/tables live under `paper/supporting_information/`, technical
audit reports under `reproduced/`, and reproduction instructions in `docs/figures/`.
