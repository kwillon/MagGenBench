"""Scientific/artifact contracts after centralizing publication inputs."""
import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

from mvpipeline.analysis.artifact_paths import resolve_artifact_path
from mvpipeline.analysis.manuscript_figure5_v2 import FIGURE_SOURCE, load_paired_predictions

ROOT = Path(__file__).resolve().parents[1]


def test_selected_figure8_is_exact_hybrid_v2():
    figures = ROOT/'paper/figures'
    assert (figures/'fig08_multiobjective.pdf').read_bytes() == (figures/'legacy/fig08_multiobjective_hybrid_v2.pdf').read_bytes()
    assert not list(figures.glob('*.png'))
    assert {p.name for p in figures.glob('*.md')} == {'README.md'}


def test_all_publication_pdf_checksums():
    figures = ROOT/'paper/figures'
    listed = set()
    for line in (figures/'SHA256SUMS.txt').read_text().splitlines():
        checksum, relative = line.split(maxsplit=1)
        path = figures/relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == checksum
        listed.add(path.resolve())
    assert listed == {p.resolve() for p in figures.rglob('*.pdf')}


def test_moved_figure5_source_retains_population():
    assert FIGURE_SOURCE == Path('tables/figure_sources/fig05_energy_magnetism.csv')
    raw, paired = load_paired_predictions(ROOT/FIGURE_SOURCE)
    assert len(raw) == 12281 and len(paired) == 12277
    params = json.loads((ROOT/'tables/figure_sources/figure5_overlap/analysis_parameters.json').read_text())
    resolved = resolve_artifact_path(params['source'])
    assert resolved == ROOT/FIGURE_SOURCE
    assert hashlib.sha256(resolved.read_bytes()).hexdigest() == params['source_sha256']


def test_s1_top5_uses_atomic_content_rank_distribution():
    with (ROOT/'tables/figure_sources/figure8/figure08_scenario_rankings_v2.csv').open() as f:
        rows = [r for r in csv.DictReader(f) if r['variant']=='S1']
    assert len(rows) == 10
    expected = {'mattergen_baseline':20000, 'mattergen_finetuned':13004,
                'concdvae_baseline':14855, 'concdvae_finetuned':9700,
                'crystalformer_baseline':73, 'crystalformer_finetuned':19729,
                'crystallm_baseline':0, 'crystallm_finetuned':0,
                'crysjepa_base':17406, 'crysjepa_refined':5233}
    for row in rows:
        total = sum(Decimal(row[f'rank_{i}_pct']) for i in range(1,6))
        assert abs(total-Decimal(row['top5_pct'])) < Decimal('1e-10')
        assert round(total*200) == expected[row['analysis_cohort']]
        assert int(row['n_weights']) == 20000
