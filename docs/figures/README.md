# Figure reproduction

Run from the repository root with the project installed, or set `PYTHONPATH=src`.
No model training or new structure generation is needed for publication plots.

- [Figure 2](figure2_reproduction.md): full harmonized QC populations.
- [Figure 3](figure3_reproduction.md): ten-set descriptors and frozen inputs.
- [Figure 4](figure4_reproduction.md): retained statistical vectors and limitations.
- [Figures 3/5 styling history](figures_3_5_polish.md).
- Figure 5: `python scripts/illustrations/plot_manuscript_figure5_v2.py --help`.
- Figure 6: `python scripts/illustrations/plot_fig06_diversity_adaptation_palette_preview.py`.
- PCA: `python scripts/illustrations/plot_paper_pca.py`.

## Figure 8

Canonical inputs: `tables/figure_sources/figure8/`; publication generator:
`scripts/analysis/build_paper_figure08_hybrid.py`. Default PDF:
`paper/figures/fig08_multiobjective.pdf`; default PNG:
`reproduced/figure8/previews/fig08_multiobjective.png`.
Existing outputs are protected. For a safe reproduction:

```powershell
.venv/Scripts/python.exe scripts/analysis/build_paper_figure08_hybrid.py --output-dir reproduced/figure8/recheck --audit-dir reproduced/figure8/recheck/audit
```

Saved 20000-weight S1 distributions are reused (seed 1984). D sums C's first
five ranks; no weights are resampled. Historical/alternative analyses remain
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
checked in checkpoint `0f76fdb4`. Frozen CSV/NPZ values and selected Figure 8 bytes
are unchanged by reorganization.
