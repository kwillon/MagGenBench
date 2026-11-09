# Scenario sensitivity audit

Date: 2026-11-09. PASS. Existing results and figures were read only. No sampling, training, generation, or ranking-result replacement was performed.

## Correlation

Across the ten generated sets, QC retention versus unique-formula yield: Pearson r = 0.8451521417668733; Spearman rho = 0.9151515151515152. Rounded to three decimals: 0.845, 0.915. Spearman uses average ranks (there are no ties in these two series). These yields share a structural-retention component: unique yield = QC retention × within-QC uniqueness / 100.

## Pareto-front membership

- S1: 6 sets: MatterGen Base, MatterGen FT, Con-CDVAE Base, Con-CDVAE FT, CrystalFormer FT, Crys-JEPA Base. Identical membership after removing the QC objective.
- S2: 4 sets: MatterGen Base, Con-CDVAE Base, Crys-JEPA Base, Crys-JEPA Refined. Identical membership after removing the QC objective.
- S3: 2 sets: MatterGen Base, Con-CDVAE Base. Identical membership after removing the QC objective.

Criterion values for every efficient set (and the remaining sets) are in Table S8 and the publication CSV. All saved pairwise dominance relations and n_dominators were independently reconstructed for all nine variants.

## Ranking sensitivity and rounding

Each rank frequency was converted back to an integer count out of 20000; all saved frequencies match counts within numerical floating-point tolerance. All rank distributions sum to 100% by row and rank column. First/Top-3/Top-5 totals are 100/300/500%. All saved first/Top-3/Top-5 summaries and mean ranks match full distributions. Equal-weight scores/ranks were independently checked from the saved normalized criterion values; no random weights were resampled.

Publication CSV retains source-text precision, exact three-decimal frequencies from integer counts, and two-decimal ROUND_HALF_UP values. At exact decimal ties, binary-float formatting can give inconsistent last digits. The requested S2 Crys-JEPA Refined 25.32% corresponds to exactly 5065/20000 = 25.325%; ROUND_HALF_UP gives 25.33%, whereas half-even gives 25.32%. Tables/section therefore use three decimals to avoid ambiguity. Similarly, 41.825%, 32.515%, 40.825%, 57.025%, and 42.975% are the exact values underlying the other requested rounded frequencies.

## Alternative criteria: comparison provenance

- A: qc_retention_pct, unique_formula_yield_pct, 3d_containing_yield_pct. Pareto size 5; Crys-JEPA Refined score 0.4378153808998346, rank 7.
- B: qc_retention_pct, unique_formula_yield_pct, 3d_containing_yield_pct, lanthanide_containing_yield. Pareto size 5; Crys-JEPA Refined score 0.48576894308228336, rank 5.
- C: qc_retention_pct, unique_formula_yield_pct, 3d_atomic_content_yield, lanthanide_atomic_content_yield. Pareto size 7; Crys-JEPA Refined score 0.579885820577964, rank 4.

The reported 5 -> 7 Pareto expansion and rank 7 -> 4 refer specifically to A -> C. A is not S1: S1 already has six efficient sets. B -> C also expands 5 -> 7 but moves Refined only 5 -> 4. A and B share the same five members. C adds Crys-JEPA Base and Refined to A. Full scores/ranks/frequencies/membership for A/B/C are in Table S9 and the CSV.

## QC ablation

- S1 equal-weight leader: MatterGen Base; score 0.7678980714986876; first-place frequency 32.515%.
- S1-2D equal-weight leader: MatterGen Base; score 0.7104541287655853; first-place frequency 31.800%.
- S2 equal-weight leader: Crys-JEPA Base; score 0.8644691927639716; first-place frequency 31.340%.
- S2-2D equal-weight leader: Crys-JEPA Base; score 0.8250163599273843; first-place frequency 35.085%.
- S3 equal-weight leader: Con-CDVAE Base; score 0.8874429223744292; first-place frequency 57.025%.
- S3-2D equal-weight leader: MatterGen Base; score 0.8755530973451328; first-place frequency 57.390%.

For S3, MatterGen Base rises from rank 2 (score 0.8779640505517192, first 42.975%) to rank 1 (0.8755530973451328, first 57.390%); Con-CDVAE Base moves from rank 1 (0.8874429223744292, first 57.025%) to rank 2 (0.8311643835616438, first 42.610%). Removal of the QC objective changes weights and scores, but does not remove QC filtering or the QC dependence embedded in the two remaining yields. Full ablation results for all ten sets are in Table S9 and CSV.

## Figure and text consistency

The current hybrid_v2 Figure 8B-D show S1 only; D is Top-5, not first-place frequency. Its saved D counts match S1 exactly. S2, S3 and ablation results are cited to provisional Tables S8/S9. The original full Sections 3.7.2-3.7.4 were not provided; consolidation follows the four requested scientific parts, without claiming line-by-line preservation. The previous 3.7.1 text is not repeated. Chemical proxies do not establish magnetism.

## Sources and checks

- `reproduced\figure8\figure08_scenario_metrics_v2.csv`
- `reproduced\figure8\figure08_scenario_rankings_v2.csv`
- `reproduced\figure8\figure08_scenario_pareto_v2.csv`
- `reproduced\figure8\figure08_criteria_metrics_v2.csv`
- `reproduced\figure8\figure08_criteria_rankings_v2.csv`
- `reproduced\figure8\figure08_criteria_pareto_v2.csv`
- `reproduced\figure8\figure08_ablation_metrics_v2.csv`
- `reproduced\figure8\figure08_ablation_rankings_v2.csv`
- `reproduced\figure8\figure08_ablation_pareto_v2.csv`
- `reproduced\figure8\audit_2026-11-09\scenario_results_source_precision.csv`
- `reproduced\figure8\hybrid_v2\panel_D_S1_top5_pct.csv`
- Methodology: `scripts/analysis/build_paper_figure08.py` (criterion definitions, min-max normalization, independent seed reset 1984 for each variant, stable cohort-order tie rule).

All nine variants (90 cohort/variant records), 900 pairwise dominance entries, and all 900 rank-frequency entries passed consistency checks. No analysis was missing. Thus no sensitivity analysis had to be reproduced.

## Deliverables

- `section_3_7_2_consolidated.md`: four English paragraphs, 390 body words; a proposed replacement section, not an edit to the manuscript.
- `table_s8_scenario_results.md`: all ten sets in S1/S2/S3, with criterion values, Pareto membership, scores, ranks, and first/Top-3/Top-5 frequencies.
- `table_s9_criteria_ablation.md`: all sets under A/B/C and the three QC-ablation variants. S8/S9 numbering remains provisional.
- `scenario_sensitivity_publication.csv`: 90 cohort/variant records; source score strings, exact integer frequency counts, exact three-decimal frequencies, and publication rounding.
- `criteria_ablation_changes.csv`: 50 exact comparisons (B/C versus A; each 2D ablation versus its corresponding S1/S2/S3 baseline), including scores, ranks, first-place percentage-point differences, and Pareto changes. Score deltas describe mathematical differences between scoring systems, not directly comparable performance gains.
- `source_manifest.json`: source and protected-figure hashes plus correlation/frontier results.
- `build_audit.py`, `extract_changes.py`: independent standard-library verification/export code; exclusive file creation prevents output overwrites.
