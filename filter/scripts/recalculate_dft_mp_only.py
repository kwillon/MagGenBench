#!/usr/bin/env python3
"""Re-evaluate historical DFT candidates against MP-only filter scores.

Original DFT calculations and source-to-SHA maps are not changed. The join is
by (generator dataset, original CIF SHA256), not by old filenames or old
pred_ordering. A complete 324/324 match is required by default.

Files expected in the same directory as this script:
    dft_fm_source_map.csv     324 DFT candidates, generated from original results
    dft_afm_source_map.csv     60 AFM/FM comparisons, overlapping the 324

MP-only score file:
    results/mp_only/generator_scores.csv

Outputs, under results/mp_only/dft_validation/:
    dft_joined_mp_only.csv
    dft_confirmation_by_generator.csv
    dft_confirmation_by_pipeline_class.csv
    dft_afm_ground_states_mp_only.csv
    unmatched_dft_candidates.csv
    fig2D_dft_confirmation_mp_only.png, .pdf
    dft_confirmation_by_pipeline_class.png, .pdf
    dft_validation_audit.json

IMPORTANT: This historical DFT cohort was selected using the old filter and
is NOT a new independent or representative sample of generated structures.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

COL = 'magnetic_reference_vs_NM_contrast'
MODELS = ['mattergen_base', 'concdvae_base', 'crystalformer', 'crystalllm']
LABELS = {
    'mattergen_base': 'MatterGen base',
    'concdvae_base': 'ConcDVAE base',
    'crystalformer': 'CrystalFormer',
    'crystalllm': 'CrystALLM base',
}
COLORS = {
    'mattergen_base': '#9DAA90',
    'concdvae_base': '#E1B15A',
    'crystalformer': '#DD8B63',
    'crystalllm': '#B84D45',
}


def require(df: pd.DataFrame, cols: set[str], what: str):
    absent = cols - set(df.columns)
    if absent:
        raise ValueError(f'{what} missing columns: {sorted(absent)}')


def wilson(k: int, n: int, z: float = 1.959963984540054):
    if n == 0:
        return np.nan, np.nan
    p = k / n
    den = 1 + z*z / n
    center = (p + z*z/(2*n)) / den
    half = z * np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return max(0., float(center - half)), min(1., float(center + half))


def style():
    plt.rcParams.update({
        'font.family': 'DejaVu Sans',
        'font.size': 9, 'axes.labelsize': 9, 'xtick.labelsize': 8,
        'ytick.labelsize': 8, 'axes.titlesize': 10,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.grid': False,
        'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'pdf.fonttype': 42, 'ps.fonttype': 42,
    })


def read_scores(scores_path: Path, manifests_dir: Path):
    d = pd.read_csv(scores_path, low_memory=False)
    require(d, {'dataset', 'structure_id', COL, 'nearest_magnetic_reference_branch'}, 'MP-only scores')
    d['dataset'] = d['dataset'].astype(str).str.strip().str.lower()
    d['structure_id'] = d['structure_id'].astype(str).str.strip()
    if 'score_status' in d:
        d = d.loc[d['score_status'].astype(str).eq('ok')].copy()
    d[COL] = pd.to_numeric(d[COL], errors='coerce')
    if not np.isfinite(d[COL].to_numpy(float)).all():
        raise ValueError('Non-finite contrasts in successfully scored rows')
    d['nearest_magnetic_reference_branch'] = (
        d['nearest_magnetic_reference_branch'].astype(str).str.strip()
        .replace({'FIM': 'FiM', 'fim': 'FiM'})
    )
    if not set(d['nearest_magnetic_reference_branch']).issubset({'AFM', 'FM', 'FiM'}):
        raise ValueError('Scores must be from the MP-only AFM/FM/FiM/NM model, not MAGNDATA')

    if 'sha256' not in d or d['sha256'].isna().any():
        # Fallback: the reorganization step records hashes in each generator manifest.
        parts = []
        for dataset in MODELS:
            p = manifests_dir / dataset / 'manifest.csv'
            if not p.exists():
                continue
            m = pd.read_csv(p, dtype=str)
            require(m, {'cif_id','sha256'}, str(p))
            m = m[['cif_id','sha256']].copy()
            m['dataset'] = dataset
            m = m.rename(columns={'cif_id': 'structure_id', 'sha256': 'sha_manifest'})
            parts.append(m)
        if not parts:
            raise FileNotFoundError('Scores lack sha256, and generator manifests not found in '+str(manifests_dir))
        m = pd.concat(parts, ignore_index=True)
        if m.duplicated(['dataset','structure_id']).any():
            raise ValueError('Duplicate dataset/structure_id in generator manifests')
        d = d.merge(m, on=['dataset','structure_id'], how='left', validate='many_to_one')
        if 'sha256' in d:
            d['sha256'] = d['sha256'].fillna(d.pop('sha_manifest'))
        else:
            d['sha256'] = d.pop('sha_manifest')
    require(d, {'sha256'}, 'scores after manifest join')
    d['sha256'] = d['sha256'].astype('string').str.strip().str.lower()
    if d['sha256'].isna().any():
        raise ValueError(f'{d["sha256"].isna().sum()} scored rows lack SHA256')
    d = d.loc[d['dataset'].isin(MODELS)].copy()
    if d.duplicated(['dataset','sha256']).any():
        # Hash-identical structures can genuinely occur; they cannot be joined
        # one-to-one unless scores are identical. Do not select arbitrarily.
        repeated = d.loc[d.duplicated(['dataset','sha256'], keep=False)].copy()
        if repeated.groupby(['dataset','sha256'])[COL].nunique().gt(1).any():
            raise ValueError('Identical CIF hashes have conflicting contrasts')
        d = d.drop_duplicates(['dataset','sha256'], keep='first')
    return d


def build_join(mapping: pd.DataFrame, scores: pd.DataFrame):
    require(mapping, {'dataset','sha256','folder','is_magnetic'}, 'DFT source map')
    m = mapping.copy()
    m['dataset'] = m['dataset'].astype(str).str.strip().str.lower()
    m['sha256'] = m['sha256'].astype(str).str.strip().str.lower()
    if len(m) != 324 or m.duplicated(['dataset','sha256']).any():
        raise ValueError('Expected 324 unique (dataset, SHA256) original DFT records')
    flags = m['is_magnetic'].astype(str).str.strip().str.lower()
    if not flags.isin(['yes','no']).all():
        raise ValueError('DFT is_magnetic must be yes or no')
    m['dft_is_magnetic'] = flags.eq('yes').astype(int)

    keep = [c for c in [
        'dataset','sha256','structure_id','formula_reduced',COL,
        'nearest_magnetic_reference_branch','nearest_reference_branch','score_status'
    ] if c in scores.columns]
    s = scores[keep].copy().rename(columns={'structure_id':'mp_structure_id'})
    if 'formula_reduced' in s:
        s = s.rename(columns={'formula_reduced':'mp_formula_reduced'})
    return m.merge(s, on=['dataset','sha256'], how='left', validate='one_to_one', indicator=True)


def summarize(joined: pd.DataFrame):
    d = joined.copy()
    d['MP_pipeline_class'] = np.where(d[COL].gt(0), 'Magnetic-like', 'NM-like')
    rows=[]
    for dataset in MODELS:
        g=d[d.dataset.eq(dataset)]
        selected=g[g['MP_pipeline_class'].eq('Magnetic-like')]
        n=len(selected); k=int(selected['dft_is_magnetic'].sum())
        lo,hi=wilson(k,n)
        rows.append({'dataset':dataset,'n_dft_all':len(g),
                     'n_pipeline_magnetic_like':n,'n_DFT_magnetic_in_selected':k,
                     'confirmation_fraction':k/n if n else np.nan,
                     'ci95_low':lo,'ci95_high':hi})
    per_model=pd.DataFrame(rows)
    overall=[]
    for label in ['Magnetic-like','NM-like']:
        g=d[d.MP_pipeline_class.eq(label)]
        n=len(g); k=int(g['dft_is_magnetic'].sum())
        lo,hi=wilson(k,n)
        overall.append({'MP_pipeline_class':label,'n':n,
                        'n_DFT_magnetic':k,'fraction_DFT_magnetic':k/n if n else np.nan,
                        'ci95_low':lo,'ci95_high':hi})
    return d, per_model, pd.DataFrame(overall)


def save(fig, path: Path, dpi: int):
    fig.savefig(path.with_suffix('.png'), dpi=dpi,
                bbox_inches='tight', pad_inches=0.08, facecolor='white')
    fig.savefig(path.with_suffix('.pdf'),
                bbox_inches='tight', pad_inches=0.08, facecolor='white')
    plt.close(fig)


def draw_generator_dft(stats: pd.DataFrame, output: Path, dpi: int):
    style()
    fig,ax=plt.subplots(figsize=(8.2,4.8))
    fig.subplots_adjust(left=0.22,right=0.965,bottom=0.18,top=0.97)
    data=stats.set_index('dataset').loc[MODELS]
    y=np.arange(len(MODELS))
    vals=data['confirmation_fraction'].to_numpy(float)
    ok=np.isfinite(vals)
    if ok.any():
        ax.barh(y[ok], vals[ok], color=[COLORS[MODELS[i]] for i in np.where(ok)[0]],
                height=.68, edgecolor='none')
        low=data['ci95_low'].to_numpy(float); high=data['ci95_high'].to_numpy(float)
        ax.errorbar(vals[ok],y[ok],
                    xerr=np.vstack([np.maximum(0,vals[ok]-low[ok]),
                                    np.maximum(0,high[ok]-vals[ok])]),
                    fmt='none',ecolor='#333333',elinewidth=1,capsize=2.5)
    ax.set_yticks(y,[LABELS[x] for x in MODELS])
    ax.invert_yaxis(); ax.tick_params(axis='y',length=0)
    ax.set_xlim(0,1); ax.set_xticks(np.linspace(0,1,6))
    ax.set_xlabel('Fraction confirmed magnetic by DFT')
    ax.xaxis.grid(True,color='#9099A1',alpha=.15,lw=.6)
    ax.set_axisbelow(True)
    save(fig, output/'fig2D_dft_confirmation_mp_only', dpi)


def draw_overall(overall: pd.DataFrame, output: Path, dpi:int):
    style()
    fig, ax=plt.subplots(figsize=(5.2,4.3))
    fig.subplots_adjust(left=.17,right=.96,top=.96,bottom=.18)
    dat=overall.set_index('MP_pipeline_class').loc[['Magnetic-like','NM-like']]
    vals=dat['fraction_DFT_magnetic'].to_numpy(float)
    low=dat['ci95_low'].to_numpy(float);high=dat['ci95_high'].to_numpy(float)
    x=np.arange(2)
    ax.bar(x,vals,color=['#5F7F57','#C7CDD3'],width=.65)
    ok=np.isfinite(vals)
    if ok.any():
        ax.errorbar(x[ok],vals[ok],yerr=np.vstack([vals[ok]-low[ok],high[ok]-vals[ok]]),
                    fmt='none',ecolor='#333333',elinewidth=1,capsize=2)
    ax.set_ylim(0,1);ax.set_xticks(x,['Pipeline\nmagnetic-like','Pipeline\nNM-like'])
    ax.set_ylabel('Fraction magnetic in DFT')
    ax.yaxis.grid(True,color='#9099A1',alpha=.16,lw=.6);ax.set_axisbelow(True)
    save(fig,output/'dft_confirmation_by_pipeline_class',dpi)


def main():
    root=Path(__file__).resolve().parent
    project=Path.cwd()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scores',type=Path,default=project/'results/mp_only/generator_scores.csv')
    p.add_argument('--dft-map',type=Path,default=root.parent/'paper/data/dft_fm_source_map.csv')
    p.add_argument('--afm-map',type=Path,default=root.parent/'paper/data/dft_afm_source_map.csv')
    p.add_argument('--manifests-dir',type=Path,default=project/'data/generators')
    p.add_argument('--output-dir',type=Path,default=project/'results/mp_only/dft_validation')
    p.add_argument('--dpi',type=int,default=600)
    p.add_argument('--allow-partial',action='store_true',help='Produce exploratory results even if some DFT structures are unmatched')
    args=p.parse_args()
    out=args.output_dir;out.mkdir(parents=True,exist_ok=True)
    scores=read_scores(args.scores,args.manifests_dir)
    mapping=pd.read_csv(args.dft_map,low_memory=False)
    joined=build_join(mapping,scores)
    missing=joined.loc[joined['_merge'].ne('both')].copy()
    missing.to_csv(out/'unmatched_dft_candidates.csv',index=False)
    audit={'dft_original_count':int(len(mapping)),
           'matched_count':int(len(joined)-len(missing)),
           'unmatched_count':int(len(missing)),
           'model_classes':['AFM','FM','FiM','NM'],
           'source_scores':str(args.scores.resolve()),
           'source_dft_map':str(args.dft_map.resolve()),
           'historical_cohort':True,
           'selection_bias_warning':'DFT structures were chosen using an older magnetic-reference filter; results conditional on historical selected cohort.'}
    (out/'dft_validation_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print('SHA256 matches:',len(joined)-len(missing),'/',len(joined))
    if len(missing) and not args.allow_partial:
        raise SystemExit('Some DFT structures not found in MP-only scores. See unmatched_dft_candidates.csv. No potentially misleading figures generated. Add --allow-partial only for diagnostic analysis.')
    good=joined.loc[joined['_merge'].eq('both')].drop(columns=['_merge']).copy()
    if not len(good):
        raise SystemExit('No DFT candidates matched MP-only scored structures')
    good, by_model, overall=summarize(good)
    good.to_csv(out/'dft_joined_mp_only.csv',index=False)
    by_model.to_csv(out/'dft_confirmation_by_generator.csv',index=False)
    overall.to_csv(out/'dft_confirmation_by_pipeline_class.csv',index=False)

    afm=pd.read_csv(args.afm_map)
    require(afm,{'dataset','sha256','ground_state','dE_per_atom_meV'},'AFM source map')
    if len(afm)!=60 or afm.duplicated(['dataset','sha256']).any():
        raise ValueError('Expected 60 unique AFM-vs-FM historical calculations')
    afm=afm.merge(good[['dataset','sha256',COL,'MP_pipeline_class','nearest_magnetic_reference_branch']],
                  on=['dataset','sha256'],how='left',validate='one_to_one',indicator=True)
    afm.to_csv(out/'dft_afm_ground_states_mp_only.csv',index=False)
    print('\nDFT magnetic fraction for MP-only pipeline classes:\n',overall.to_string(index=False))
    print('\nBy generator:\n',by_model.to_string(index=False))
    print('\nAFM subset matched:',int(afm['_merge'].eq('both').sum()),'/',len(afm))
    draw_generator_dft(by_model,out,args.dpi)
    draw_overall(overall,out,args.dpi)
    print('\nOutput:',out.resolve())
    print('Note: the historical DFT cohort was selected by the previous model; interpret as external electronic-structure evidence for a re-scored cohort, not a new unbiased DFT test set.')

if __name__=='__main__':
    main()
