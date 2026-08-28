# Manuscript figures

This directory contains the manuscript-selected publication artifacts.

Generated analysis outputs remain under
`reproduced/analysis_v2_magnetic/figures/`. The files in this directory are
selected snapshots intended for manuscript preparation and review.

## Main figures

| Manuscript figure | Scientific role | Reproduced source |
|---|---|---|
| Figure 1 | Study and analysis pipeline | `paper_pipeline_v2_preview` |
| Figure 2 | Structural and cohort overview | `manuscript_figure2_structural_overview_v2_preview` |
| Figure 3 | Magnetic-domain composition | `manuscript_figure3_magnetic_domain_v2_preview` |
| Figure 4 | Descriptor-space and PCA analysis | `manuscript_figure4_descriptor_space_v2_preview` |
| Figure 5 | Energy-magnetism landscape | `manuscript_figure5_energy_magnetism_v2_preview` |
| Figure 6 | Diversity and adaptation | `manuscript_figure6_diversity_adaptation_v2_preview` |

## Supplementary figures

- `supp01_pca_loadings`: complete PCA loading overview derived from
  `08_pca_loadings_v2`.

## Artifact policy

PDF files are the tracked manuscript publication artifacts.
Raster previews remain available in the reproducible figure output directory.

Internal analysis-stage labels such as `v2` and `_preview` are intentionally
removed from manuscript filenames.

These files should not be edited manually. Changes should be made in the
reproducible plotting code and regenerated before replacing the selected
manuscript artifact.
