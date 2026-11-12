# Figure 4 and supplementary figures: current sources

## Current Figure 4 panel-title renderer

Figure 4 is now generated natively by Matplotlib in
`scripts/analysis/plot_figure4_publication.py` (`combined_figure`, `add_letter`).
The publication builder dispatches to it; the historical
`filter/scripts/plot_mp_only_publication.py` is not the selected renderer and
its older DFT join is not used. Reproduce Figure 4 alone with:

```powershell
.venv/Scripts/python.exe scripts/analysis/build_figure4_supp_publication.py --figure4-only --output reproduced/figure4_panel_titles/build
```

The output bundle contains `fig04_magnetic_reference_dft.{png,pdf,svg}`, a PDF
render for visual review, and `figure4_panel_titles_verification.json`.
The four panel titles contain only A, B, C, and D, with no subtitles.
Each is a single Matplotlib left title with Ebrima Regular,
14.5 pt, regular weight and 10 pt padding, matching the final Figure 3 hierarchy.
There are no separate letter artists. C's AFM/FM/FiM legend has its own row
above the title; a rendered-bounds assertion checks that they do not overlap.
Formula-cluster bootstrap remains described in the caption only.

This native renderer supersedes the initial text-stream conversion for
**Figure 4 only** described below. It retains the supplied PDF's panel frames,
model order, family/branch colors and display scales (A 0-1.025, B -6-6.4,
C -0.6-9.6 and 0-1.03, D 0-1.035). Scientific values come from the frozen
`figure_statistics.csv`, with the selected-artwork values from
`selected_artwork_statistics_readback.csv` applied before plotting. The latter
is an unchanged copy of the existing audited
`reproduced/figure4/publication_audit/original_pdf_vs_reproduced.csv` and preserves
the documented original bootstrap bounds and CrystalFormer FT quantiles.
Each build independently checks A/C fractions, all five B quantiles, and both
endpoints of A/D confidence intervals against the supplied source vectors
(absolute tolerance at most 0.000005, accounting for PDF coordinate precision).

Panel D reads `tables/figure_sources/figure4/Figure4D_summary.csv`, copied
unchanged from the previously checked `reproduced/figure4_supp_update/build/`
summary. The title-only build never reads raw moments, recalculates a DFT
criterion, or recomputes Wilson intervals. All plotted elements and text are
native vector artists; PDF fonts are checked for embedded Ebrima Regular,
weight 400. Supplementary files are untouched by `--figure4-only`.

## Initial coauthor update and supplementary provenance

Figure 4, S3 and S4 are based on the supplied external coauthor script,
`scripts/analysis/external/plot_figures_maggenbench.py`, retained byte-for-byte.
The supplied updated DFT data are retained byte-for-byte at
`tables/figure_sources/DFT_figure4D_updated.csv` (324 unique structures).
The supplied Figure 4 artwork is retained at
`tables/figure_sources/figure4/Figure4_DFT.pdf` (SHA256
`acaa9aa6713d9bba4fe265f8c0a57a3cccd92516f8498e8cd174892ebe9255a4`).

| Manuscript figure | Selected file in `paper/figures/` | Source |
|---|---|---|
| 4 | `fig04_magnetic_reference_dft.pdf` | Native Matplotlib renderer above, guarded against supplied updated PDF values |
| S1 | `supp01_descriptor_space_ten_sets.pdf` | Existing ten-set descriptor-space organization and cohort-centroid shifts; unchanged bytes |
| S2 | `supp02_descriptor_space.pdf` | `legacy/descriptor_space_pca.pdf`; eight generated sets and three adaptation comparisons |
| S3 | `supp03_reference_space_validation.pdf` | External script and frozen four-class counts |
| S4 | `supp04_magnetic_branch_agreement.pdf` | External script and frozen three-magnetic-branch counts |

The prior ten-set S2 is preserved as the current S1,
`paper/figures/supp01_descriptor_space_ten_sets.pdf`. PCA loadings are preserved
at `paper/figures/legacy/supp00_pca_loadings.pdf`. The ten-set projection is an alternative
scientific analysis, not a typography revision of the selected eight-set S2.
S1 and S2 therefore describe their respective original populations; no PCA
was refitted to make these populations identical.
The previous selected Figure 4 is preserved as
`paper/figures/legacy/fig04_magnetic_reference_dft_before_coauthor_update.pdf`.
All earlier legacy PDFs remain intact.

## Scientific inputs

The three auxiliary CSVs expected by the coauthor script were not supplied.
`figure_statistics.csv` was recovered from the frozen historical
`reproduced/figure4/publication_audit/figure_statistics.csv` and is retained under
`tables/figure_sources/figure4/` for the coauthor input bundle. The selected
Figure 4 was initially taken directly from the supplied updated PDF. The current
native renderer above preserves that artwork's audited values rather than
substituting the numerically different recalculation table.

`reference_confusion_counts.csv` and `branch_confusion_counts.csv` in the same
directory were recovered using leave-one-out scoring of the frozen MP-only
arrays in `filter/src/cifmagfilter/data/model/reference_filter.npz` with
`cifmagfilter.reference.score_reference_training`, k=15. There is no refit,
descriptor extraction, model training or new DFT calculation. The old five-class
MP+MAGNDATA results in `filter/paper/results/reference_validation_scores.csv`
are not used. These recovered counts reproduce all supplied script assertions:

- S3: 8,000 structures; four-class agreement 0.762875, magnetic sensitivity
  0.9446666666666667, NM specificity 0.9145, binary balanced accuracy
  0.9295833333333333.
- S4: 6,000 magnetic structures; three-class agreement 0.7518333333333334,
  displayed as 75.18%.
- Updated DFT: absolute maximum local moment >0.5 mu_B; 202/324 magnetic,
  231 magnetic-reference candidates, and 186/231 confirmed. By generator:
  MatterGen 52/55, Con-CDVAE 57/73, CrystalFormer 27/45, CrystALLM 50/58.
  Confidence intervals use the coauthor's Wilson implementation.

The Figure 4 caption changes only where required by the new DFT values and
artwork (median ticks, no hatching/diamonds). S1's caption follows the current
ten-set descriptor-space selection; S2-S4 retain the provided manuscript/support
wording. Reference consistency is not independent validation;
the historical DFT cohort was selected using the previous reference model.

## Reproduction and typography

From the repository root, with project PDF/plot dependencies installed:

```powershell
.venv/Scripts/python.exe scripts/analysis/build_figure4_supp_publication.py --output reproduced/figure4_supp_update/recheck --verify-reference-counts
```

Use a fresh output directory. This creates candidates, PNG previews, the DFT
summary and `verification.json`; it does not overwrite publication PDFs.
The optional verification flag needs scikit-learn and independently checks the
frozen confusion counts against the bundled MP-only reference arrays.
Without the flag, only the saved counts are read.

The builder wraps the unchanged external script for S3/S4. Ebrima Regular is
resolved by the existing shared font helper (Windows `ebrima.ttf` or
`MAGGENBENCH_EBRIMA_FONT`); missing Ebrima is an error. Every text artist,
including matrix diagonals, uses regular weight 400. Panel letters are 14.5 pt,
matching the shared publication hierarchy. S4 is a single panel without a letter,
as in the supplied script; S1's existing titles remain unchanged.

Restored S2 uses the shared PDF text-stream replacement, with
identity wording and preserved source text sizes except panel letters.
Mathematical subscripts retain their original sizes and baselines. No white
overlay, rasterization, masking, or scientific graphical editing is used.
For S2 the builder proves identical drawing signatures, image content and page boxes,
unchanged numeric tokens, embedded regular fonts and text inside page bounds.
Scientific content is unchanged **during typography conversion**; the supplied
DFT update and selected S2 version are explicit scientific-source replacements.
Rendered previews of all five PDFs were visually reviewed.

Final verification: `scripts/analysis/verify_figure4_supp_update.py` opens the
selected PDFs, verifies fonts/labels/bounds, compares S2 scientific PDF layers and
exact non-whitespace character multisets with its source artwork, verifies the
archives against the pinned pre-update Git version, checks unrelated figures/SI, and
updates the PDF checksums. Its report and final previews are under
`reproduced/figure4_supp_update/final/`. The existing
`tests/test_publication_typography.py` suite passed all six tests.
`git diff --check` passed. The pre-existing working-tree edit in
`paper/supporting_information/table_s7_pairwise_overlap.csv` was preserved.

`paper/figures/SHA256SUMS.txt` covers all selected and legacy PDFs. Figures
1, 2, 3, 5, 6 and 7 (formerly 8), along with SI tables, are outside this update.
