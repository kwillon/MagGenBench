# Figure typography audit

Date: 2026-11-10. Branch: `style/unify-publication-typography`.

Historical audit of the initial Ebrima revision. Subsequent font enlargement,
Figure 6 spacing, final checksums and completed PCA tests are documented in
`reproduced/figure_layout_polish_audit.md`; that report supersedes the sizes and
output hashes below.

## Scope and Figure 1 reference

Eight canonical PDFs were updated: Figures 2, 3, 4, 5, 6, 8, Supplementary 1
and Supplementary 2. No additional current publication figure was found.
Figure 1 was read only, never replaced or archived. It contains embedded Ebrima
(100 text spans) on a 1939.72 × 950 pt page, with sizes 15–24 pt. As a wide
workflow diagram, its absolute sizes are not copied blindly into denser charts;
the same regular family is used with a chart-appropriate hierarchy.

Ebrima Regular is loaded from `C:/Windows/Fonts/ebrima.ttf`, registered with
Matplotlib font_manager, and resolved with fallback_to_default=False. Its
OS/2 weight is 400. No system font file was copied into the repository. A
missing font causes a clear error; MAGGENBENCH_EBRIMA_FONT permits an explicit
local path. There is no Arial/DejaVu fallback or synthetic bold.

## Fonts and sizes

| PDF | Before | After | Actual sizes (pt) |
|---|---|---|---|
| fig02_structural_overview.pdf | DejaVuSans, DejaVuSans-Bold | Ebrima Regular, embedded, weight 400 | 9, 11, 12, 14 |
| fig03_magnetic_domain.pdf | DejaVuSans, DejaVuSans-Bold | Ebrima Regular, embedded, weight 400 | 10, 11, 14 |
| fig04_magnetic_reference_dft.pdf | DejaVu Sans Bold, DejaVu Sans Book | Ebrima Regular, embedded, weight 400 | 9.5, 10, 11, 14 |
| fig05_energy_magnetism.pdf | DejaVuSans, DejaVuSans-Bold | Ebrima Regular, embedded, weight 400 | 9, 11, 14 |
| fig06_diversity_adaptation.pdf | DejaVuSans, DejaVuSans-Bold | Ebrima Regular, embedded, weight 400 | 8.3, 9, 11, 14 |
| fig08_multiobjective.pdf | DejaVuSans, DejaVuSans-Bold | Ebrima Regular, embedded, weight 400 | 9, 10, 11, 14 |
| supp01_pca_loadings.pdf | DejaVuSans | Ebrima Regular, embedded, weight 400 | 9, 11, 14 |
| supp02_descriptor_space.pdf | DejaVuSans | Ebrima Regular, embedded, weight 400 | 9, 11, 12, 14, 16 |

Hierarchy: panel letters and main panel headings 14 pt; axis and colorbar titles
11 pt; ticks normally 9 pt (Figure 8 uses 10 pt for its dense matrix/numeric
elements); legends 9–10 pt; dense Figure 6 numeric annotations 8.3 pt; smaller
Figure 2 headings and supplementary cohort headings 12 pt; supplementary overall
heading 16 pt. Figure 4's small legend uses 9.5 pt. All sizes are native PDF
points. Exact per-label old/new sizes are recorded in final_hierarchy/audit.json.

## Actual text corrections

The following table lists every distinct actual string replacement (including
numeric-minus typography), grouped by figure and occurrence count. Scientific
hyphens in Fine-tuned, 3d-containing, Pareto-efficient, transition-metal,
magnetic-like and configured terminology were preserved. Raw descriptor identifiers
in PCA coefficient labels were retained to preserve the exact mapping to features.

| Figure | Original text | Corrected text | Count |
|---|---|---|---:|
| fig02_structural_overview.pdf | Crys-JEPA Ref. | Crys-JEPA Refined | 1 |
| fig03_magnetic_domain.pdf | C   Local magnetic-neighbor environment (applicable records) | C   Local magnetic neighbor environment (applicable records) | 1 |
| fig03_magnetic_domain.pdf | Crys-JEPA Ref. | Crys-JEPA Refined | 3 |
| fig03_magnetic_domain.pdf | Magnetic-neighbor fraction | Magnetic neighbor fraction | 1 |
| fig04_magnetic_reference_dft.pdf | -2 | −2 | 1 |
| fig04_magnetic_reference_dft.pdf | -4 | −4 | 1 |
| fig04_magnetic_reference_dft.pdf | Contrast: d(NM) - d(magnetic) | Contrast: d(NM) − d(magnetic) | 1 |
| fig06_diversity_adaptation.pdf | -0.2 | −0.2 | 1 |
| fig06_diversity_adaptation.pdf | -1.5 | −1.5 | 1 |
| fig06_diversity_adaptation.pdf | -1.8 | −1.8 | 1 |
| fig06_diversity_adaptation.pdf | -1.9 | −1.9 | 1 |
| fig06_diversity_adaptation.pdf | -11.2 | −11.2 | 1 |
| fig06_diversity_adaptation.pdf | -11.8 | −11.8 | 1 |
| fig06_diversity_adaptation.pdf | -12.7 | −12.7 | 1 |
| fig06_diversity_adaptation.pdf | -12.8 | −12.8 | 1 |
| fig06_diversity_adaptation.pdf | -13.5 | −13.5 | 1 |
| fig06_diversity_adaptation.pdf | -14.0 | −14.0 | 1 |
| fig06_diversity_adaptation.pdf | -14.8 | −14.8 | 1 |
| fig06_diversity_adaptation.pdf | -16.3 | −16.3 | 1 |
| fig06_diversity_adaptation.pdf | -21.0 | −21.0 | 1 |
| fig06_diversity_adaptation.pdf | -3.1 | −3.1 | 2 |
| fig06_diversity_adaptation.pdf | -4.2 | −4.2 | 1 |
| fig06_diversity_adaptation.pdf | -4.6 | −4.6 | 1 |
| fig06_diversity_adaptation.pdf | -4.7 | −4.7 | 1 |
| fig06_diversity_adaptation.pdf | -4.9 | −4.9 | 2 |
| fig06_diversity_adaptation.pdf | -45.9 | −45.9 | 1 |
| fig06_diversity_adaptation.pdf | -6.4 | −6.4 | 1 |
| fig06_diversity_adaptation.pdf | -6.7 | −6.7 | 1 |
| fig06_diversity_adaptation.pdf | -7.5 | −7.5 | 1 |
| fig06_diversity_adaptation.pdf | -9.5 | −9.5 | 1 |
| fig06_diversity_adaptation.pdf | -9.8 | −9.8 | 2 |
| fig06_diversity_adaptation.pdf | Adaptation-associated changes | Changes associated with adaptation | 1 |
| fig06_diversity_adaptation.pdf | Compound-class distribution | Compound class distribution | 1 |
| fig06_diversity_adaptation.pdf | Con-CDVAE Fine-tuned | Con-CDVAE FT | 1 |
| fig06_diversity_adaptation.pdf | Crys-JEPA Ref. | Crys-JEPA Refined | 2 |
| fig06_diversity_adaptation.pdf | CrystalFormer Fine-tuned | CrystalFormer FT | 1 |
| fig06_diversity_adaptation.pdf | D  Unique formula–space-group pairs | D  Unique formula–space group pairs | 1 |
| fig06_diversity_adaptation.pdf | MatterGen Fine-tuned | MatterGen FT | 1 |
| fig08_multiobjective.pdf | 3d atomic- | 3d atomic-content | 1 |
| fig08_multiobjective.pdf | Lanthanide atomic- | Lanthanide | 1 |
| fig08_multiobjective.pdf | Min-max normalized score | Min–max normalized score | 1 |
| fig08_multiobjective.pdf | content yield | atomic-content yield | 1 |
| fig08_multiobjective.pdf | content yield | yield | 1 |
| supp01_pca_loadings.pdf | Magnetic-sublattice geometry: PC1 | Magnetic sublattice geometry: PC1 | 1 |
| supp01_pca_loadings.pdf | Magnetic-sublattice geometry: PC2 | Magnetic sublattice geometry: PC2 | 1 |
| supp02_descriptor_space.pdf | Descriptor-space PCA and cohort-centroid shifts | Descriptor space PCA and cohort centroid shifts | 1 |
| supp02_descriptor_space.pdf | Magnetic-sublattice geometry | Magnetic sublattice geometry | 1 |

The Figure 8 two-line labels now read `3d atomic-content / yield` and
`Lanthanide / atomic-content yield`, rather than breaking after `atomic-`.
Figure 6D's original split text/vector en-dash was composed into one regular
Ebrima label, `D  Unique formula–space group pairs`. Negative tick values are
unchanged: Type-3 vector minus glyphs were replaced with the Ebrima mathematical
minus and associated with their original numbers. Hidden clipped font glyphs
inside the composite Figure 6 Form were not interpreted as data.

Ebrima shares font glyphs for SPACE/NBSP and HYPHEN/SOFT HYPHEN. The common
Unicode-map correction ensures that copied PDF text retains ordinary spaces
and visible hyphens, avoiding accidental soft hyphens. This also fixed a
Figure 4 source-export regression detected by its existing integration test.

## Scientific preservation evidence

The canonical figures were not rebuilt by recalculating scientific algorithms.
A shared scripted text-layer rebuild starts from the audited canonical vector
snapshots (Git revision 51241b340b3ae95751d193b5c4bead0f71532746). It removes
only PDF text operators and explicitly named font-glyph XObjects, then inserts
Ebrima text. Every non-typographic vector path, its coordinates, colors and
line styles, every rasterized scatter/heatmap image and placement, and every
page box was compared exactly. Font glyph outlines are typography, not
statistical vectors; this distinction is explicitly handled for legacy minus
and en-dash XObjects. All visible numerical token multisets, with recovered
negative signs, agree before and after. All eight checks passed.

This preserves QC counts, chemical metrics, normalization, Pareto criteria,
S1–S3 results, model order, scatter samples, medians, intervals, PCA coordinates
and loadings. No training, structure generation, CHGNet or DXMag inference, or
PCA refitting was performed. No scientific table/configuration was edited.
Figure 8 remains the approved hybrid_v2 design, including its Art Nouveau
palette and S1 Top-5 D panel; it was never replaced by the old presence analysis.

## Source implementation and reproducibility

`src/mvpipeline/analysis/typography.py` is the single family/weight, hierarchy,
text-correction and PDF text-rebuild implementation. Native Matplotlib exports
use the same registered family, explicit regular FontProperties and corrected
labels. The shared save hook is explicitly limited to manuscript Figures
2/3/5/6 and does not affect Figure 1. Figure 8, the Figure 6 palette/merge
entry points, PCA exports and the original-vector Figure 4 exporter call the
same typography module. Scientific algorithms and table paths are unchanged.

The verified publication update can be reconstructed into a fresh directory:

```powershell
.venv/Scripts/python.exe scripts/illustrations/restyle_publication_typography.py --source-from-git --output-dir reproduced/figure_typography/recheck
```

The pinned source read skips Figure 1 entirely. An independent native Figure 8
export also passed from relocated `tables/figure_sources/figure8/` inputs under
`reproduced/figure_typography/generator_check/figure8/`.

## Font and visual QA

PyMuPDF confirms Ebrima Regular is the only used font; fontTools confirms every
embedded face has weight 400. `pdffonts` independently reports CID TrueType,
embedded=yes, subset=yes and Unicode=yes in all eight final PDFs. Per-PDF logs
are retained in final_hierarchy/*_pdffonts.txt.

Before/after raster renders for all eight figures were inspected. Font ascender
differences were corrected with small text-only offsets inside unchanged page
boxes. There are no text spans outside page bounds and no nonblank text-overlap
candidates in the final texttrace scan. Figures 2/3 labels, Figure 4 minuses,
Figure 5 units, Figure 6D, Figure 8A/D, and supplementary negative PCA ticks were
checked explicitly. Palettes and panel layouts are unchanged. PNG previews
are under reproduced/figure2, figure3, figure4, figure5, figure6, figure8 and
supplementary/figure1, supplementary/figure2, each in previews/; none were added
to paper/figures/.

## Tests and final checks

The first run passed 43 tests and exposed the Figure 4 Unicode-map issue.
After fixing the shared map, its six-test focused rerun passed. The final
publication-contract run is recorded separately below. `git diff --check`
passes. The legacy byte-equality test for Figure 8 was replaced by stricter
scientific-vector/image/numeric checks plus the Ebrima embedding check, because
changing typography necessarily changes PDF bytes.

Final complete run: **48 passed in 47.31 seconds**, covering publication typography,
publication artifacts/checksums, manuscript Figures 2/3/5/6 and Figure 4 vector
preservation. Native Figure 8 source export also passed. PDF paths are explicitly
marked binary in .gitattributes so Git cannot normalize embedded font/PDF streams.

The reference Figure 1 contains some punctuation conventions such as
`Fine–tuned`; these were recorded but not copied blindly or corrected in the
protected reference. Its font family is the reference; its file is unchanged.

No merge, push or automatic main integration was performed. All work remains
on style/unify-publication-typography for review. No scientific labeling error
was silently corrected; changes are limited to typography and equivalent wording.

## Final PDF checksums

| PDF | SHA256 |
|---|---|
| fig01_pipeline.pdf | e66d6a2c15b83c3605d08b5cfaff1094c9b81a72f81f445e1fb7fc63c1349e44 |
| fig02_structural_overview.pdf | 9b0441c6ba6564f839919b9d8d900ca9ac7401046c054d2205ee7b7bdce4c171 |
| fig03_magnetic_domain.pdf | d7698c017daefe9b3e87f71a652143d9be3386b8aef15150de7b498d49a4efae |
| fig04_magnetic_reference_dft.pdf | 6404cfdd1bde128aa150214efc3f8c2ef07ea50553948fcf830e32265662e3cb |
| fig05_energy_magnetism.pdf | c4c1b43b4e52cbbb967d06a8211a76e82951e8de395c4d0cf29598a7cb02863c |
| fig06_diversity_adaptation.pdf | 35c6d2c4f872cb0e63aa7b9f15d2ff560e7d0aa5abe560a64dcca0818b06806f |
| fig08_multiobjective.pdf | 84d893f0b4c573a5c26e172d69c38c19695d39876c03111373382cb23ea0c389 |
| supp01_pca_loadings.pdf | e2a5d3d2ade7038ddb52c05bccbe545300f5f5937b1d802443cf7790591347c0 |
| supp02_descriptor_space.pdf | 07e55d22063efcb5c63132d3bf6b5a25b2dfc1c776cd31ce6e1e69655bc8f13b |

Figure 1 SHA256 is unchanged: `e66d6a2c15b83c3605d08b5cfaff1094c9b81a72f81f445e1fb7fc63c1349e44`.

## Changed files for review

```text
 M .gitattributes
 M docs/figures/README.md
 M paper/figures/README.md
 M paper/figures/SHA256SUMS.txt
 M paper/figures/fig02_structural_overview.pdf
 M paper/figures/fig03_magnetic_domain.pdf
 M paper/figures/fig04_magnetic_reference_dft.pdf
 M paper/figures/fig05_energy_magnetism.pdf
 M paper/figures/fig06_diversity_adaptation.pdf
 M paper/figures/fig08_multiobjective.pdf
 M paper/figures/supp01_pca_loadings.pdf
 M paper/figures/supp02_descriptor_space.pdf
 M reproduced/figure8/previews/fig08_multiobjective.png
 M scripts/analysis/build_paper_figure08_hybrid.py
 M scripts/illustrations/merge_fig06_updated_pdf.py
 M scripts/illustrations/plot_fig06_diversity_adaptation_palette_preview.py
 M scripts/illustrations/plot_paper_pca.py
 M scripts/illustrations/restyle_figure4_original_vectors.py
 M src/mvpipeline/analysis/manuscript_figure5_v2.py
 M src/mvpipeline/analysis/plotting_v2.py
 M src/mvpipeline/analysis/publication_style.py
 M tests/test_publication_artifacts.py
?? scripts/analysis/audit_figure_typography.py
?? scripts/analysis/verify_figure_typography.py
?? scripts/illustrations/restyle_publication_typography.py
?? src/mvpipeline/analysis/typography.py
?? tests/test_publication_typography.py
```

Additional requested local outputs: reproduced/figure_typography_audit.md and reproduced/figure_typography/text_corrections.csv. All previews/audit JSON/pdffonts logs are under reproduced and no font TTF/OTF was added. Final focused run after the shared term-map addition: 9 passed in 7.41 seconds.
