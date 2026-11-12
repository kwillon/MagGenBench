#!/usr/bin/env python3
"""Rebuild Figure 4 (A-D), Figure S3 and Figure S4 of MagGenBench.

Input data are included in data/; exports PNG and vector PDF to output/.
Dependencies: numpy, pandas, matplotlib. No VASP, CIF parser or repo checkout needed.

Run: python plot_figures.py
Optional: python plot_figures.py --output /path/to/output --dpi 400
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parent
COLORS = {
    'mattergen_base': '#9DAA90', 'mattergen_finetuned': '#4F6B46',
    'concdvae_base': '#E1B15A', 'concdvae_finetuned': '#C05C17',
    'crysjepa_base': '#8CA5AE', 'crysjepa_refined': '#344E68',
    'crystalformer': '#DD8B63', 'crystalformer_finetuned': '#AA5439',
    'crystalllm': '#B84D45', 'crystalllm_finetuned': '#792C47',
}
ORDER = list(COLORS)
LABELS = {
    'mattergen_base': 'MatterGen base', 'mattergen_finetuned': 'MatterGen tuned',
    'concdvae_base': 'Con-CDVAE base', 'concdvae_finetuned': 'Con-CDVAE tuned',
    'crysjepa_base': 'Crys-JEPA base', 'crysjepa_refined': 'Crys-JEPA refined',
    'crystalformer': 'CrystalFormer base', 'crystalformer_finetuned': 'CrystalFormer tuned',
    'crystalllm': 'CrystALLM base', 'crystalllm_finetuned': 'CrystALLM tuned',
}
BRANCHES = ('AFM', 'FM', 'FiM')
BRANCH_COLORS = {'AFM': '#D6A64F', 'FM': '#5F7F57', 'FiM': '#A65A73'}
DFT_ORDER = ('mattergen_base', 'concdvae_base', 'crystalformer', 'crystalllm')
REF_CMAP = LinearSegmentedColormap.from_list(
    'paper_reference', ['#F5F6F4', '#CAD3CB', '#7C9F90', '#3F6A5A'])
INK = '#273540'


def configure():
    plt.rcParams.update({
        'font.family': 'DejaVu Sans', 'font.size': 9.0,
        'axes.labelsize': 9.5, 'xtick.labelsize': 8.2,
        'ytick.labelsize': 8.2, 'legend.fontsize': 8.2,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.facecolor': 'white', 'figure.facecolor': 'white',
        'savefig.facecolor': 'white', 'pdf.fonttype': 42,
        'ps.fonttype': 42,
    })


def read_inputs(data_dir: Path):
    stat = pd.read_csv(data_dir / 'figure_statistics.csv').set_index('dataset').loc[ORDER]
    dft = pd.read_csv(data_dir / 'DFT_figure4D_updated.csv')
    ref = pd.read_csv(data_dir / 'reference_confusion_counts.csv').set_index('known_MP_label')
    branch = pd.read_csv(data_dir / 'branch_confusion_counts.csv').set_index('known_MP_label')
    assert len(dft) == 324 and dft['structure_id'].nunique() == 324, 'DFT records: expected 324 unique structures'
    assert int(stat.n_scored.sum()) == 18485, 'Figure 4 A-C statistics do not match the full screened cohort'
    assert int(ref.to_numpy().sum()) == 8000, 'S3 reference cohort should contain 8,000 structures'
    assert int(branch.to_numpy().sum()) == 6000, 'S4 branch-only cohort should contain 6,000 structures'
    assert (np.abs(dft['max_magmom_uB']) == 0.5).sum() == 0, 'Threshold boundary needs review'
    derived = dft['max_magmom_uB'].abs().gt(0.5)
    assert np.array_equal(derived.to_numpy(), dft['DFT_magnetic_mmax_gt_0p5'].astype(bool).to_numpy())
    assert np.array_equal(dft['magnetic_reference_contrast'].gt(0).to_numpy(),
                          dft['magnetic_like_by_reference'].astype(bool).to_numpy())
    assert int(derived.sum()) == 202
    assert int(dft['magnetic_like_by_reference'].sum()) == 231
    assert int((derived & dft['magnetic_like_by_reference'].astype(bool)).sum()) == 186
    return stat, dft, ref, branch


def ci_wilson(success: int, n: int, z: float = 1.959963984540054):
    p = success / n
    den = 1 + z*z/n
    mid = (p + z*z/(2*n))/den
    half = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return mid-half, mid+half


def dft_summary(dft):
    rows = []
    for ds in DFT_ORDER:
        group = dft[dft.dataset.eq(ds)]
        maglike = group[group['magnetic_like_by_reference'].astype(bool)]
        n = len(maglike)
        k = int(maglike['DFT_magnetic_mmax_gt_0p5'].sum())
        low, high = ci_wilson(k, n)
        rows.append(dict(dataset=ds, n_DFT_total=len(group), n_magnetic_like=n,
                         n_DFT_magnetic=k, confirmation_fraction=k/n,
                         CI95_low=low, CI95_high=high))
    df = pd.DataFrame(rows).set_index('dataset')
    assert list(df.n_magnetic_like) == [55,73,45,58]
    assert list(df.n_DFT_magnetic) == [52,57,27,50]
    return df


def horizontal_axis(ax, keys, y):
    ax.set_yticks(y, [LABELS[k] for k in keys])
    ax.set_ylim(-.8, y[-1]+.8)
    ax.invert_yaxis()
    ax.tick_params(axis='y', length=0, pad=3)
    if len(keys) > 4:
        for i in range(2, len(keys), 2):
            ax.axhline((y[i-1]+y[i])/2, lw=.6, color='#B8C0C4', alpha=.55)
    ax.xaxis.grid(True, lw=.6, color='#9099A1', alpha=.17)
    ax.set_axisbelow(True)


def y_positions(n):
    return np.array([i + .78*(i//2) for i in range(n)], dtype=float)


def panel_a(ax, stat):
    y = y_positions(len(ORDER))
    values = stat.fraction_magnetic_like.to_numpy(float)
    lo, hi = stat.fmag_ci_low.to_numpy(float), stat.fmag_ci_high.to_numpy(float)
    ax.barh(y, values, color=[COLORS[d] for d in ORDER], height=.68)
    ax.errorbar(values, y, xerr=np.vstack([values-lo, hi-values]),
                fmt='none', ecolor='#303030', lw=.9, capsize=2.5, zorder=5)
    horizontal_axis(ax, ORDER, y)
    ax.set_xlim(0, 1.025)
    ax.set_xticks(np.linspace(0,1,6))
    ax.set_xlabel('Fraction closer to magnetic than NM reference')


def panel_b(ax, stat):
    y = y_positions(len(ORDER))
    qq = [stat[f'contrast_q{i}'].to_numpy(float) for i in ('05','25','50','75','95')]
    for j, ds in enumerate(ORDER):
        q05, q25, med, q75, q95 = (v[j] for v in qq)
        c = COLORS[ds]
        ax.plot([q05,q95], [y[j],y[j]], color=c, lw=2.2)
        ax.plot([q25,q75], [y[j],y[j]], color=c, lw=8.0, solid_capstyle='butt')
        ax.plot([med,med], [y[j]-.22,y[j]+.22], color=INK, lw=1.7)
        for val in (q05,q95):
            ax.plot([val,val], [y[j]-.10,y[j]+.10], color=c, lw=1.2)
    ax.axvline(0, color='#666666', lw=.9)
    horizontal_axis(ax, ORDER, y)
    span = max(1.0, float(np.max(qq[-1])-np.min(qq[0])))
    ax.set_xlim(float(np.min(qq[0]))-.06*span, float(np.max(qq[-1]))+.06*span)
    ax.set_xlabel(r'Magnetic-reference contrast, $d_{NM}-d_{mag}$')


def panel_c(ax, stat):
    x = np.arange(len(ORDER))
    bottom = np.zeros(len(ORDER))
    for branch in BRANCHES:
        values = stat[f'branch_{branch}'].to_numpy(float)
        ax.bar(x, values, width=.72, bottom=bottom,
               color=BRANCH_COLORS[branch], label=branch)
        bottom += values
    ax.set_ylim(0,1.025)
    ax.set_xlim(-.55,len(ORDER)-.45)
    ax.set_ylabel('Fraction among magnetic-like candidates')
    ax.set_xticks(x, [LABELS[d] for d in ORDER], rotation=30, ha='right', rotation_mode='anchor')
    ax.tick_params(axis='x', labelsize=7.5)
    ax.yaxis.grid(True, lw=.6, color='#9099A1', alpha=.17)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, ncol=3, loc='lower center', bbox_to_anchor=(.5, 1.02))


def panel_d(ax, dft_by_generator):
    y = np.arange(len(DFT_ORDER))
    d = dft_by_generator.loc[list(DFT_ORDER)]
    values, lo, hi = (d[col].to_numpy(float) for col in
                      ('confirmation_fraction', 'CI95_low', 'CI95_high'))
    ax.barh(y, values, color=[COLORS[ds] for ds in DFT_ORDER], height=.68)
    ax.errorbar(values, y, xerr=np.vstack([values-lo, hi-values]),
                fmt='none', ecolor='#303030', lw=1, capsize=2.4, zorder=5)
    horizontal_axis(ax, DFT_ORDER, y)
    ax.set_xlim(0,1.025)
    ax.set_xticks(np.linspace(0,1,6))
    ax.set_xlabel(r'Fraction with $|m_{max}| > 0.5$ $\mu_B$ in DFT')
    # Intentionally NO n/k counts and NO percentage labels on bars.


def label_panel(ax, letter):
    ax.text(-.067, 1.045, letter, transform=ax.transAxes, fontsize=15,
            fontweight='bold', va='bottom', ha='left', clip_on=False)


def save(fig, output_dir, name, dpi):
    output_dir.mkdir(parents=True, exist_ok=True)
    for ext in ('.png','.pdf'):
        fig.savefig(output_dir / f'{name}{ext}', dpi=dpi,
                    bbox_inches='tight', pad_inches=.16)
    plt.close(fig)


def figure4(stat, dftsum, output, dpi):
    fig = plt.figure(figsize=(17,12))
    gs = fig.add_gridspec(2, 2, left=.115, right=.985,
                          bottom=.14, top=.96, wspace=.32, hspace=.44)
    axes = [fig.add_subplot(gs[i,j]) for i in range(2) for j in range(2)]
    for ax, func, name in zip(axes, (panel_a,panel_b,panel_c,panel_d), 'ABCD'):
        func(ax, dftsum if name=='D' else stat)
        label_panel(ax, name)
    save(fig, output, 'Figure_4', dpi)


def plot_matrix(ax, counts, labels):
    counts = counts.loc[list(labels), list(labels)]
    frac = counts.div(counts.sum(axis=1), axis=0).to_numpy()
    ax.imshow(frac, cmap=REF_CMAP, vmin=0, vmax=1, interpolation='nearest')
    ax.set_xticks(np.arange(len(labels)), labels)
    ax.set_yticks(np.arange(len(labels)), labels)
    ax.set_xlabel('Assigned reference category')
    ax.set_ylabel('Materials Project annotation')
    ax.tick_params(length=0)
    ax.set_xticks(np.arange(-.5,len(labels),1), minor=True)
    ax.set_yticks(np.arange(-.5,len(labels),1), minor=True)
    ax.grid(which='minor', color='white', linewidth=2)
    ax.tick_params(which='minor', bottom=False, left=False)
    for (i,j), v in np.ndenumerate(frac):
        percent = 100 * v
        value = f'{percent:.2f}'.rstrip('0').rstrip('.')+'%'
        ax.text(j,i,value,ha='center',va='center',fontsize=9.6,
                color='white' if v>.55 else INK,
                weight='bold' if i==j else 'normal')
    for spine in ax.spines.values(): spine.set_visible(False)


def figureS3(ref, output, dpi):
    labels = ('AFM','FM','FiM','NM')
    r = ref.loc[list(labels),list(labels)]
    agreement = np.trace(r.to_numpy())/r.to_numpy().sum()
    mag_sensitivity = 1 - r.loc[['AFM','FM','FiM'],'NM'].sum() / r.loc[['AFM','FM','FiM']].to_numpy().sum()
    nm_specificity = r.loc['NM','NM'] / r.loc['NM'].sum()
    balanced = (mag_sensitivity+nm_specificity)/2
    assert abs(agreement-0.762875)<1e-9
    assert abs(balanced-0.9295833333333333)<1e-6
    fig, (a,b) = plt.subplots(1,2,figsize=(13.8,6.1),gridspec_kw={'width_ratios':[1.05,1.1]})
    fig.subplots_adjust(left=.08,right=.985,top=.92,bottom=.15,wspace=.40)
    plot_matrix(a, r, labels)
    names = ('Four-class agreement','Magnetic sensitivity','NM specificity','Binary balanced accuracy')
    vals = np.array([agreement,mag_sensitivity,nm_specificity,balanced])
    y = np.arange(4)
    b.barh(y,vals,color=['#4F6B46','#8CA5AE','#9DAA90','#5F7F57'],height=.53)
    b.set_yticks(y,names)
    b.invert_yaxis()
    b.set_xlim(0,1.02)
    b.set_xticks(np.linspace(0,1,6),[f'{i:.0f}%' for i in np.linspace(0,100,6)])
    b.set_xlabel('Agreement with Materials Project labels')
    b.tick_params(axis='y',length=0)
    b.xaxis.grid(True,color='#9099A1',lw=.6,alpha=.22)
    b.set_axisbelow(True)
    for letter,ax in zip('AB',(a,b)):
        ax.text(-.11,1.07,letter,transform=ax.transAxes,fontsize=15,fontweight='bold',color=INK)
    # No text values on right-panel bars (as requested). Matrix values are retained.
    save(fig,output,'Figure_S3',dpi)


def figureS4(branch, output, dpi):
    labels=('AFM','FM','FiM')
    agreement=np.trace(branch.loc[list(labels),list(labels)].to_numpy())/6000
    assert abs(agreement-0.7518333333333334)<1e-6
    fig,ax=plt.subplots(figsize=(7.2,6.8))
    fig.subplots_adjust(left=.16,right=.92,top=.84,bottom=.15)
    plot_matrix(ax,branch,labels)
    ax.set_title(f'Three-branch agreement: {agreement*100:.2f}%',pad=24,fontsize=14,color=INK)
    save(fig,output,'Figure_S4',dpi)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,default=ROOT/'data')
    parser.add_argument('--output',type=Path,default=ROOT/'output')
    parser.add_argument('--dpi',type=int,default=300)
    args=parser.parse_args()
    configure()
    stat,dft,ref,branch=read_inputs(args.data)
    dftsum=dft_summary(dft)
    args.output.mkdir(parents=True,exist_ok=True)
    dftsum.reset_index().to_csv(args.output/'Figure4D_summary.csv',index=False)
    figure4(stat,dftsum,args.output,args.dpi)
    figureS3(ref,args.output,args.dpi)
    figureS4(branch,args.output,args.dpi)
    print('Completed 3 figures (PNG/PDF):',args.output)
    print(dftsum[['n_DFT_total','n_magnetic_like','n_DFT_magnetic','confirmation_fraction']].to_string())
    print('Figure 4D: 186/231 positive local moments among magnetic-reference candidates')

if __name__=='__main__': main()
