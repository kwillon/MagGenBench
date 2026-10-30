import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path

OUTPUT_DIR = Path('reproduced/figures35_audit')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, 'src')
import numpy as np
import pandas as pd
from matplotlib.cbook import boxplot_stats
from mvpipeline.analysis import manuscript_figure3_v2 as current
from mvpipeline.analysis.manuscript_figure5_v2 import (
    load_paired_predictions, ENERGY, MOMENT,
)

baseline = '9adb8f7f'
old = types.ModuleType('mvpipeline.analysis._baseline_figure3')
old.__package__ = 'mvpipeline.analysis'
sys.modules[old.__name__] = old
source = subprocess.check_output(['git', 'show', baseline + ':src/mvpipeline/analysis/manuscript_figure3_v2.py'])
exec(compile(source, '<baseline figure3>', 'exec'), old.__dict__)
qc = {key: Path(f'tables/03_features/phase5b_{key}_with_classes.csv')
      for key in ('crystalformer_finetuned', 'crystallm_finetuned')}
before, audit_before, missing = old.load_figure3_inputs(qc_inputs=qc)
after, audit_after, _ = current.load_figure3_inputs(qc_inputs=qc)
assert not missing
pd.testing.assert_frame_equal(before, after, check_exact=True)
pd.testing.assert_frame_equal(audit_before, audit_after, check_exact=True)
rows = []
for cohort in current.COHORT_ORDER:
    for panel, variable in zip('ABC', current.VARIABLES):
        values = after.loc[after.analysis_cohort.eq(cohort), variable].dropna()
        if panel != 'C':
            values = values[values.gt(0)]
        stats = boxplot_stats(values.to_numpy())[0]
        rows.append({'cohort': cohort, 'panel': panel, 'n': len(values),
                     **{key: float(stats[key]) for key in ('q1', 'med', 'q3', 'whislo', 'whishi')}})
df, paired = load_paired_predictions()
path = 'paper/tables/figure_sources/fig05_energy_magnetism.csv'
old_bytes = subprocess.check_output(['git', 'show', baseline + ':' + path])
assert old_bytes.replace(b'\r\n', b'\n') == Path(path).read_bytes().replace(b'\r\n', b'\n')
summary = paired.groupby('analysis_cohort')[[ENERGY, MOMENT]].agg(['count', 'median'])
summary.to_csv(OUTPUT_DIR / 'figure5_medians.csv')
audit_after.to_csv(OUTPUT_DIR / 'figure3_audit.csv')
(OUTPUT_DIR / 'box_statistics.json').write_text(json.dumps(rows, indent=2))
print('PASS: old/new Figure 3 aligned records, prevalence and availability audits identical.')
print('PASS: all 30 boxplot populations unchanged (quartiles, medians, whiskers).')
print('PASS: Figure 5 normalized source unchanged; baseline Git-blob SHA256:', hashlib.sha256(old_bytes).hexdigest())
print('Finite pairs:', len(paired), '/', len(df))
print(summary.to_string())
xlo, xhi = paired[ENERGY].quantile([0.005, 0.995])
ylo, yhi = paired[MOMENT].quantile([0.005, 0.995])
limits = ((xlo - .06*(xhi-xlo), xhi + .06*(xhi-xlo)),
          (ylo - .08*(yhi-ylo), yhi + .08*(yhi-ylo)))
outside = ~(paired[ENERGY].between(*limits[0]) & paired[MOMENT].between(*limits[1]))
print('Historical Figure 5 display limits:', limits)
print('Finite pairs outside the display window (still included in medians):', int(outside.sum()))
print(paired.loc[outside].groupby('analysis_cohort').size().to_string())

import pymupdf
old_figure4 = subprocess.check_output(['git', 'show', baseline + ':paper/figures/fig04_magnetic_reference_dft.pdf'])
assert old_figure4 == Path('paper/figures/fig04_magnetic_reference_dft.pdf').read_bytes()
print('PASS: Figure 4 is byte-identical to baseline; SHA256:', hashlib.sha256(old_figure4).hexdigest())
for name in ('fig03_magnetic_domain', 'fig05_energy_magnetism'):
    page = pymupdf.open(f'paper/figures/{name}.pdf')[0]
    if name == 'fig03_magnetic_domain':
        np.testing.assert_allclose([page.rect.width, page.rect.height], [1152, 648], atol=0.01)
        from PIL import Image
        with Image.open('reproduced/analysis_v2_magnetic/figures/manuscript_figure3_magnetic_domain_v2_preview.png') as png:
            assert png.size == (7200, 4050)
        print('PASS: Figure 3 PDF is exactly 16:9 (1152 x 648 pt), no tight crop.')
    else:
        historical_pdf = subprocess.check_output(['git', 'show', baseline + ':paper/figures/fig05_energy_magnetism.pdf'])
        historical = pymupdf.open(stream=historical_pdf, filetype='pdf')[0]
        np.testing.assert_allclose(tuple(page.rect), tuple(historical.rect), atol=0.01)
        # Compare the historical palette and open/filled median-diamond
        # encodings directly to vector artists in the original PDF.
        def diamonds(pdf_page):
            return [d for d in pdf_page.get_drawings()
                    if d['fill'] is not None and len(d['items']) == 4
                    and all(item[0] == 'l' for item in d['items'])
                    and 5 < d['rect'].width < 20 and 5 < d['rect'].height < 20]
        original_diamonds, current_diamonds = diamonds(historical), diamonds(page)
        assert len(original_diamonds) == len(current_diamonds) == 10
        for original, restored in zip(original_diamonds, current_diamonds):
            np.testing.assert_allclose(original['fill'], restored['fill'], atol=1e-6)
            np.testing.assert_allclose(original['color'], restored['color'], atol=1e-6)
        print('PASS: Figure 5 page size, palette and open/filled diamonds match the historical PDF.')
    page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(OUTPUT_DIR / f'{name}.png')
    sizes = [s['size'] for b in page.get_text('dict')['blocks'] if 'lines' in b
             for line in b['lines'] for s in line['spans']]
    print(name, 'PDF size:', page.rect, 'minimum text size:', min(sizes))
    assert all(page.rect.contains(pymupdf.Rect(s['bbox']))
               for b in page.get_text('dict')['blocks'] if 'lines' in b
               for line in b['lines'] for s in line['spans'])
print('PASS: PDF text within page bounds.')
