"""Inventory canonical PDF fonts and text without modifying publication files."""
import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

import pymupdf as fitz

ROOT=Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'reproduced/figure_typography/before')
    args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    report={}
    for path in sorted((ROOT/'paper/figures').glob('*.pdf')):
        doc=fitz.open(path)
        spans=[];fonts=[]
        for page in doc:
            for f in page.get_fonts(full=True):
                name,ext,_,content=doc.extract_font(f[0])
                fonts.append(dict(basefont=f[3],resource=f[4],embedded=bool(content),extension=ext))
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines',[]):
                    for span in line['spans']:
                        spans.append(dict(text=span['text'],font=span['font'],size=span['size'],bbox=span['bbox'],origin=span['origin'],direction=line['dir'],color=span['color']))
        entry=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),page_sizes=[list(p.rect) for p in doc],
                   fonts=fonts,text_spans=spans,counts=dict(Counter(s['font'] for s in spans)),
                   sizes=sorted(set(round(s['size'],3) for s in spans)))
        report[path.name]=entry
        # Independent reference files exclude Figure 1, which remains read-only.
        if path.name!='fig01_pipeline.pdf':
            dest=args.output_dir/path.name
            if not dest.exists():shutil.copyfile(path,dest)
        doc[0].get_pixmap(matrix=fitz.Matrix(1.25,1.25)).save(args.output_dir/(path.stem+'.png'))
        print(path.name,entry['counts'],entry['sizes'],flush=True)
    (args.output_dir/'font_inventory.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':main()
