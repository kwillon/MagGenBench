"""Rebuild only publication text layers from audited canonical vector snapshots."""
import argparse
import json
from pathlib import Path
import sys
import subprocess
import hashlib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from mvpipeline.analysis.typography import restyle_pdf_typography
from mvpipeline.analysis.figure6_layout import polish_figure6_bar_layout


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',type=Path,default=ROOT/'reproduced/figure_typography/before')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'reproduced/figure_typography/after')
    parser.add_argument('--source-from-git',action='store_true',help='Read the audited pre-typography canonical PDFs from the pinned Git revision')
    parser.add_argument('--baseline-commit',default='51241b340b3ae95751d193b5c4bead0f71532746')
    args=parser.parse_args();results=[]
    if args.source_from_git:
        args.source_dir=ROOT/'reproduced/figure_typography/source_from_git'
        args.source_dir.mkdir(parents=True,exist_ok=True)
        for canonical in sorted((ROOT/'paper/figures').glob('*.pdf')):
            if canonical.name.startswith('fig01'):continue
            data=subprocess.check_output(['git','show',args.baseline_commit+':paper/figures/'+canonical.name],cwd=ROOT)
            target=args.source_dir/canonical.name
            if target.exists() and target.read_bytes()!=data:raise RuntimeError(f'Pinned source changed: {target}')
            if not target.exists():target.write_bytes(data)
    if len(list(args.source_dir.glob('*.pdf')))!=8:raise RuntimeError('Expected all eight audited publication PDFs, excluding Figure 1')
    for source in sorted(args.source_dir.glob('*.pdf')):
        if source.name.startswith('fig01'):continue
        target=args.output_dir/source.name
        text_target=target.with_suffix('.text.pdf') if source.name.startswith('fig06') else target
        result=restyle_pdf_typography(source,text_target)
        if source.name.startswith('fig06'):
            result['layout_polish']=polish_figure6_bar_layout(text_target,target)
            result['after_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
            result['graphics_unchanged']=False
            result['scientific_values_unchanged']=True
        results.append(result)
        (args.output_dir/'audit.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        import pymupdf as fitz
        with fitz.open(target) as doc:doc[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(target.with_suffix('.png'))
        print(source.name,result['fonts'],'outside_page',len(result['outside_page']),flush=True)


if __name__=='__main__':main()
