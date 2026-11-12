"""Audit selected Figure 4/S1-S4, archives and unrelated protected files."""
from pathlib import Path
import hashlib
import io
import json
import re
import subprocess
import sys
from collections import Counter

import pymupdf as fitz
from fontTools.ttLib import TTFont

ROOT=Path(__file__).resolve().parents[2]
FIGURES=ROOT/'paper/figures'
BASELINE='7ca61b64858134c2dbc72bbec0a7bcef21893473'
sys.path.insert(0,str(ROOT/'src'))
from mvpipeline.analysis.typography import _drawing_signature, _image_signature, _numeric_tokens


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_bytes(path):
    return subprocess.check_output(['git','show',BASELINE+':'+path],cwd=ROOT)


def main():
    # Check untouched publication figures and every SI file against the baseline, except
    # the explicitly pre-existing working-tree edit, checked by its initial hash.
    protected = subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE,'paper/figures','paper/supporting_information'],cwd=ROOT,text=True).splitlines()
    protected=[p for p in protected if p.startswith('paper/supporting_information/') or p.endswith('.pdf')]
    changed={'paper/figures/fig04_magnetic_reference_dft.pdf','paper/figures/supp02_descriptor_space.pdf',
             'paper/figures/supp01_pca_loadings.pdf'}
    user_table='paper/supporting_information/table_s7_pairwise_overlap.csv'
    for name in protected:
        if name in changed or name==user_table:
            continue
        current,baseline=(ROOT/name).read_bytes(),git_bytes(name)
        if not name.endswith('.pdf'):
            current,baseline=current.replace(b'\r\n',b'\n'),baseline.replace(b'\r\n',b'\n')
        assert current==baseline,name
    assert sha(ROOT/user_table)=='64e6f2424a20c1ec4b5513f9cdb2fcb1c5147caf38e0e04bbc7778daa86e4495'
    for old,current in [('fig04_magnetic_reference_dft.pdf','legacy/fig04_magnetic_reference_dft_before_coauthor_update.pdf'),
                        ('supp02_descriptor_space.pdf','supp01_descriptor_space_ten_sets.pdf'),
                        ('supp01_pca_loadings.pdf','legacy/supp00_pca_loadings.pdf')]:
        assert (FIGURES/current).read_bytes()==git_bytes('paper/figures/'+old)

    for source,target in [(FIGURES/'legacy/descriptor_space_pca.pdf',FIGURES/'supp02_descriptor_space.pdf')]:
        before,after=fitz.open(source),fitz.open(target)
        assert before[0].rect==after[0].rect
        assert _drawing_signature(before[0])==_drawing_signature(after[0])
        assert _image_signature(before[0])==_image_signature(after[0])
        assert _numeric_tokens(before[0].get_text())==_numeric_tokens(after[0].get_text())
        # Exact non-whitespace character multisets also preserve all axis wording.
        normalize=lambda text: Counter(re.sub(r'\s','',text))
        assert normalize(before[0].get_text())==normalize(after[0].get_text())

    # Figure 4 is now native Matplotlib: check its frozen data against source
    # vectors, and its new titles directly, rather than demanding old text paths.
    import pandas as pd
    from plot_figure4_publication import source_layout, ORDER, DFT_ORDER, TITLES
    data=ROOT/'tables/figure_sources/figure4'
    stat=pd.read_csv(data/'figure_statistics.csv').set_index('dataset').loc[list(ORDER)]
    for row in pd.read_csv(data/'selected_artwork_statistics_readback.csv').itertuples():
        if row.panel in ('A','B','C') and row.metric in stat.columns:
            stat.loc[row.dataset,row.metric]=row.original_pdf_readback
    dft=pd.read_csv(data/'Figure4D_summary.csv').set_index('dataset').loc[list(DFT_ORDER)]
    source_layout(stat,dft)

    selected=['fig04_magnetic_reference_dft.pdf','supp01_descriptor_space_ten_sets.pdf',
              'supp02_descriptor_space.pdf','supp03_reference_space_validation.pdf',
              'supp04_magnetic_branch_agreement.pdf']
    out=ROOT/'reproduced/figure4_supp_update/final'
    out.mkdir(parents=True,exist_ok=True)
    report={}
    for name in selected:
        doc=fitz.open(FIGURES/name)
        assert len(doc)==1
        page=doc[0]
        for f in page.get_fonts():
            base,_,_,data=doc.extract_font(f[0])
            assert 'Ebrima' in base and 'Bold' not in base and data
            with TTFont(io.BytesIO(data)) as font:
                assert font['OS/2'].usWeightClass==400
        panels=[]
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                for s in line['spans']:
                    assert page.rect.contains(fitz.Rect(s['bbox'])),(name,s)
                    if s['text'] in list('ABCD') and s['size']>=12:
                        assert not (s['flags']&16)
                        assert abs(s['size']-14.5)<.01
                        panels.append(s['text'])
                    elif name=='fig04_magnetic_reference_dft.pdf' and s['text'] in [f'{k}  {t}' for k,t in zip('ABCD',TITLES)]:
                        assert not (s['flags']&16) and abs(s['size']-14.5)<.01
                        panels.append(s['text'][0])
        expected={'fig04_magnetic_reference_dft.pdf':list('ABCD'),
                  'supp02_descriptor_space.pdf':list('ABC'),
                  'supp03_reference_space_validation.pdf':list('AB')}.get(name,[])
        assert panels==expected,(name,panels)
        page.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(out/(Path(name).stem+'.png'))
        report[name]={'sha256':sha(FIGURES/name),'panel_letters':panels,'regular_ebrima_embedded':True}
    rows=''.join(sha(p)+'  ./'+p.relative_to(FIGURES).as_posix()+'\n' for p in sorted(FIGURES.rglob('*.pdf')))
    (FIGURES/'SHA256SUMS.txt').write_text(rows,encoding='utf-8')
    for row in rows.splitlines():
        expected,name=row.split('  ./')
        assert sha(FIGURES/name)==expected
    assert not list(FIGURES.glob('*.png'))
    (out/'verification.json').write_text(json.dumps({'status':'PASS','selected':report,
        'scientific_values_preserved':True,'archives_match_baseline':BASELINE,
        'protected_publication_and_SI_unchanged':True,'pre_existing_SI_edit_preserved':True},indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
