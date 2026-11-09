"""Export exact baseline comparisons from the audited, source-precision CSV."""
import csv
import argparse
from decimal import Decimal as D
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO/'reproduced/figure8/scenario_sensitivity'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir',type=Path,default=ROOT/'recheck')
ROOT = parser.parse_args().output_dir
ROOT.mkdir(parents=True,exist_ok=True)
with (REPO/'tables/figure_sources/figure8/scenario_sensitivity_publication.csv').open(encoding='utf-8',newline='') as f:
    rows=list(csv.DictReader(f))
lookup={(r['variant'],r['analysis_cohort']):r for r in rows}
changes=[]
for row in rows:
    variant=row['variant']
    baseline='A' if variant in ('B','C') else variant[:-3] if variant.endswith('-2D') else None
    if baseline is None:continue
    original=lookup[baseline,row['analysis_cohort']]
    changes.append(dict(variant=variant,baseline_variant=baseline,analysis_cohort=row['analysis_cohort'],label=row['label'],
        baseline_equal_weight_score=original['equal_weight_score_source'],
        equal_weight_score=row['equal_weight_score_source'],
        equal_weight_score_delta=str(D(row['equal_weight_score_source'])-D(original['equal_weight_score_source'])),
        baseline_equal_weight_rank=original['equal_weight_rank'],equal_weight_rank=row['equal_weight_rank'],
        equal_weight_rank_delta=int(row['equal_weight_rank'])-int(original['equal_weight_rank']),
        baseline_first_place_pct=original['first_place_pct_exact'],first_place_pct=row['first_place_pct_exact'],
        first_place_delta_pp=str(D(row['first_place_pct_exact'])-D(original['first_place_pct_exact'])),
        baseline_pareto_efficient=original['pareto_efficient'],pareto_efficient=row['pareto_efficient'],
        pareto_membership_changed=original['pareto_efficient']!=row['pareto_efficient']))
with (ROOT/'criteria_ablation_changes.csv').open('x',encoding='utf-8',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(changes[0]))
    writer.writeheader();writer.writerows(changes)
print('Saved 50 exact baseline comparisons: B/C versus A, S1/S2/S3-2D versus their three-objective scenarios.')
