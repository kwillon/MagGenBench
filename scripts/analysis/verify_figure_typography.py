"""Verify typography candidates; optionally promote only fully checked PDFs."""
import argparse
import csv
import hashlib
import io
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pymupdf as fitz
from fontTools.ttLib import TTFont

ROOT=Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-dir',type=Path,default=ROOT/'reproduced/figure_typography/final_check')
    parser.add_argument('--promote',action='store_true')
    parser.add_argument('--previous-candidate-dir',type=Path,help='Permit replacing only the exact previously verified typography revision')
    parser.add_argument('--before-inventory',type=Path,default=ROOT/'reproduced/figure_typography/before/font_inventory.json')
    args=parser.parse_args()
    before=json.loads(args.before_inventory.read_text())
    audits=json.loads((args.candidate_dir/'audit.json').read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert len(audits)==8
    ref=ROOT/'paper/figures/fig01_pipeline.pdf'
    assert sha(ref)==before[ref.name]['sha256']
    changes=[];font_checks={};overlaps=[];char_count=0
    for audit in audits:
        name=audit['figure'];path=args.candidate_dir/name
        assert audit['before_sha256']==before[name]['sha256']
        assert sha(path)==audit['after_sha256']
        assert all(audit[k] for k in ('embedded','images_unchanged','numeric_tokens_unchanged'))
        if audit.get('layout_polish'):
            assert audit['layout_polish']['all_values_order_and_colors_preserved']
            assert audit['layout_polish']['upper_AB_render_identical']
            assert audit['layout_polish']['numeric_tokens_unchanged']
        else:assert audit['graphics_unchanged']
        assert not audit['outside_page']
        doc=fitz.open(path)
        entries=[]
        for page in doc:
            for f in page.get_fonts():
                base,ext,_,data=doc.extract_font(f[0])
                assert 'Ebrima' in base and 'Bold' not in base and data
                with TTFont(io.BytesIO(data)) as font:
                    weight=font['OS/2'].usWeightClass
                assert weight==400
                entries.append(dict(basefont=base,type=f[2],embedded=True,weight=weight))
            spans=page.get_texttrace()
            for i,s in enumerate(spans):
                char_count+=len(s['chars'])
                if not ''.join(chr(c[0]) for c in s['chars']).strip():continue
                r=fitz.Rect(s['bbox'])
                assert page.rect.contains(r), (name, 'Text outside page', r)
                for other in spans[i+1:]:
                    if not ''.join(chr(c[0]) for c in other['chars']).strip():continue
                    q=fitz.Rect(other['bbox']);intersection=r&q
                    if intersection.is_empty:continue
                    small=min(r.get_area(),q.get_area())
                    if small and intersection.get_area()/small>.25:
                        overlaps.append(dict(figure=name,text=''.join(chr(c[0]) for c in s['chars']),
                                             other=''.join(chr(c[0]) for c in other['chars']),fraction=intersection.get_area()/small))
        font_checks[name]=entries
        for c in audit['text_changes']:changes.append(c)
        cmd=shutil.which('pdffonts')
        if cmd:
            result=subprocess.run([cmd,str(path)],capture_output=True,text=True,check=True)
            (args.candidate_dir/(path.stem+'_pdffonts.txt')).write_text(result.stdout,encoding='utf-8')
    unique=Counter((r['figure'],r['original'],r['corrected']) for r in changes)
    with (args.candidate_dir/'text_corrections.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.writer(f);writer.writerow(['figure','original text','corrected text','occurrences'])
        writer.writerows([(*key,count) for key,count in sorted(unique.items())])
    summary=dict(status='PASS',figures=8,reference_sha256=sha(ref),font_checks=font_checks,
                 scientific_values_unchanged=True,
                 layout_adjusted=[a['figure'] for a in audits if a.get('layout_polish')],
                 characters_verified=char_count,
                 overlap_candidates=overlaps,distinct_text_corrections=len(unique))
    (args.candidate_dir/'verification.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print('Fonts/embedding/weight, numeric signatures, data vectors, raster samples and page bounds: PASS')
    print('Overlap candidates:',len(overlaps))
    for item in overlaps[:12]:print(item)
    if args.promote:
        assert not overlaps,'Review text overlap candidates before promotion'
        prior={r['figure']:r['after_sha256'] for r in json.loads((args.previous_candidate_dir/'audit.json').read_text())} if args.previous_candidate_dir else {}
        for audit in audits:
            name=audit['figure'];target=ROOT/'paper/figures'/name
            assert sha(target) in (audit['before_sha256'],prior.get(name)), 'Canonical PDF changed outside the verified typography revisions'
        for audit in audits:
            name=audit['figure'];target=ROOT/'paper/figures'/name
            shutil.copyfile(args.candidate_dir/name,target)
            folder=('figure'+name[3:5].lstrip('0')) if name.startswith('fig') else 'supplementary/figure'+name[4:6].lstrip('0')
            preview=ROOT/'reproduced'/folder/'previews'/(Path(name).stem+'.png')
            preview.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile((args.candidate_dir/name).with_suffix('.png'),preview)
            assert sha(target)==audit['after_sha256']
        figures=ROOT/'paper/figures'
        (figures/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  ./'+p.relative_to(figures).as_posix()+'\n' for p in sorted(figures.rglob('*.pdf'))),encoding='utf-8')
        assert sha(ref)==before[ref.name]['sha256']
        print('Promoted eight verified PDFs. Figure 1 unchanged.')


if __name__=='__main__':main()
