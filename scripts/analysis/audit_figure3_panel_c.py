"""Audit the actual Figure 3 panel-C population and optionally rebuild Figure 3."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.cbook import boxplot_stats
import numpy as np
import pymupdf as fitz
from mvpipeline.analysis import manuscript_figure3_v2 as figure3


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    args = parser.parse_args()
    out = ROOT / 'reproduced/figure3_panel_c'
    out.mkdir(parents=True, exist_ok=True)
    protected = [ROOT / 'paper/figures' / name for name in
                 ('fig01_pipeline.pdf', 'fig04_magnetic_reference_dft.pdf')]
    protected_hashes = {str(p.relative_to(ROOT)): sha(p) for p in protected}
    qc = {key: ROOT / f'tables/03_features/phase5b_{key}_with_classes.csv'
          for key in ('crystalformer_finetuned', 'crystallm_finetuned')}
    df, audit, missing = figure3.load_figure3_inputs(qc_inputs=qc)
    assert not missing, missing
    assert audit.descriptor_records.eq(audit.qc_count).all()
    subset = df.loc[df.analysis_cohort.eq('concdvae_baseline')]
    mask = subset.magnetic_geometry_status.eq('ok')
    values = subset.loc[mask, figure3.MAGNETIC_NEIGHBOR_VARIABLE].dropna().to_numpy()
    assert np.isfinite(values).all()
    figure3.apply_publication_style()
    captured = {}
    original_boxplot = Axes.boxplot
    def capture(ax, x, *positional, **kwargs):
        bound = inspect.signature(original_boxplot).bind(ax, x, *positional, **kwargs)
        bound.apply_defaults()
        captured.update(bound.arguments)
        return original_boxplot(ax, x, *positional, **kwargs)
    Axes.boxplot = capture
    fig, ax = plt.subplots()
    try:
        figure3._boxplot(ax, [values])
    finally:
        Axes.boxplot = original_boxplot
        plt.close(fig)
    whis = captured['whis']
    if whis is None:
        whis = plt.rcParams['boxplot.whiskers']
    settings = dict(whis=whis, autorange=captured['autorange'], showfliers=captured['showfliers'])
    stats = boxplot_stats(values, whis=whis, autorange=settings['autorange'])[0]
    populations = {}
    for cohort in figure3.COHORT_ORDER:
        for panel, variable in zip('ABC', figure3.VARIABLES):
            selected = df.analysis_cohort.eq(cohort)
            if panel == 'C':
                selected &= df.magnetic_geometry_status.eq('ok')
            population = df.loc[selected, variable].dropna().to_numpy()
            if panel != 'C':
                population = population[population > 0]
            populations[f'{panel}/{cohort}'] = hashlib.sha256(population.tobytes()).hexdigest()
    summary = dict(
        cohort='concdvae_baseline', variable=figure3.MAGNETIC_NEIGHBOR_VARIABLE,
        mask="retained QC IDs; analysis_cohort == concdvae_baseline; magnetic_geometry_status == ok; dropna (reader excludes nonfinite)",
        qc_retained=len(subset), applicable_finite=len(values),
        zeros=int((values == 0).sum()), zero_fraction=float((values == 0).mean()),
        min=float(values.min()), Q1=float(stats['q1']), median=float(stats['med']),
        Q3=float(stats['q3']), max=float(values.max()),
        whislo=float(stats['whislo']), whishi=float(stats['whishi']),
        positive_values=int((values > 0).sum()), positive_fliers=int((stats['fliers'] > 0).sum()),
        not_applicable=int(subset.magnetic_geometry_status.eq('not_applicable').sum()),
        ok_missing=int((mask & subset[figure3.MAGNETIC_NEIGHBOR_VARIABLE].isna()).sum()),
        status_missing=int(subset.magnetic_geometry_status.isna().sum()), settings=settings,
        sources={str(p): sha(p) for p in set(map(Path, subset.descriptor_source.dropna()))},
        qc_source=str(figure3.QC_INPUTS['concdvae_baseline']),
        qc_source_sha256=sha(figure3.QC_INPUTS['concdvae_baseline']),
        populations_sha256=populations, protected_sha256=protected_hashes,
    )
    baseline_path = out / 'before.json'
    if args.build:
        baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
        assert summary == baseline, 'Input populations, statistics, settings or protected PDFs changed'
        original_export = figure3.save_analysis_v2_figure_bundle
        def verify_export(fig, *a, **kw):
            panel_c = fig.axes[-1]
            assert panel_c.get_ylim()[0] < 0
            medians = [line for line in panel_c.lines if line.get_zorder() == 4]
            assert len(medians) == 10
            zero_median = medians[2]
            np.testing.assert_array_equal(zero_median.get_ydata(), [0, 0])
            assert zero_median.get_zorder() > panel_c.spines['bottom'].get_zorder()
            return original_export(fig, *a, **kw)
        figure3.save_analysis_v2_figure_bundle = verify_export
        try:
            paths = figure3.save_manuscript_figure3(df, output_dir=out / 'build', audit=audit)
        finally:
            figure3.save_analysis_v2_figure_bundle = original_export
        with fitz.open(paths.pdf) as doc:
            assert tuple(doc[0].rect) == (0, 0, 1152, 648)
            doc[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(out / 'preview.png')
            for block in doc[0].get_text('dict')['blocks']:
                for line in block.get('lines', []):
                    for span in line['spans']:
                        # Rotated Ebrima font boxes overestimate visible ink at the
                        # left edge by <1 pt; the rendered labels are reviewed too.
                        bounds = doc[0].rect + (-1, 0, 0, 0)
                        assert bounds.contains(fitz.Rect(span['bbox'])), span
        for p in protected:
            assert sha(p) == protected_hashes[str(p.relative_to(ROOT))]
        target = ROOT / 'paper/figures/fig03_magnetic_domain.pdf'
        shutil.copyfile(paths.pdf, target)
        checksums = ROOT / 'paper/figures/SHA256SUMS.txt'
        rows = checksums.read_text(encoding='utf-8').splitlines()
        rows = [f'{sha(target)}  ./fig03_magnetic_domain.pdf'
                if r.endswith('  ./fig03_magnetic_domain.pdf') else r for r in rows]
        checksums.write_text('\n'.join(rows) + '\n', encoding='utf-8')
        summary['validation'] = 'PASS: all 30 populations/settings unchanged; zero median visible; protected PDFs unchanged'
        summary['canonical_sha256'] = sha(target)
        audit.to_csv(out / 'figure3_availability_audit.csv')
        (out / 'after.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    else:
        baseline_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'populations_sha256'}, indent=2))


if __name__ == '__main__':
    main()
