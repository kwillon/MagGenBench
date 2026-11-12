# Publication figures

Selected publication PDFs, captions, this map, checksums and `legacy/` belong here.
Captions are consolidated in [figure_captions.md](figure_captions.md).
Raster previews and technical audits live under `reproduced/`.

| Figure | Selected PDF | Reproduction code | Scientific inputs |
|---|---|---|---|
| 1 | [Pipeline](fig01_pipeline.pdf) | Supplied artwork; historical code in `scripts/illustrations/plot_paper_pipeline_v3.py` | [Source](../../reproduced/figure1/fig01_pipeline_source.png); [preview](../../reproduced/figure1/previews/fig01_pipeline.png) |
| 2 | [Structural QC](fig02_structural_overview.pdf) | `scripts/illustrations/plot_manuscript_figure2_v2.py` | Full `tables/02_validation/` and `tables/03_features/` QC records |
| 3 | [Magnetic domain](fig03_magnetic_domain.pdf) | `scripts/illustrations/plot_manuscript_figure3_v2.py` | Frozen `tables/10_analysis_v2_magnetic/` plus FT descriptors in `tables/figure_sources/` |
| 4 | [Reference screening / DFT](fig04_magnetic_reference_dft.pdf) | `scripts/analysis/build_figure4_supp_publication.py --figure4-only`; native `plot_figure4_publication.py` | Frozen selected-artwork statistics and DFT summary, guarded against supplied `Figure4_DFT.pdf`; see [provenance](../../docs/figures/figure4_supp_provenance.md) |
| 5 | [Energy–magnetism](fig05_energy_magnetism.pdf) | `scripts/illustrations/plot_manuscript_figure5_v2.py` | `tables/figure_sources/fig05_energy_magnetism.csv` |
| 6 | [Diversity / adaptation](fig06_diversity_adaptation.pdf) | `scripts/illustrations/plot_fig06_diversity_adaptation_palette_preview.py` | `tables/figure_sources/fig06_compound_classes.csv`, `fig06_diversity_summary.csv` |
| 7 | [Multiobjective trade-offs](fig07_multiobjective.pdf) | `scripts/analysis/build_paper_multiobjective_figure.py` | `tables/figure_sources/figure8/figure08_scenario_{metrics,rankings,pareto}_v2.csv` |
| Supplementary 1 | [Ten-set descriptor space](supp01_descriptor_space_ten_sets.pdf) | `scripts/illustrations/plot_paper_pca.py` | Frozen analysis and two FT descriptor CSVs |
| Supplementary 2 | [Descriptor space](supp02_descriptor_space.pdf) | `scripts/analysis/build_figure4_supp_publication.py` | Restored eight-set `legacy/descriptor_space_pca.pdf`, text-only Ebrima conversion |
| Supplementary 3 | [Reference-space validation](supp03_reference_space_validation.pdf) | `scripts/analysis/external/plot_figures_maggenbench.py` via the publication builder | Frozen MP-only four-class confusion counts, 8,000 references |
| Supplementary 4 | [Magnetic-branch agreement](supp04_magnetic_branch_agreement.pdf) | Same builder and external script | Frozen MP-only three-branch confusion counts, 6,000 magnetic references |

Verified standalone captions for Figures 1/6 were not recovered;
their captions require the external manuscript. S1-S4 captions follow the supplied
manuscript/support text and are consolidated in `figure_captions.md`.
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
the updated coauthor PDF's plotted values without recalculation. Its native
Matplotlib renderer adds Figure 3-style panel subtitles and exports PNG/PDF/SVG;
the frozen DFT summary and confidence intervals are reused unchanged.
The previous Figure 4 is preserved as
`legacy/fig04_magnetic_reference_dft_before_coauthor_update.pdf`.
The ten-set descriptor-space PDF is now S1; PCA loadings are archived as
`legacy/supp00_pca_loadings.pdf`. Restored S2 contains eight sets, including
three adaptation comparisons. These renames preserve the original PDF bytes.
The ten-set Figure 6 still uses the documented palette-preview entry point;
the historical eight-set implementation is retained.
The current typography pass increases fonts by 0.5 pt and gives Figure 6 C/D
an internal label gutter with display limits 0–124; its percentages and counts
remain unchanged. See `reproduced/figure_layout_polish_audit.md` for checks.

`SHA256SUMS.txt` covers current and archived PDFs relative to this directory.
`legacy/` keeps historical Figure 8 and hybrid versions for provenance; only
`fig07_multiobjective.pdf` is current.
