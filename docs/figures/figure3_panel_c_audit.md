# Figure 3 panel C: Con-CDVAE Base

Reproduce the input audit and Figure 3 without recomputing descriptors:

```powershell
.venv/Scripts/python.exe scripts/analysis/audit_figure3_panel_c.py
.venv/Scripts/python.exe scripts/analysis/audit_figure3_panel_c.py --build
```

Inputs are `tables/10_analysis_v2_magnetic/analysis_v2_magnetic.csv` and
`tables/03_features/master_structures_with_classes.csv`, loaded by the selected
Figure 3 loader. QC-retained IDs are joined to descriptors; panel C selects
`analysis_cohort == "concdvae_baseline"` and `magnetic_geometry_status == "ok"`,
then drops missing values. The descriptor reader excludes nonfinite values.
No missing or not-applicable records are replaced by zero.

| Quantity | Value |
|---|---:|
| QC-retained records | 1864 |
| Applicable finite values | 1168 |
| Genuine zeros | 977 (83.6472602739726%) |
| Not applicable (excluded) | 696 |
| Missing values with status ok | 0 |
| Missing status | 0 |
| min / Q1 / median / Q3 / max | 0 / 0 / 0 / 0 / 1 |
| Lower / upper whisker | 0 / 0 |
| Positive values | 191 |
| Positive values classified as fliers | 191 |

The actual boxplot call uses `whis=1.5` (the Matplotlib rcParam),
`autorange=False`, and `showfliers=False`. With zero IQR and autorange disabled,
both whiskers and the entire box collapse at y=0. All 191 positive values
(16.3527397260274% of applicable finite values) are hidden as fliers; a visible
zero line does not mean every applicable record is zero.

The former panel-C lower limit of zero placed the collapsed box directly on
the bottom spine. Panel C now uses limits (-0.04, 1.05), and its median lines
use zorder 4, above boxes, caps, whiskers, grid and spines. Values, quartiles,
whisker rules, hidden-fliers setting and panels A/B are unchanged.

The audit captures the actual `_boxplot` call settings, fingerprints all 30
boxplot populations before and after, checks the zero median and its drawing
order, exports PNG/PDF/SVG, renders the PDF, and checks text bounds and the
16:9 page size. It updates only the Figure 3 PDF and its checksum entry.
Figure 1 and Figure 4 PDF hashes must match the initial audit. Detailed reports
and the preview are under `reproduced/figure3_panel_c/`.
