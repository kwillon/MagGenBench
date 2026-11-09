# Figure 8 hybrid: audit

Date: 2026-11-09. Validation: PASS.

- A retains the new five-metric matrix: QC retention, unique-formula yield, 3d atomic-content yield (S1), configured-lanthanide atomic-content yield (S2), and configured-group union yield (S3). Annotations are original percentages; colors are normalized within each metric. A nonzero value below 0.01% is printed with four decimals.
- B restores the old scatter styling and Base/FT/Refined marker shapes. Marker area now uses S1 3d atomic-content yield (55 + 2 × yield in percentage units), and dark outlines identify the saved three-objective S1 Pareto frontier. Pareto status was independently checked from the S1 metrics; no fitted curve is implied.
- C restores the full rank 1–10 distribution for S1 only. The saved scenario ranking CSV already contains all ten rank-frequency columns, so no weight generation or rank-distribution recalculation was needed. These saved results were calculated with 20000 Dirichlet(1,1,1) weights and seed 1984. Row/column sums, integer sample counts, first/top3/top5 frequencies, mean ranks and agreement with D S1 were checked.
- D retains first-place frequencies for S1, S2 and S3. It is not a top-5 plot. Each scenario column sums to 100%.

Only display normalization and marker areas were calculated for plotting. Normalized equal-weight scores/ranks and Pareto dominance were independently recalculated as validation checks, without replacing saved results. All yields use Ngen=2000; atomic-content yields sum per-structure fractions over QC-retained structures, while S3 counts presence of either configured group (OR, not AND). These are chemical proxies, not validated magnetic properties.

The four panels retain a 2×2 layout. All explanatory footer lines were removed; axis/colorbar labels and the scatter size legend remain. Fonts are enlarged from the scenario figure's 9–10 pt to 11–12 pt, with 15 pt panel titles. The existing project palette, embedded TrueType PDF fonts, and white publication background are retained. Article text and existing figures were not changed.

Inputs: `reproduced/figure8/figure08_scenario_metrics_v2.csv`, `figure08_scenario_rankings_v2.csv`, and `figure08_scenario_pareto_v2.csv`. Implementation follows `scripts/analysis/build_paper_figure08.py` and imports the existing `plotting_v2` publication style. Exact source/output SHA256 hashes and numeric checks are in `audit.json`; four panel-source CSVs accompany this report.

Final visual QA: the exported PDF was rendered with pdftoppm and inspected alongside the 300 dpi PNG preview. Scatter annotations and legend, panel headings, heatmap labels and colorbars are separated and readable. No explanatory footer remains. Final artifacts: `paper/figures/fig08_multiobjective_hybrid.pdf` and `paper/figures/fig08_multiobjective_hybrid.png`. The generator refuses to overwrite existing outputs.
