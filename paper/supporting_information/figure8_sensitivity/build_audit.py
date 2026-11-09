"""Audit frozen Figure 8 analyses using stdlib only; never overwrite outputs."""
import csv
import hashlib
import json
import math
from collections import defaultdict
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
BASE = ROOT/'reproduced/figure8'
source_hashes = {}


def read(path):
    source_hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def save(name, text):
    with (OUT/name).open('x', encoding='utf-8') as f:
        f.write(text)


def close(a, b, tolerance='1e-10'):
    assert abs(D(str(a))-D(str(b))) <= D(tolerance), (a, b)


def rounded(x, places=2):
    return format(D(str(x)).quantize(D(1).scaleb(-places), rounding=ROUND_HALF_UP), f'.{places}f')


def corr(x, y):
    mx, my = sum(x)/len(x), sum(y)/len(y)
    return sum((a-mx)*(b-my) for a,b in zip(x,y))/math.sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))


def rank_values(x):
    return [1+sum(v<a for v in x)+(sum(v==a for v in x)-1)/2 for a in x]


families = {}
results = []
fronts = {}
definitions = {}
criteria_values = {}
for family in ('scenario','criteria','ablation'):
    metrics = read(BASE/f'figure08_{family}_metrics_v2.csv')
    rankings = read(BASE/f'figure08_{family}_rankings_v2.csv')
    pareto = read(BASE/f'figure08_{family}_pareto_v2.csv')
    families[family] = (metrics, rankings, pareto)
    assert len(rankings) == 30 and len(pareto) == 300
    assert len({(r['variant'],r['analysis_cohort']) for r in rankings}) == 30
    assert len({(r['variant'],r['analysis_cohort'],r['criterion']) for r in metrics}) == len(metrics)
    assert len({(r['variant'],r['analysis_cohort'],r['compared_cohort']) for r in pareto}) == 300
    variants = list(dict.fromkeys(r['variant'] for r in rankings))
    for variant in variants:
        rr = [r for r in rankings if r['variant']==variant]
        order = [r['analysis_cohort'] for r in rr]
        assert len(set(order)) == 10
        mm = [r for r in metrics if r['variant']==variant]
        criteria = list(dict.fromkeys(r['criterion'] for r in mm))
        definitions[variant] = criteria
        assert len(mm)==10*len(criteria)
        values = {(r['analysis_cohort'],r['criterion']):r for r in mm}
        criteria_values[variant]=values
        assert {r['n_generated_assumed'] for r in mm}=={'2000'}
        zz=defaultdict(list)
        for criterion in criteria:
            xx = [D(values[c,criterion]['value_pct']) for c in order]
            lo,hi=min(xx),max(xx)
            for c,x in zip(order,xx):
                assert 0<=x<=100
                z=(x-lo)/(hi-lo) if hi>lo else D(0)
                close(z,values[c,criterion]['normalized_score'],'1e-14')
                zz[c].append(z)
        scores={c:sum(zz[c])/len(criteria) for c in order}
        ranked=sorted(order,key=lambda c:-scores[c])
        pp={(r['analysis_cohort'],r['compared_cohort']):r for r in pareto if r['variant']==variant}
        dominated={c:0 for c in order}
        for a in order:
            for b in order:
                av=[D(values[a,k]['value_pct']) for k in criteria]
                bv=[D(values[b,k]['value_pct']) for k in criteria]
                dom=all(x>=y for x,y in zip(av,bv)) and any(x>y for x,y in zip(av,bv))
                assert dom==(pp[a,b]['dominates']=='True')
                dominated[b]+=dom
        fronts[variant]=[r['label'] for r in rr if not dominated[r['analysis_cohort']]]
        for r in rr:
            c=r['analysis_cohort']
            close(scores[c],r['equal_weight_score'],'1e-14')
            assert ranked.index(c)+1==int(r['equal_weight_rank'])
            assert int(r['n_weights'])==20000
            p=[D(r[f'rank_{k}_pct']) for k in range(1,11)]
            counts=[int((x*200).to_integral_value()) for x in p]
            for x,count in zip(p,counts):
                assert 0<=count<=20000
                close(x*200,count,'1e-8')
            assert sum(counts)==20000
            close(sum(p),100)
            close(sum((i+1)*p[i] for i in range(10))/100,r['mean_rank'])
            for n,key in ((1,'first_place_pct'),(3,'top3_pct'),(5,'top5_pct')):
                close(sum(p[:n]),r[key])
            for b in order:
                assert (pp[c,b]['pareto_efficient']=='True')==(dominated[c]==0)
                assert int(pp[c,b]['n_dominators'])==dominated[c]
            out=dict(analysis_family=family,variant=variant,analysis_cohort=c,label=r['label'],
                     n_generated=2000,n_weights=20000,n_criteria=len(criteria),
                     criteria=';'.join(criteria),pareto_efficient=dominated[c]==0,
                     equal_weight_score_source=r['equal_weight_score'],
                     equal_weight_score_publication=rounded(r['equal_weight_score'],4),
                     equal_weight_rank=int(r['equal_weight_rank']))
            for n,key in ((1,'first_place_pct'),(3,'top3_pct'),(5,'top5_pct')):
                exact=D(sum(counts[:n]))/200
                out[key+'_source']=r[key]
                out[key+'_count']=sum(counts[:n])
                out[key+'_exact']=format(exact,'.3f')
                out[key+'_publication_2dp']=rounded(exact)
            for key in ('qc_retention_pct','unique_formula_yield_pct','3d_containing_yield_pct',
                        'lanthanide_containing_yield','3d_atomic_content_yield',
                        'lanthanide_atomic_content_yield','configured_3d_lanthanide_union_yield'):
                out[key]=values[c,key]['value_pct'] if (c,key) in values else ''
            results.append(out)
        for k in range(1,11):
            close(sum(D(r[f'rank_{k}_pct']) for r in rr),100)
        close(sum(D(r['first_place_pct']) for r in rr),100)
        close(sum(D(r['top3_pct']) for r in rr),300)
        close(sum(D(r['top5_pct']) for r in rr),500)

lookup={(r['variant'],r['analysis_cohort']):r for r in results}
for s,expected in (('S1',6),('S2',4),('S3',2)):
    assert len(fronts[s])==expected
    assert fronts[s]==fronts[s+'-2D']
    for c in [r['analysis_cohort'] for r in results if r['variant']==s]:
        for k in definitions[s+'-2D']:
            close(criteria_values[s][c,k]['value_pct'],criteria_values[s+'-2D'][c,k]['value_pct'])
            close(criteria_values[s][c,k]['normalized_score'],criteria_values[s+'-2D'][c,k]['normalized_score'])
assert len(fronts['A'])==5 and len(fronts['B'])==5 and len(fronts['C'])==7
assert lookup['A','crysjepa_refined']['equal_weight_rank']==7
assert lookup['C','crysjepa_refined']['equal_weight_rank']==4

ss=[r for r in results if r['variant']=='S1']
x=[float(r['qc_retention_pct']) for r in ss]
y=[float(r['unique_formula_yield_pct']) for r in ss]
pearson,spearman=corr(x,y),corr(rank_values(x),rank_values(y))

# Verify consistency with the previous audit and the actual current Figure 8D.
old=read(BASE/'audit_2026-11-09/scenario_results_source_precision.csv')
for r in old:
    for s in ('S1','S2','S3'):
        z=lookup[s,r['analysis_cohort']]
        close(z['equal_weight_score_source'],r[s+'_equal_weight_score'])
        assert z['equal_weight_rank']==int(r[s+'_equal_weight_rank'])
for r in read(BASE/'hybrid_v2/panel_D_S1_top5_pct.csv'):
    z=lookup['S1',r['analysis_cohort']]
    close(z['top5_pct_exact'],r['top5_pct'])
    assert z['top5_pct_count']==int(r['top5_count'])

with (OUT/'scenario_sensitivity_publication.csv').open('x',encoding='utf-8',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(results[0]))
    writer.writeheader();writer.writerows(results)

def result_table(variant, full):
    text='| Generated set | '+('QC (%) | Unique (%) | Chemical (%) | ' if full else '')+'Pareto | Score | Rank | First (%) | Top-3 (%) | Top-5 (%) |\n'
    text+='|---|'+('---:|---:|---:|' if full else '')+'---|---:|---:|---:|---:|---:|\n'
    for r in results:
        if r['variant']!=variant: continue
        cells=[r['label']]
        if full:
            cells += [rounded(r[k],4) if 0<D(r[k])<D('.01') else rounded(r[k]) for k in definitions[variant]]
        cells += ['Yes' if r['pareto_efficient'] else 'No',r['equal_weight_score_publication'],str(r['equal_weight_rank']),
                  *[r[k+'_exact'] for k in ('first_place_pct','top3_pct','top5_pct')]]
        text+='| '+' | '.join(cells)+' |\n'
    return text

s8='# Table S8. Scenario-specific Pareto efficiency, equal-weight rankings, and ranking sensitivity across generated sets.\n\n'
s8+='Provisional numbering; existing manuscript references are unchanged. FT = Fine-tuned. All yields use the nominal budget Ngen = 2000 and contributions from QC-retained structures. Unique = unique reduced-formula yield, not within-QC uniqueness. Chemical = S1: 3d atomic-content yield; S2: configured-lanthanide atomic-content yield; S3: configured 3d/lanthanide union-presence yield (OR). Scores are the mean of three independently min-max-normalized criteria across all ten sets; rank 1 is best. Frequencies are exact to 0.005 percentage points from 20000 Dirichlet(1,1,1) weights, seed 1984, and are shown with three decimals. Pareto refers to all three scenario objectives.\n\n'
for s in ('S1','S2','S3'):
    s8+=f'## {s}\n\n'+result_table(s,True)+'\n'
s8+='Figure 8B-C show S1 Pareto/rank sensitivity; Figure 8D shows S1 Top-5 only. S2/S3 frequencies are reported here. Full source-precision scores and integer counts are in `scenario_sensitivity_publication.csv`.\n'
save('table_s8_scenario_results.md',s8)

s9='# Table S9. Alternative chemical criteria and QC-retention ablation.\n\nProvisional numbering. This separate table keeps Table S8 readable. Scores are dimensionless, normalized within each criterion across the same ten sets. Scores under different criterion systems are not directly comparable as performance gains. Frequencies use 20000 saved weights and seed 1984, with Dirichlet(1,...,1) dimension equal to the number of criteria.\n\n'
for v in ('A','B','C','S1-2D','S2-2D','S3-2D'):
    names={'qc_retention_pct':'QC retention','unique_formula_yield_pct':'unique-formula yield',
           '3d_containing_yield_pct':'3d-containing yield','lanthanide_containing_yield':'configured-lanthanide-containing yield',
           '3d_atomic_content_yield':'3d atomic-content yield','lanthanide_atomic_content_yield':'configured-lanthanide atomic-content yield',
           'configured_3d_lanthanide_union_yield':'configured 3d/lanthanide union-presence yield (OR)'}
    titles={'A':'S9A. Original presence-based criteria (A)','B':'S9B. Four presence-based criteria (B)',
            'C':'S9C. Four criteria including both atomic-content yields (C)',
            'S1-2D':'S9D. S1 without the separate QC-retention objective',
            'S2-2D':'S9E. S2 without the separate QC-retention objective',
            'S3-2D':'S9F. S3 without the separate QC-retention objective'}
    s9+=f'## {titles[v]}\n\nObjectives: '+'; '.join(names[k] for k in definitions[v])+f'.\n\nPareto-efficient sets ({len(fronts[v])}): '+', '.join(fronts[v])+'.\n\n'+result_table(v,False)+'\n'
s9+='For 2D ablation, only the separate QC objective is dropped: unique-formula yield and the scenario chemical yield retain Ngen=2000 and identical values/min-max normalization. QC filtering is not removed. All three scenario Pareto memberships are unchanged. A is the original presence-based three-objective analysis, not the updated atomic-content S1. B adds lanthanide presence to A; C replaces the chemical objectives with both atomic-content yields.\n'
save('table_s9_criteria_ablation.md',s9)

audit='# Scenario sensitivity audit\n\nDate: 2026-11-09. PASS. Existing results and figures were read only. No sampling, training, generation, or ranking-result replacement was performed.\n\n'
audit+=f'## Correlation\n\nAcross the ten generated sets, QC retention versus unique-formula yield: Pearson r = {pearson:.16f}; Spearman rho = {spearman:.16f}. Rounded to three decimals: {pearson:.3f}, {spearman:.3f}. Spearman uses average ranks (there are no ties in these two series). These yields share a structural-retention component: unique yield = QC retention × within-QC uniqueness / 100.\n\n'
audit+='## Pareto-front membership\n\n'
for s in ('S1','S2','S3'):
    audit+=f'- {s}: {len(fronts[s])} sets: '+', '.join(fronts[s])+'. Identical membership after removing the QC objective.\n'
audit+='\nCriterion values for every efficient set (and the remaining sets) are in Table S8 and the publication CSV. All saved pairwise dominance relations and n_dominators were independently reconstructed for all nine variants.\n\n'
audit+='## Ranking sensitivity and rounding\n\nEach rank frequency was converted back to an integer count out of 20000; all saved frequencies match counts within numerical floating-point tolerance. All rank distributions sum to 100% by row and rank column. First/Top-3/Top-5 totals are 100/300/500%. All saved first/Top-3/Top-5 summaries and mean ranks match full distributions. Equal-weight scores/ranks were independently checked from the saved normalized criterion values; no random weights were resampled.\n\n'
audit+='Publication CSV retains source-text precision, exact three-decimal frequencies from integer counts, and two-decimal ROUND_HALF_UP values. At exact decimal ties, binary-float formatting can give inconsistent last digits. The requested S2 Crys-JEPA Refined 25.32% corresponds to exactly 5065/20000 = 25.325%; ROUND_HALF_UP gives 25.33%, whereas half-even gives 25.32%. Tables/section therefore use three decimals to avoid ambiguity. Similarly, 41.825%, 32.515%, 40.825%, 57.025%, and 42.975% are the exact values underlying the other requested rounded frequencies.\n\n'
audit+='## Alternative criteria: comparison provenance\n\n'
for v in ('A','B','C'):
    r=lookup[v,'crysjepa_refined']
    audit+=f'- {v}: '+', '.join(definitions[v])+f". Pareto size {len(fronts[v])}; Crys-JEPA Refined score {r['equal_weight_score_source']}, rank {r['equal_weight_rank']}.\n"
audit+='\nThe reported 5 -> 7 Pareto expansion and rank 7 -> 4 refer specifically to A -> C. A is not S1: S1 already has six efficient sets. B -> C also expands 5 -> 7 but moves Refined only 5 -> 4. A and B share the same five members. C adds Crys-JEPA Base and Refined to A. Full scores/ranks/frequencies/membership for A/B/C are in Table S9 and the CSV.\n\n'
audit+='## QC ablation\n\n'
for s in ('S1','S2','S3'):
    for v in (s,s+'-2D'):
        leaders=[r for r in results if r['variant']==v and r['equal_weight_rank']==1]
        r=leaders[0]
        audit+=f"- {v} equal-weight leader: {r['label']}; score {r['equal_weight_score_source']}; first-place frequency {r['first_place_pct_exact']}%.\n"
audit+='\nFor S3, MatterGen Base rises from rank 2 (score 0.8779640505517192, first 42.975%) to rank 1 (0.8755530973451328, first 57.390%); Con-CDVAE Base moves from rank 1 (0.8874429223744292, first 57.025%) to rank 2 (0.8311643835616438, first 42.610%). Removal of the QC objective changes weights and scores, but does not remove QC filtering or the QC dependence embedded in the two remaining yields. Full ablation results for all ten sets are in Table S9 and CSV.\n\n'
audit+='## Figure and text consistency\n\nThe current hybrid_v2 Figure 8B-D show S1 only; D is Top-5, not first-place frequency. Its saved D counts match S1 exactly. S2, S3 and ablation results are cited to provisional Tables S8/S9. The original full Sections 3.7.2-3.7.4 were not provided; consolidation follows the four requested scientific parts, without claiming line-by-line preservation. The previous 3.7.1 text is not repeated. Chemical proxies do not establish magnetism.\n\n## Sources and checks\n\n'
for path in source_hashes:
    audit+=f'- `{path}`\n'
audit+='- Methodology: `scripts/analysis/build_paper_figure08.py` (criterion definitions, min-max normalization, independent seed reset 1984 for each variant, stable cohort-order tie rule).\n\nAll nine variants (90 cohort/variant records), 900 pairwise dominance entries, and all 900 rank-frequency entries passed consistency checks. No analysis was missing. Thus no sensitivity analysis had to be reproduced.\n'
save('scenario_sensitivity_audit.md',audit)

protected=[*BASE.glob('*.csv'),*sorted((ROOT/'paper/figures').glob('*'))]
for path in protected:
    if path.is_file():source_hashes[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
save('source_manifest.json',json.dumps(dict(status='PASS',pearson=pearson,spearman=spearman,
     pareto_fronts=fronts,criteria=definitions,source_sha256=source_hashes),indent=2))
print(json.dumps(dict(pearson=pearson,spearman=spearman,fronts=fronts),indent=2))
print('PASS: 9 variants; 90 scores/ranks; 900 dominance entries; 900 rank-frequency entries.')
