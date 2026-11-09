"""Read-only audit of saved Figure 8 inputs; stdlib only; never plots or trains.

Run from the repository root. Outputs use exclusive creation to prevent overwrite.
"""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal as D
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SOURCES = set()


def rows(name):
    path = ROOT / name
    SOURCES.add(path)
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(name, data):
    with (OUT / name).open("x", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def close(a, b, tol="1e-10"):
    assert abs(D(str(a)) - D(str(b))) <= D(tol), (a, b)


metrics = rows("tables/figure_sources/figure8/figure08_scenario_metrics_v2.csv")
ranks = rows("tables/figure_sources/figure8/figure08_scenario_rankings_v2.csv")
original = rows("tables/figure_sources/fig08_metric_matrix.csv")
diversity = rows("tables/figure_sources/fig06_diversity_summary.csv")
energy = rows("tables/figure_sources/fig05_energy_magnetism.csv")
order = [r["analysis_cohort"] for r in original]
assert len(order) == len(set(order)) == 10
assert len(metrics) == 90 and len(ranks) == 30
assert len({(r['variant'], r['analysis_cohort'], r['criterion']) for r in metrics}) == 90
assert len({(r['variant'], r['analysis_cohort']) for r in ranks}) == 30
assert {r['n_generated_assumed'] for r in metrics} == {'2000'}
assert {r['variant'] for r in metrics} == {'S1', 'S2', 'S3'}
by = {(r['variant'], r['analysis_cohort'], r['criterion']): r for r in metrics}
rb = {(r['variant'], r['analysis_cohort']): r for r in ranks}
ob = {r['analysis_cohort']: r for r in original}
db = {r['analysis_cohort']: r for r in diversity}
chemicals = {'S1': '3d_atomic_content_yield', 'S2': 'lanthanide_atomic_content_yield',
             'S3': 'configured_3d_lanthanide_union_yield'}

# The same descriptor population assembled by the original build script.
descriptors = rows('tables/10_analysis_v2_magnetic/analysis_v2_magnetic.csv')
for cohort in ('crystalformer_finetuned', 'crystallm_finetuned'):
    descriptors += rows(f'tables/figure_sources/{cohort}_descriptors.csv')
assert len(descriptors) == len(energy) == 12281
assert len({r['sample_uid'] for r in descriptors}) == 12281
assert {(r['analysis_cohort'], r['sample_uid']) for r in descriptors} == {
    (r['analysis_cohort'], r['sample_uid']) for r in energy}
grouped = defaultdict(list)
for r in descriptors:
    assert r['sample_uid'].strip()
    grouped[r['analysis_cohort']].append(r)
assert set(grouped) == set(order)

# Re-read benchmark QC status records, including rejected rows.
qc = {}
baseline = ROOT / 'tables/02_validation/master_structures_with_validation_status.csv'
SOURCES.add(baseline)
with baseline.open(encoding='utf-8-sig', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    assert header[-3:] == ['status', 'status_source', 'rejection_reason']
    baseline_rows = list(reader)
assert len(baseline_rows) == 8000
for model, cohort in zip(('MatterGen', 'Con-CDVAE', 'CrystalFormer', 'CrystaLLM'),
                        ('mattergen_baseline', 'concdvae_baseline',
                         'crystalformer_baseline', 'crystallm_baseline')):
    population = [r for r in baseline_rows if r[1].strip() == model]
    assert {r[-2].strip() for r in population} == {'all_structures_row_order'}
    assert {r[-3].strip() for r in population} == {'validated', 'rejected'}
    qc[cohort] = (len(population), sum(r[-3].strip() == 'validated' for r in population), str(baseline.relative_to(ROOT)))
for cohort in order:
    if cohort in qc:
        continue
    filename = ('phase5b_' if cohort.endswith('_finetuned') else '') + cohort + '_with_classes.csv'
    name = 'tables/03_features/' + filename
    population = rows(name)
    identity = 'sample_uid' if 'sample_uid' in population[0] else 'structure_id'
    assert len({r[identity].strip() for r in population}) == len(population)
    assert all(r[identity].strip() for r in population)
    assert {r['status'].strip().lower() for r in population} <= {'validated', 'rejected'}
    qc[cohort] = (len(population), sum(r['status'].strip().lower() == 'validated' for r in population), name)

qc_output, precision, rounding, comparison = [], [], [], []
for cohort in order:
    source = ob[cohort]
    group = grouped[cohort]
    n, retained, qc_path = qc[cohort]
    assert n == 2000 and retained == len(group) == int(source['n']) == int(db[cohort]['n'])
    qc_output.append(dict(analysis_cohort=cohort, n_total=n, n_qc=retained,
                          n_rejected=n-retained, qc_source=qc_path))
    # Figure 6 uses formula_reduced, not formula+space-group identity.
    nf = len({r['formula_reduced'] for r in group})
    assert nf == int(source['n_unique_formula']) == int(db[cohort]['n_unique_formula'])
    f3 = [D(r['transition_3d_fraction']) for r in group]
    fl = [D(r['configured_lanthanide_fraction']) for r in group]
    assert all(0 <= x <= 1 for x in f3 + fl)
    presence = D(sum(x > 0 for x in f3)) / 20
    close(presence, source['3d_containing_yield_pct'])
    expected = {'qc_retention_pct': D(retained)/20, 'unique_formula_yield_pct': D(nf)/20,
                chemicals['S1']: sum(f3)/20, chemicals['S2']: sum(fl)/20,
                chemicals['S3']: D(sum(a > 0 or b > 0 for a, b in zip(f3, fl)))/20}
    out = dict(analysis_cohort=cohort, label=source['label'], n_generated=2000, n_qc=retained,
               n_unique_formula=nf)
    for metric in ('qc_retention_pct', 'unique_formula_yield_pct'):
        saved = by['S1', cohort, metric]['value_pct']
        out[metric] = saved  # Keep the exact text precision stored in source CSV.
    for scenario, chemical in chemicals.items():
        for criterion in ('qc_retention_pct', 'unique_formula_yield_pct', chemical):
            row = by[scenario, cohort, criterion]
            assert int(row['n_qc']) == retained
            close(row['value_pct'], expected[criterion])
        out[scenario+'_chemical_yield_pct'] = by[scenario, cohort, chemical]['value_pct']
        out[scenario+'_equal_weight_score'] = rb[scenario, cohort]['equal_weight_score']
        out[scenario+'_equal_weight_rank'] = rb[scenario, cohort]['equal_weight_rank']
    out['original_3d_containing_yield_pct'] = source['3d_containing_yield_pct']
    precision.append(out)
    rounded = out.copy()
    for key, value in out.items():
        if key.endswith('_pct'):
            rounded[key] = f'{D(value):.4f}' if 0 < D(value) < D('.01') else f'{D(value):.2f}'
        elif key.endswith('_score'):
            rounded[key] = f'{D(value):.4f}'
    rounding.append(rounded)
    comparison.append(dict(analysis_cohort=cohort, original_equal_weight_score=source['equal_weight_score'],
                           original_equal_weight_rank=source['equal_weight_rank'],
                           **{s+'_equal_weight_rank': out[s+'_equal_weight_rank'] for s in chemicals}))

# Independently reconstruct normalization, equal-weight scores and ranks only.
# No random sampling or rerunning the Figure 8 build script.
for scenario, chemical in chemicals.items():
    criteria = ('qc_retention_pct', 'unique_formula_yield_pct', chemical)
    normalized = defaultdict(list)
    for criterion in criteria:
        values = [D(by[scenario, c, criterion]['value_pct']) for c in order]
        lo, hi = min(values), max(values)
        for cohort, value in zip(order, values):
            z = (value-lo)/(hi-lo) if hi > lo else D(0)
            close(z, by[scenario, cohort, criterion]['normalized_score'], '1e-14')
            normalized[cohort].append(z)
    score = {c:sum(normalized[c])/3 for c in order}
    ranked = sorted(order, key=lambda c:-score[c])
    for cohort in order:
        close(score[cohort], rb[scenario, cohort]['equal_weight_score'], '1e-14')
        assert ranked.index(cohort)+1 == int(rb[scenario, cohort]['equal_weight_rank'])
    assert {rb[scenario,c]['n_weights'] for c in order} == {'20000'}

write_csv('scenario_results_source_precision.csv', precision)
write_csv('scenario_results_publication.csv', rounding)
write_csv('qc_budget_verification.csv', qc_output)
write_csv('original_vs_scenario_ranks.csv', comparison)
table = ['| Generated set | QC (%) | Unique (%) | S1 yield (%) | S1 score / rank | S2 yield (%) | S2 score / rank | S3 yield (%) | S3 score / rank |',
         '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for r in rounding:
    cells = [r['label'], r['qc_retention_pct'], r['unique_formula_yield_pct']]
    for s in chemicals:
        cells += [r[s+'_chemical_yield_pct'], r[s+'_equal_weight_score']+' / '+r[s+'_equal_weight_rank']]
    table.append('| '+' | '.join(cells)+' |')
with (OUT/'comparison_table.md').open('x', encoding='utf-8') as f:
    f.write('\n'.join(table)+'\n\nAll yields use Ngen = 2000. Scores are dimensionless (0-1); rank 1 is best. S1/S2: summed per-structure atomic fractions; S3: presence of either configured group. Percentages have two decimals, except nonzero values below 0.01%, shown with four decimals.\n')
for name in ('scripts/analysis/build_paper_figure08.py', 'paper/figures/fig08_multiobjective.pdf',
             'docs/figures/legacy/fig08_presence_caption.md', 'config/magnetism.yaml',
             'reproduced/figure8/figure08_scenarios_v2.pdf',
             'tables/figure_sources/fig08_rank_distribution.csv',
             'tables/figure_sources/fig08_ranking_summary.csv'):
    SOURCES.add(ROOT/name)
manifest = {str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SOURCES)}
with (OUT/'verification.json').open('x', encoding='utf-8') as f:
    json.dump(dict(status='PASS', cohorts=10, n_generated_per_cohort=2000,
                   retained_total=12281, checks=['QC statuses and budget for all ten benchmark sets',
                   'exact descriptor/energy sample identity', 'unique reduced formulas',
                   'all five yields against saved source precision', 'scenario normalization, equal scores and ranks'],
                   tolerance_yields_pct='1e-10', tolerance_score='1e-14', source_sha256=manifest), f, indent=2)
print('\n'.join(table))
print('PASS: ten cohorts; 2000 benchmark QC records each; 12281 retained; saved scores and ranks verified.')
