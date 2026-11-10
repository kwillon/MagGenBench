# Publication figures

Selected publication PDFs, captions, this map, checksums and `legacy/` belong here.
Captions are consolidated in [figure_captions.md](figure_captions.md).
Raster previews and technical audits live under `reproduced/`.

| Figure | Selected PDF | Reproduction code | Scientific inputs |
|---|---|---|---|
| 1 | [Pipeline](fig01_pipeline.pdf) | Supplied artwork; historical code in `scripts/illustrations/plot_paper_pipeline_v3.py` | [Source](../../reproduced/figure1/fig01_pipeline_source.png); [preview](../../reproduced/figure1/previews/fig01_pipeline.png) |
| 2 | [Structural QC](fig02_structural_overview.pdf) | `scripts/illustrations/plot_manuscript_figure2_v2.py` | Full `tables/02_validation/` and `tables/03_features/` QC records |
| 3 | [Magnetic domain](fig03_magnetic_domain.pdf) | `scripts/illustrations/plot_manuscript_figure3_v2.py` | Frozen `tables/10_analysis_v2_magnetic/` plus FT descriptors in `tables/figure_sources/` |
| 4 | [Reference screening / DFT](fig04_magnetic_reference_dft.pdf) | `scripts/illustrations/restyle_figure4_original_vectors.py`; `filter/scripts/plot_mp_only_publication.py` | Original statistical vectors and retrospective DFT; see [limitations](../../docs/figures/figure4_reproduction.md) |
| 5 | [Energy–magnetism](fig05_energy_magnetism.pdf) | `scripts/illustrations/plot_manuscript_figure5_v2.py` | `tables/figure_sources/fig05_energy_magnetism.csv` |
| 6 | [Diversity / adaptation](fig06_diversity_adaptation.pdf) | `scripts/illustrations/plot_fig06_diversity_adaptation_palette_preview.py` | `tables/figure_sources/fig06_compound_classes.csv`, `fig06_diversity_summary.csv` |
| 7 | [Multiobjective trade-offs](fig07_multiobjective.pdf) | `scripts/analysis/build_paper_multiobjective_figure.py` | `tables/figure_sources/figure8/figure08_scenario_{metrics,rankings,pareto}_v2.csv` |
| Supplementary 1 | [PCA loadings](supp01_pca_loadings.pdf) | `scripts/illustrations/plot_paper_pca.py` | Frozen analysis and two FT descriptor CSVs |
| Supplementary 2 | [Descriptor space](supp02_descriptor_space.pdf) | `scripts/illustrations/plot_paper_pca.py` | Frozen analysis and two FT descriptor CSVs |

Verified standalone captions for Figures 1/6 and the supplementary PCA figures
were not recovered; their captions require the external manuscript.
The selected multiobjective comparison is Figure 7 (formerly Figure 8).

Figure 7 retains the Art Nouveau hybrid v2 scientific content and layout, with
Ebrima Regular typography matching Figure 1. The pre-typography v2 archive remains
unchanged; text-only export checks preserve all numbers, data vectors and images.
A contains five metrics; B is the S1 scatter with atomic-content marker size and
S1 Pareto outlines; C is the S1 rank distribution; D is S1 Top-5 frequency.
S2/S3 and alternative criteria are in the
[Supporting Information map](../supporting_information/README.md).
`scripts/analysis/build_paper_figure08.py` retains the historical presence-based
analysis and exports exploratory artifacts only under `reproduced/figure8/`.

See [reproduction instructions](../../docs/figures/README.md). Figure 4 retains
original statistical vectors rather than numerically different recalculations.
The ten-set Figure 6 still uses the documented palette-preview entry point;
the historical eight-set implementation is retained.
The current typography pass increases fonts by 0.5 pt and gives Figure 6 C/D
an internal label gutter with display limits 0–124; its percentages and counts
remain unchanged. See `reproduced/figure_layout_polish_audit.md` for checks.

`SHA256SUMS.txt` covers current and archived PDFs relative to this directory.
`legacy/` keeps historical Figure 8 and hybrid versions for provenance; only
`fig07_multiobjective.pdf` is current.
