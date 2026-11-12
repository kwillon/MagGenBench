"""Reproduce the supplied Figure 4 and selected S2-S4; never promote implicitly.

Run from the repository root. Outputs default to reproduced/figure4_supp_update/build.
The external coauthor script is kept byte-for-byte intact.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from mvpipeline.analysis.typography import (
    apply_ebrima_typography, ebrima_font_path, fix_ebrima_to_unicode,
    restyle_pdf_typography,
)


def source_sizes(name, text, old):
    # Do not enlarge mathematical subscripts that happen to be a panel letter.
    return 14.5 if text in ('A','B','C','D') and old >= 12 else old


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'reproduced/figure4_supp_update/build')
    parser.add_argument('--figure4-only', action='store_true',
                        help='Render current Figure 4 natively with panel subtitles; leave supplementary figures alone')
    parser.add_argument('--verify-reference-counts', action='store_true',
                        help='Independently recompute frozen counts using MP-only LOO scoring; no refit')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.figure4_only:
        from plot_figure4_publication import combined_figure
        combined_figure(args.output)
        return
    data = ROOT/'tables/figure_sources/figure4'
    spec = importlib.util.spec_from_file_location('coauthor', ROOT/'scripts/analysis/external/plot_figures_maggenbench.py')
    coauthor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(coauthor)
    import numpy as np
    import pandas as pd
    import pymupdf as fitz
    from fontTools.ttLib import TTFont
    from matplotlib.text import Text
    from matplotlib.font_manager import FontProperties

    # Assemble the coauthor's expected input bundle without duplicating the DFT source.
    bundle = args.output/'inputs'
    bundle.mkdir(exist_ok=True)
    for name in ('figure_statistics.csv','reference_confusion_counts.csv','branch_confusion_counts.csv'):
        shutil.copyfile(data/name,bundle/name)
    shutil.copyfile(ROOT/'tables/figure_sources/DFT_figure4D_updated.csv',bundle/'DFT_figure4D_updated.csv')
    stat,dft,ref,branch = coauthor.read_inputs(bundle)
    dftsum = coauthor.dft_summary(dft)
    dftsum.to_csv(args.output/'Figure4D_summary.csv')

    if args.verify_reference_counts:
        sys.path.insert(0,str(ROOT/'filter/src'))
        from cifmagfilter.reference import score_reference_training
        model = np.load(ROOT/'filter/src/cifmagfilter/data/model/reference_filter.npz')
        labels = ['AFM','FM','FiM','NM']
        X = np.vstack([model['ref_'+k] for k in labels])
        y = pd.Series(np.repeat(labels,[len(model['ref_'+k]) for k in labels]))
        scored = score_reference_training(pd.DataFrame({'label_order':y}),X,y,labels,labels[:3],k=15)
        for expected,column in ((ref,'nearest_reference_branch'),(branch,'nearest_magnetic_reference_branch')):
            subset = scored[scored.label_order.isin(expected.index)]
            actual = pd.crosstab(subset.label_order,subset[column]).reindex(index=expected.index,columns=expected.columns,fill_value=0)
            np.testing.assert_array_equal(actual.to_numpy(),expected.to_numpy())

    audits = []
    from plot_figure4_publication import combined_figure
    combined_figure(args.output)
    for source,name in ((ROOT/'paper/figures/legacy/descriptor_space_pca.pdf','supp02_descriptor_space.pdf'),):
        audits.append(restyle_pdf_typography(source,args.output/name,
                      figure_name='supplied_'+name,text_transform=lambda text:text,font_size=source_sizes))

    coauthor.configure()
    apply_ebrima_typography()
    font = ebrima_font_path()
    def publication_save(fig, output, name, dpi):
        fig.canvas.draw()
        for artist in fig.findobj(match=Text):
            size = 14.5 if artist.get_text() in ('A','B') else artist.get_fontsize()
            artist.set_fontproperties(FontProperties(fname=str(font),size=size,weight='normal'))
        canonical = {'Figure_S3':'supp03_reference_space_validation',
                     'Figure_S4':'supp04_magnetic_branch_agreement'}[name]
        fig.savefig(output/(canonical+'.pdf'),bbox_inches='tight',pad_inches=.16)
        coauthor.plt.close(fig)
        with fitz.open(output/(canonical+'.pdf')) as doc:
            fix_ebrima_to_unicode(doc)
            doc.save(output/(canonical+'_unicode.pdf'),garbage=4,deflate=True)
        (output/(canonical+'_unicode.pdf')).replace(output/(canonical+'.pdf'))
    coauthor.save = publication_save
    coauthor.figureS3(ref,args.output,160)
    coauthor.figureS4(branch,args.output,160)

    checks = {}
    selected = [ROOT/'paper/figures/supp01_descriptor_space_ten_sets.pdf'] + sorted(args.output.glob('*.pdf'))
    for path in selected:
        doc = fitz.open(path)
        assert len(doc)==1
        page = doc[0]
        for f in page.get_fonts():
            base,ext,_,blob=doc.extract_font(f[0])
            assert 'Ebrima' in base and 'Bold' not in base and blob
            with TTFont(io.BytesIO(blob)) as face:
                assert face['OS/2'].usWeightClass==400
        assert all(page.rect.contains(fitz.Rect(s['bbox'])) for b in page.get_text('dict')['blocks']
                   for line in b.get('lines',[]) for s in line['spans'])
        page.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(args.output/(path.stem+'.png'))
        checks[path.name] = {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                             'fonts': [f[3] for f in page.get_fonts()], 'pages':len(doc)}
    report = {'typography':audits, 'files':checks,
              'reference_counts_verified':args.verify_reference_counts,
              'dft_confirmation':dftsum.reset_index().to_dict(orient='records')}
    (args.output/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'status':'PASS','files':list(checks),'reference_counts_verified':args.verify_reference_counts},indent=2))


if __name__=='__main__':
    main()
