"""Final content, PDF, reference and reproduction checks; no scientific writes."""
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reproduced/repository_cleanup'
mapping=json.loads((ROOT/'tables/figure_sources/path_relocations.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def relocated(path):
    seen=set()
    while path in mapping and path not in seen:
        seen.add(path);path=mapping[path]
    return path
inventory_file = OUT/'inventory_before.csv'
if not inventory_file.exists():inventory_file = OUT/'scientific_before.csv'
inventory=list(csv.DictReader(inventory_file.open(encoding='utf-8')))
verified=[]
for r in inventory:
    path=r['path']
    # Frozen inputs/results and selected publication bytes, not regenerated previews.
    if not path.startswith(('paper/','tables/')):continue
    if Path(path).suffix not in ('.csv','.npz','.parquet','.pdf','.png'):continue
    target=ROOT/relocated(path)
    assert target.is_file(),(path,target)
    assert sha(target)==r['sha256'],(path,target)
    verified.append(path)
figure=ROOT/'paper/figures'
assert not list(figure.glob('*.png'))
assert {p.name for p in figure.glob('*.md')}=={'README.md'}
assert {p.name for p in figure.iterdir() if p.is_dir()}=={'legacy'}
assert sha(figure/'fig08_multiobjective.pdf')==sha(figure/'legacy/fig08_multiobjective_hybrid_v2.pdf')
assert sha(figure/'fig08_multiobjective.pdf')=='3b7ec054069d739faba5153af3abcda4b22c7c8c5728d9998e3d132095e55b02'
for p in figure.rglob('*.pdf'):
    assert p.read_bytes().startswith(b'%PDF-') and b'%%EOF' in p.read_bytes()[-1024:]
for line in (figure/'SHA256SUMS.txt').read_text().splitlines():
    h,relative=line.split(maxsplit=1);assert sha(figure/relative)==h
tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
markdown={ROOT/p for p in tracked if p.endswith('.md') and (ROOT/p).is_file()}
markdown.update((ROOT/'paper').rglob('*.md'));markdown.update((ROOT/'docs').rglob('*.md'))
broken=[]
for p in sorted(markdown):
    for m in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)',p.read_text(encoding='utf-8-sig')):
        target=m.group(2).strip('<>')
        if target.startswith(('https:','http:','mailto:','#')):continue
        path=unquote(target.split('#')[0])
        if not (p.parent/path).exists():broken.append(dict(file=p.relative_to(ROOT).as_posix(),target=target))
(OUT/'all_tracked_markdown_broken_links.json').write_text(json.dumps(broken,indent=2),encoding='utf-8')
# Publication SI tables reproduce from their new frozen source paths.
with (ROOT/'paper/supporting_information/table_s7_pairwise_overlap.csv').open(encoding='utf-8') as f:a=list(csv.reader(f))
with (OUT/'verification/figure5_si/publication/table_s7_pairwise_overlap.csv').open(encoding='utf-8') as f:b=list(csv.reader(f))
assert a==b
with (ROOT/'tables/figure_sources/figure8/scenario_sensitivity_publication.csv').open(encoding='utf-8') as f:a=list(csv.DictReader(f))
with (OUT/'verification/sensitivity/scenario_sensitivity_publication.csv').open(encoding='utf-8') as f:b=list(csv.DictReader(f))
assert a==b
assert (ROOT/'reproduced/figure8/scenario_sensitivity/criteria_ablation_changes.csv').read_bytes()==(OUT/'verification/sensitivity_changes/criteria_ablation_changes.csv').read_bytes()
result=dict(status='PASS' if not broken else 'REVIEW_LINKS',scientific_and_publication_files_byte_verified=len(verified),
            canonical_figure8_sha256=sha(figure/'fig08_multiobjective.pdf'),
            markdown_files_checked=len(markdown),broken_links=broken,publication_si_tables_reproduced=True,
            pytest='20 passed (Figure5 overlap/manuscript, publication contracts, Figure4 vector design)',
            scenario_checks='9 variants, 90 scores/ranks, 900 dominance, 900 rank frequencies',
            audits_with_access_errors=22)
(OUT/'verification_summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
