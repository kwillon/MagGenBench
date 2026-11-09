# Publication typography and Figure 6 label spacing

Date: 2026-11-10. All eight canonical PDFs were rebuilt and visually reviewed:
`fig02_structural_overview.pdf`, `fig03_magnetic_domain.pdf`,
`fig04_magnetic_reference_dft.pdf`, `fig05_energy_magnetism.pdf`,
`fig06_diversity_adaptation.pdf`, `fig08_multiobjective.pdf`,
`supp01_pca_loadings.pdf`, `supp02_descriptor_space.pdf`.
Their canonical directory is `paper/figures/`; previews are under the corresponding
`reproduced/figure*/previews/` and supplementary directories. Figure 1 was excluded
from all edits; its SHA-256 remains
`e66d6a2c15b83c3605d08b5cfaff1094c9b81a72f81f445e1fb7fc63c1349e44`.

## Font sizes (PDF points)

Ebrima Regular remains embedded, weight 400. Every previously established size
increased by 0.5 pt; the roles below include existing figure-specific variants.

| Text role | Before | After |
|---|---:|---:|
| Main title | 16 | 16.5 |
| Panel titles and letters | 14 | 14.5 |
| Secondary headings | 12 | 12.5 |
| Axis labels | 11 | 11.5 |
| Larger ticks / legends / annotations | 10 | 10.5 |
| Figure 4 compact text | 9.5 | 10 |
| Standard ticks / legends / annotations | 9 | 9.5 |
| Dense Figure 6 value labels | 8.3 | 8.8 |

The Figure 2 Crys-JEPA Refined tick label uses two lines to retain clearance.
No new text overlaps or page clipping were found in the eight rendered previews.

## Figure 6 C/D

Both horizontal bar panels now use a 4 pt offset from each bar end and display
limits **0–124**, replacing **0–115** (original limit recovered from vector geometry).
Ticks remain 0, 20, 40, 60, 80 and 100; the extra range is display space only.
The measured minimum distances from value-label ends to the right frame are
**9.44 pt (C)** and **8.16 pt (D)**, exceeding the 7 pt clearance guard.
The shared native plotting helper measures rendered text and extends the display
range further if a narrower export needs additional room.

The 20 bars were reconstructed from
`tables/figure_sources/fig06_diversity_summary.csv`. Saved values were checked
against original vector widths before changing their display scale. Model order,
percentages, numerator/denominator counts, bar colors, alpha and edges were
retained. A/B render identically before and after C/D reconstruction within the
font-enlarged candidate. Obsolete C/D text was removed from the composition so
the final PDF contains no hidden duplicate labels.

## Implementation files

- `src/mvpipeline/analysis/typography.py`: common +0.5 pt font hierarchy and
  final rendered-label clearance check.
- `src/mvpipeline/analysis/figure6_layout.py`: reusable bar annotations and
  saved-data reconstruction of C/D, with numerical/color/order guards.
- `src/mvpipeline/analysis/diversity_figures_v2.py`: native plotting uses the
  shared annotation helper and minimum display range.
- `scripts/illustrations/merge_fig06_updated_pdf.py`: composed Figure 6 uses
  the same C/D layout implementation.
- `scripts/illustrations/restyle_publication_typography.py`: reproducible
  eight-PDF build, with Figure 6 layout audit.
- `scripts/analysis/verify_figure_typography.py`: final page bounds, fonts,
  overlap screening and guarded canonical promotion.
- `tests/test_figure6_layout.py`: long-label clearance at two export widths,
  including unchanged values, colors and label strings.
- `docs/figures/README.md`, `paper/figures/README.md` and
  `paper/figures/SHA256SUMS.txt`: reproduction notes and current checksums.

Existing Ebrima hooks in the Figure 2/3/5/6/8 and supplementary exporters inherit
the new hierarchy. No data files, model predictions or statistical computations
were changed. The scientific Figure 8 remains the approved hybrid v2.

## Verification evidence

Candidate PDFs, previews, font reports, numerical checks, per-panel clearance
and color lists: `reproduced/figure_layout_polish/check_v2/` (`audit.json`,
`verification.json`). Current-before snapshots are in
`reproduced/figure_layout_polish/before/`. The reproducible build uses the pinned
pre-typography canonical PDF snapshots so vector scientific content remains
identical for the seven figures without an intentional axis-layout adjustment.
All eight final PDFs pass numerical-token preservation, embedded Ebrima Regular,
page-boundary and text-overlap checks. Figure 6 additionally passes saved-data,
bar-order/color and unchanged A/B raster checks.

The focused figure regression suite passed: **50 tests**, including the two new
label-clearance cases, typography embedding, publication artifact checks,
diversity and Figure 2/3/5 plotting checks (45.90 s). `git diff --check` passed.
After canonical promotion, the four publication artifact/checksum tests passed
again (4.37 s). Final PDF verification reported zero text-overlap candidates.
Initially three additional PCA computation tests could not execute because
`scikit-learn` was absent. This limitation was resolved before integration:
`uv pip install --python .venv/Scripts/python.exe scikit-learn` installed
scikit-learn 1.9.1 and SciPy 1.18.1 in the ignored local environment.
The complete focused suite, including all three previously blocked PCA tests,
then passed: **55 tests in 54.80 s**. No publication PCA data was refitted.

## Integration verification

The working branch is `style/unify-publication-typography`. `git fetch origin`
confirmed local `main`, `origin/main` and the branch baseline all pointed to
`51241b340b3ae95751d193b5c4bead0f71532746` before committing these changes.
The final eight-PDF verification passed again with zero overlap candidates.
Figure 1 and the frozen scientific source tables have no Git diff.
Only selected audit notes, JSON evidence and text-correction tables are included;
temporary PDFs, test output directories, system font files and `.venv` are excluded.
The earlier `reproduced/figure_typography_audit.md` documents the initial Ebrima
revision; its font sizes/checksums are superseded by this layout pass and the
canonical `paper/figures/SHA256SUMS.txt`.
