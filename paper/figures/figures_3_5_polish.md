# Figures 3-5 publication styling: completed work and missing source

Work branch: `codex/figures-3-5-publication-polish`, based on `9adb8f7f`.

Figures 3 and 5 are regenerated through their Python implementations, with
the selected PDF names preserved. PNG (450 dpi), vector PDF and SVG exports
remain in `reproduced/analysis_v2_magnetic/figures/`, with the existing
`manuscript_figure3_magnetic_domain_v2_preview` and
`manuscript_figure5_energy_magnetism_v2_preview` basenames.

## Reproduce from the repository root (PowerShell)

```powershell
$env:PYTHONPATH = "$PWD/src"
.venv/Scripts/python.exe -X utf8 scripts/illustrations/plot_paper_figures_3_5.py --publish
.venv/Scripts/python.exe -X utf8 scripts/analysis/audit_paper_figures_3_5.py
filter/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_manuscript_figure3_v2.py tests/test_manuscript_figure5_v2.py tests/test_validation_figures_v2.py -q --basetemp=reproduced/figures35_tests
```

The wrapper passes the existing local harmonized CrystalFormer FT and
CrystaLLM FT QC paths to Figure 3 and requires complete descriptor coverage.
It uses the previously calculated FT descriptor tables under
`reproduced/figure3_ft_descriptors/`. It performs no descriptor, CHGNet,
DXMag, reference-screening or DFT calculations. Without `--publish`, it
exports only into the established reproduction directory.

Existing individual Figure 3 and Figure 5 entrypoints remain available.
`manuscript_figure4_v2.py` generates legacy PCA, not manuscript Figure 4.

## Scientific audit against the starting commit

The baseline Figure 3 loader was loaded directly from `9adb8f7f` and run
with the same inputs as the changed implementation. Exact dataframe
equality passed for every aligned descriptor record and the complete
availability/prevalence audit. Consequently all 30 boxplot populations,
quartiles, medians and whiskers are identical; only their presentation
changes. No applicable empty population is represented by a fabricated box.

| Quantity | Before | After |
|---|---:|---:|
| Figure 3 QC-retained records | 12,281 | 12,281 |
| Panel A nonzero records | 7,295 | 7,295 |
| Panel B nonzero records | 2,101 | 2,101 |
| Panel C applicable records | 9,282 | 9,282 |
| Panel C genuine zeros | 3,365 | 3,365 |
| Figure 5 finite pairs | 12,277 | 12,277 |

Figure 5 uses exactly the existing ten-cohort publication source at
`paper/tables/figure_sources/fig05_energy_magnetism.csv`. Its content is
identical to the baseline after normalizing Git's LF/Windows CRLF line
endings. The baseline Git-blob SHA256 is
`3ff1901123ae47f35dc52eabbda41fec2ae948f96f20e501f6ec46dc8f5f2249`.
Three CrystalFormer Base rows and one CrystaLLM Base row lack finite pairs.
All remaining points are displayed without subsampling or quantile clipping.
The pooled hexbin sum, every B-F point, both group medians, arrow start/end
coordinates and common full-data limits are checked by regression tests.
The shared eight-cohort analysis and its standalone plotting functions are
unchanged; the manuscript Figure 5 now has its permanent ten-cohort builder.

## Presentation and visual QA

Final verification: 28 tests passed, scientific audit passed, and
`git diff --check` passed. Audit CSVs, box statistics and PDF rasterizations
are saved under `reproduced/figures35_audit/`.

Figure 3 uses one hue per generator, solid Base boxes/bars and diagonal
FT/Refined hatching, with separate external Generator and Version legends.
Its caption retains the prevalence denominators, conditional boxplots and
reason for the Crys-JEPA separator. Figure 5A uses pooled greyscale logarithmic
hexbin counts; B-F distinguish point versions and filled/open group-median
diamonds. Its legend is outside the panels. Both selected PDFs are rendered
and inspected for clipping, overlaps, hatch visibility and units; PDF text
bounds are checked programmatically. Main tick/legend text is 10 pt at export
width about 257 mm (about 7 pt when reproduced at 180 mm); mathematical
superscripts/subscripts are smaller. No specific journal dimensions or font
minimum were supplied; check the target journal before narrower reproduction.

Captions are in `figure3_caption.md` and `figure5_caption.md`. The manuscript
source is outside this repository, so duplicate paragraphs and Figure 5/6
cross-references in that external text could not be verified or edited.

## Figure 4 is pending: do not substitute the legacy figure

The selected `fig04_magnetic_reference_dft.pdf` is an imported collaborator
artifact. Its exact MP-only ten-cohort builder and complete plotting tables
are absent. `filter/paper/figures.py` has a related older eight-cohort
MAGNDATA-inclusive renderer, not this PDF's source. The available
`filter/paper/results/mp_generator_summary.csv` contains ten-cohort point
estimates, but lacks the plotted intervals, AFM/FM/FiM composition and the
DFT confirmation table. Reconstructing those values from this PDF or using
the older reference setup would not preserve the scientific source.

Figure 4 is therefore unchanged, including all DFT coverage and intervals.
To complete it, supply the collaborator's exact plotting script plus its
MP-only summary/uncertainty, magnetic-branch and DFT tables. The task is
incomplete until Figure 4 is regenerated and reviewed. Keep this work on its
branch; merging into local `main` is deferred. No remote push is performed.
