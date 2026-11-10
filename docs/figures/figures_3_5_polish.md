# Figures 3 and 5: landscape layout and historical scatter restoration

Revision branch: `codex/figures-3-5-layout-restore`, following `6df9c7c8`.
Scientific baseline: `9adb8f7f`; historical ten-cohort Figure 5 PDF introduced
by `d66be85c`. These commits contain the selected PDF but do not contain its
matching ten-cohort Python implementation: the old Python builder has only
eight cohorts and three adaptation panels. The current permanent ten-cohort
builder therefore restores the historical presentation using the unchanged
publication source CSV, rather than reinstating the incompatible old code.

## Reproduce from the repository root (PowerShell)

```powershell
$env:PYTHONPATH = "$PWD/src"
.venv/Scripts/python.exe -X utf8 scripts/illustrations/plot_paper_figures_3_5.py --publish
.venv/Scripts/python.exe -X utf8 scripts/analysis/audit_paper_figures_3_5.py
filter/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_manuscript_figure3_v2.py tests/test_manuscript_figure5_v2.py tests/test_validation_figures_v2.py tests/test_analysis_v2_plotting.py -q --basetemp=reproduced/figures35_tests
```

The wrapper passes the existing local harmonized CrystalFormer FT and
CrystaLLM FT QC paths to Figure 3 and requires complete descriptor coverage.
It reads the previously computed FT descriptor tables from
`reproduced/figure3_ft_descriptors/`. No descriptors, CHGNet, DXMag, screening,
DFT, predictions or datasets are recalculated. Without `--publish`, only the
established reproduction directory is written.

PNG (450 dpi), PDF and SVG are exported to
`reproduced/analysis_v2_magnetic/figures/`, keeping the existing
`manuscript_figure3_magnetic_domain_v2_preview` and
`manuscript_figure5_energy_magnetism_v2_preview` basenames. Only the two selected
PDFs are copied into `paper/figures/`.

## Figure 3

The canvas is 16 x 9 inches. A and B occupy the top scientific row, with C
across the full lower row; a separate row contains Generator and Version
legends. The approved generator colors and Base/FT/Refined fill/hatch encoding
are retained. Fonts and sample labels are preserved. Both the explicit tight
bounding box and the global `savefig.bbox` setting are disabled for this
figure's exports. Its PDF MediaBox must be exactly 1152 x 648 pt (16:9);
the raster export must be 7200 x 4050 pixels at 450 dpi. Other figures retain
their existing export behavior.

## Figure 5

The historical 16 x 13 inch layout is restored: A spans the top, B-D occupy
the middle row, and E-F the bottom row. A is a multicolor scatter plot with
the five-generator legend inside its upper edge. The historical palette is
MatterGen `#527DA3`, Con-CDVAE `#47A8A0`, CrystalFormer `#C47B50`,
CrystaLLM `#9A5F69`, Crys-JEPA `#7772A5`. Circles denote Base and triangles
denote FT/Refined. Open Base median diamonds and filled adapted median
diamonds, with black arrows from Base to adapted group medians, restore the
historical encoding. This palette is intentionally independent of Figure 3.

The historical common display window uses the pooled 0.5th/99.5th percentiles
plus 6% padding in energy and 8% in moment. This restores the old view while
retaining every finite input point and the full-population medians. Points
outside that window are clipped only by the axes. The audit prints their
count and cohort distribution; the caption explicitly describes the window.
There are 61 such pairs, matching the restored historical view limits.
There is no density colorbar or claim about logarithmic bin counts.

## Scientific and visual verification

The audit compares every Figure 3 aligned descriptor record and the complete
prevalence/availability audit to the original loader from `9adb8f7f`, using
exact dataframe equality. All 30 boxplot populations and their quartiles,
medians and whiskers are unchanged. Figure 5's source CSV is identical to
the baseline after normalizing LF/CRLF line endings; the baseline Git-blob
SHA256 is `3ff1901123ae47f35dc52eabbda41fec2ae948f96f20e501f6ec46dc8f5f2249`.

| Quantity | Baseline | Current |
|---|---:|---:|
| Figure 3 QC-retained records | 12,281 | 12,281 |
| Panel A nonzero records | 7,295 | 7,295 |
| Panel B nonzero records | 2,101 | 2,101 |
| Panel C applicable records | 9,282 | 9,282 |
| Panel C genuine zeros | 3,365 | 3,365 |
| Figure 5 finite pairs | 12,277 | 12,277 |

Three CrystalFormer Base rows and one CrystaLLM Base row lack finite pairs.
Tests check every scatter coordinate in A and B-F, all ten medians, arrow
start/end points, the restored panel arrangement, palette, legend and common
view limits. Layout tests check labels remain on the canvas and cohort ticks
do not overlap. The shared exporter's existing tests remain in the check set.
PDF rasterizations, detailed numerical CSVs and box statistics are under
`reproduced/figures35_audit/`. The PDFs are rendered and visually inspected
for readable fonts, visible hatches, panel labels and legends. Captions are
in `paper/figures/figure_captions.md` (Figure 3) and `paper/figures/figure_captions.md` (Figure 5); manuscript sources remain
outside this checkout.

Final verification: 32 tests passed; the numerical audit and
`git diff --check` passed. Figure 3 is exactly 1152 x 648 pt and its PNG is
7200 x 4050 pixels. Figure 5's PDF dimensions match the historical artifact
(1160.4 x 944.4 pt), and its ten open/filled median-diamond colors match the
historical PDF's vector artists. Minimum PDF text size is 10 pt in both.

## Figure 4 and integration scope

`fig04_magnetic_reference_dft.pdf` remains byte-identical to `9adb8f7f`; its
SHA256 is verified by the audit. The collaborator's missing source is outside
this revision's scope. Neither the legacy PCA builder nor the related filter
renderer is used as a substitute. Figure 4 does not block integration of the
completed Figures 3 and 5 into local `main`. No remote push is performed.
