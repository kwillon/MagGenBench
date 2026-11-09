# Figure 8 hybrid v2: audit

Date: 2026-11-09. Validation: PASS.

- A: all five metrics, original values, model order, and min-max normalization are unchanged. Only the palette and text contrast changed. A nonzero value below 0.01% is printed with four decimals.
- B: the S1 scatter retains its coordinates, marker areas (55 + 2 × 3d atomic-content yield) and Pareto outlines. Base/FT/Refined use circle/square/diamond markers; every variant now uses the same specified family color.
- C: the complete saved S1 rank 1-10 distribution is unchanged. Its sequential palette now matches A. Results use 20000 Dirichlet(1,1,1) weights and seed 1984; there was no resampling.
- D: the horizontal Top-5 bar design is restored. Each value is obtained by summing C's saved S1 rank_1_pct through rank_5_pct and verified against the saved S1 top5_pct. All ten sets appear, sorted descending with stable cohort order for ties. Bars use family colors; three-decimal percentage labels follow bar ends, preserving the 0.005 percentage-point resolution of 20000 weights. Old 3d-containing results and first-place frequencies are not used for these bars.

Only display normalization, marker areas and D's sum of saved rank frequencies were calculated for plotting. Normalized equal-weight scores/ranks and Pareto dominance were independently recalculated as validation checks, without replacing saved results. C row/column sums, integer counts out of 20000, mean rank, and first/top3/top5 summaries pass. D counts sum to 100000 (five occupied ranks per weight), so its frequencies correctly sum to 500%, not 100%. All yields use Ngen=2000; atomic-content yields sum per-structure fractions over QC-retained structures, while S3 counts presence of either configured group (OR, not AND).

The four panels retain a 2×2 layout, white background, no explanatory footer, unified 11-12 pt labels and 15 pt headings, and embedded TrueType PDF fonts. Family palette: MatterGen #4F6745; Con-CDVAE #61838F; CrystalFormer #E89339; CrystaLLM #AD463D; Crys-JEPA #304862. A/C sequential gradient: #F4EFE5 -> #B2C1BC -> #829DA6 -> #61838F -> #243350. A annotations choose dark/white text using relative luminance for contrast. Article text and previous publication figures were not changed; their hashes are checked.

Inputs: `reproduced/figure8/figure08_scenario_metrics_v2.csv`, `figure08_scenario_rankings_v2.csv`, and `figure08_scenario_pareto_v2.csv`. Implementation follows `scripts/analysis/build_paper_figure08.py` and imports the existing `plotting_v2` publication style. Exact source/output SHA256 hashes and numeric checks are in `audit.json`; four panel-source CSVs accompany this report.

## S1 Top-5 frequencies

| Generated set | Top-5 count / 20000 | Frequency (%) |
|---|---:|---:|
| MatterGen Base | 20000 | 100.000 |
| CrystalFormer FT | 19729 | 98.645 |
| Crys-JEPA Base | 17406 | 87.030 |
| Con-CDVAE Base | 14855 | 74.275 |
| MatterGen FT | 13004 | 65.020 |
| Con-CDVAE FT | 9700 | 48.500 |
| Crys-JEPA Refined | 5233 | 26.165 |
| CrystalFormer Base | 73 | 0.365 |
| CrystaLLM Base | 0 | 0.000 |
| CrystaLLM FT | 0 | 0.000 |

## Final visual verification

The final `paper/figures/fig08_multiobjective_hybrid_v2.pdf` was rendered with pdftoppm at 2000 px and visually inspected. A/C use the specified sequential gradient; B/D use the specified family colors. Panel labels, tick labels, colorbars, scatter annotations and legend, and all ten D bar-end percentages are readable without overlap or clipping. No explanatory footer is present. The 300 dpi preview is `paper/figures/fig08_multiobjective_hybrid_v2.png`.

Numerical A/C matrices were also compared against the previous hybrid audit exports (absolute tolerance 1e-12); they are unchanged. The generator refuses to overwrite existing outputs. Reproduction command, from the repository root: `.venv/Scripts/python.exe scripts/analysis/build_paper_figure08_hybrid.py` (choose new `--output-dir` and `--audit-dir` paths for a further run).
