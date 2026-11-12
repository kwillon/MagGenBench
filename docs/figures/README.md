# Figure reproduction

Run from the repository root with the project installed, or set `PYTHONPATH=src`.
No model training or new structure generation is needed for publication plots.

- [Figure 2](figure2_reproduction.md): full harmonized QC populations.
- [Figure 3](figure3_reproduction.md): ten-set descriptors and frozen inputs.
- [Figure 4 and S1-S4](figure4_supp_provenance.md): updated coauthor artwork, DFT inputs, supplementary order and reproduction.
- [Historical Figure 4](figure4_reproduction.md): previous statistical vectors and recalculation limitations.
- [Figures 3/5 styling history](figures_3_5_polish.md).
- Figure 5: `python scripts/illustrations/plot_manuscript_figure5_v2.py --help`.
- Figure 6: `python scripts/illustrations/plot_fig06_diversity_adaptation_palette_preview.py`.
- PCA: `python scripts/illustrations/plot_paper_pca.py` exports ten-set alternatives;
  the selected S2 is restored from the eight-set artwork (see current provenance).

## Figure 7

Frozen numerical inputs retain their historical `figure8` identifiers.
Canonical inputs: `tables/figure_sources/figure8/`; publication generator:
`scripts/analysis/build_paper_multiobjective_figure.py`. Default PDF:
`paper/figures/fig07_multiobjective.pdf`; default PNG:
`reproduced/figure7/previews/fig07_multiobjective.png`.
Existing outputs are protected. For a safe reproduction:

```powershell
.venv/Scripts/python.exe scripts/analysis/build_paper_multiobjective_figure.py --output-dir reproduced/figure7/recheck --audit-dir reproduced/figure7/recheck/audit
```

Saved 20000-weight S1 distributions are reused (seed 1984). D sums C's first
five ranks; no weights are resampled. The old `build_paper_figure08_hybrid.py` entry point remains a compatibility
wrapper and also exports publication number 07. Historical/alternative analyses remain
available through `scripts/analysis/build_paper_figure08.py`.

## Supporting analyses

Frozen OVL/SWD results, projection directions, sample identities and bootstrap
arrays are tracked at `tables/figure_sources/figure5_overlap/`. Validate into a
new directory without replacing selected SI:

```powershell
.venv/Scripts/python.exe scripts/analysis/prepare_figure5_overlap_si.py --output-dir reproduced/figure5_overlap/recheck/publication --audit-dir reproduced/figure5_overlap/recheck/audit
.venv/Scripts/python.exe scripts/analysis/audit_figure8_sensitivity.py --output-dir reproduced/figure8/sensitivity_recheck --publication-dir reproduced/figure8/sensitivity_recheck/publication
```

Historical audit JSONs retain original paths/hashes. Resolve moved inputs through
`tables/figure_sources/path_relocations.json`; original document hashes can be
checked in checkpoint `0f76fdb4`. Frozen CSV/NPZ values and selected multiobjective PDF bytes (now Figure 7)
are unchanged by reorganization.

## Publication typography

Canonical Figures 2–7 and supplementary PCA now use Ebrima Regular, matching
the read-only Figure 1 reference. Windows builds resolve `C:/Windows/Fonts/ebrima.ttf`;
other environments must provide a locally installed Ebrima Regular via
`MAGGENBENCH_EBRIMA_FONT`. A missing face is an error, never a silent fallback.
Do not copy system fonts into the repository.

The shared implementation is `src/mvpipeline/analysis/typography.py`. Native
plot exporters use its Matplotlib font registration and text-artist settings.
The typography rebuild preserves scientific vector/image layers from the
audited canonical revision, including Figure 4 statistics and the composed
Figure 6 A/B panels; it does not refit PCA or rerun predictions. Figure 6 C/D
are rebuilt from the frozen ten-set diversity table with their original colors,
a 4 pt label offset and a measured right-frame gutter (display limits 0–124).
The shared font hierarchy includes a modest 0.5 pt increase over the initial
Ebrima revision:

```powershell
.venv/Scripts/python.exe scripts/illustrations/restyle_publication_typography.py --source-from-git --output-dir reproduced/figure_typography/recheck
```

Figure 1 is excluded by explicit guards. See `reproduced/figure_typography_audit.md`
for the old/new text table, embedded-font checks and numerical-preservation proof.
The subsequent font-size and Figure 6 spacing pass is documented in
`reproduced/figure_layout_polish_audit.md`.
