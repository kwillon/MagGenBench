from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

STRUCTURE_SUFFIXES = {'.cif', '.mcif'}

# source_folder -> (prepared dataset name, family, variant, role, label)
DATASETS = {
    'crysjepa_base_cifs': ('crysjepa_base', 'crysjepa', 'base', 'query', None),
    'crysjepa_refined_cifs': ('crysjepa_refined', 'crysjepa', 'refined', 'query', None),
    'crystalllm_cifs': ('crystalllm', 'crystalllm', 'base', 'query', None),
    'concdvae_cifs': ('concdvae_base', 'concdvae', 'base', 'query', None),
    'concdvae_finetuned_cifs': ('concdvae_finetuned', 'concdvae', 'finetuned', 'query', None),
    'crystalformer_cifs': ('crystalformer', 'crystalformer', 'base', 'query', None),
    'mattergen_cifs': ('mattergen_base', 'mattergen', 'base', 'query', None),
    'mattergen_finetuned_cifs': ('mattergen_finetuned', 'mattergen', 'finetuned', 'query', None),
    'magndata': ('magndata', 'magndata', 'reference', 'reference', 'MAGNDATA'),
}

MP_LABELS = {'FM': 'FM', 'AFM': 'AFM', 'FiM': 'FiM', 'NM': 'NM'}


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def safe_piece(text: str) -> str:
    text = str(text).strip()
    text = re.sub(r'[<>:"/\\|?*]+', '_', text)
    text = re.sub(r'\s+', '_', text)
    text = re.sub(r'_+', '_', text)
    return text.strip(' ._') or 'unnamed'


def flat_name(relative_path: Path) -> str:
    """Encode the full relative path in the prepared filename."""
    parts = [safe_piece(x) for x in relative_path.parts[:-1]]
    stem = safe_piece(relative_path.stem)
    suffix = relative_path.suffix.lower()
    return '__'.join(parts + [stem]) + suffix if parts else stem + suffix


def parse_int(pattern: str, text: str):
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return int(m.group(1)) if m else ''


def parse_float_token(pattern: str, text: str):
    m = re.search(pattern, text, flags=re.IGNORECASE)
    if not m:
        return ''
    token = m.group(1).replace('p', '.').replace('P', '.')
    try:
        return float(token)
    except ValueError:
        return ''


def metadata_from_path(family: str, relative_path: Path) -> dict:
    parent_parts = list(relative_path.parts[:-1])
    parent_text = '/'.join(parent_parts)
    leaf_parent = parent_parts[-1] if parent_parts else ''

    meta = {
        'benchmark_group': '',
        'condition_path': parent_text,
        'condition_leaf': leaf_parent,
        'target_formula': '',
        'seed': '',
        'n_requested': '',
        'mattergen_mgd': '',
        'mattergen_guidance': '',
        'concdvae_condition': '',
        'crystalformer_series': '',
    }

    if family == 'mattergen':
        if parent_parts:
            meta['benchmark_group'] = parent_parts[0]
        meta['seed'] = parse_int(r'seed[_-]?(\d+)', parent_text)
        meta['mattergen_mgd'] = parse_float_token(r'mgd[_-]([0-9]+p[0-9]+)', parent_text)
        meta['mattergen_guidance'] = parse_float_token(r'(?:^|[_-])g[_-]([0-9]+p[0-9]+)', parent_text)
    elif family == 'crystalformer':
        meta['seed'] = parse_int(r'seed[_-]?(\d+)', parent_text)
        meta['n_requested'] = parse_int(r'(?:^|[_-])n[_-]?(\d+)', parent_text)
        m = re.search(r'(?:^|[/\\])s(\d+)(?:_|$)', parent_text, flags=re.IGNORECASE)
        meta['crystalformer_series'] = int(m.group(1)) if m else ''
    elif family == 'crystalllm':
        if parent_parts:
            meta['target_formula'] = parent_parts[0]
    elif family == 'concdvae':
        if parent_parts:
            meta['concdvae_condition'] = parent_parts[0]
        meta['seed'] = parse_int(r'seed[_-]?(\d+)', parent_text)
    else:
        meta['seed'] = parse_int(r'seed[_-]?(\d+)', parent_text)

    return meta


def discover_files(root: Path):
    return [p for p in sorted(root.rglob('*')) if p.is_file() and p.suffix.lower() in STRUCTURE_SUFFIXES]


def prepare_dataset(
    source_root: Path,
    dest_root: Path,
    dataset: str,
    family: str,
    variant: str,
    role: str,
    label: str | None,
    manifest_rows: list[dict],
    overwrite: bool,
):
    files = discover_files(source_root)
    if not files:
        print(f'[warn] no CIF/mCIF files: {source_root}')
        return 0

    dest_root.mkdir(parents=True, exist_ok=True)
    used_names: set[str] = set()

    for idx, src in enumerate(files, 1):
        rel = src.relative_to(source_root)
        prepared = flat_name(rel)

        # Extremely rare collision after filename sanitization: append stable path hash.
        if prepared.lower() in used_names:
            short = hashlib.sha1(str(rel).encode('utf-8')).hexdigest()[:10]
            prepared = f'{Path(prepared).stem}__{short}{src.suffix.lower()}'
        used_names.add(prepared.lower())

        dst = dest_root / prepared
        if dst.exists() and not overwrite:
            # If it is exactly the same source on a rerun, leave it in place.
            if dst.stat().st_size != src.stat().st_size or sha256_file(dst) != sha256_file(src):
                raise FileExistsError(f'Destination exists with different content: {dst}')
        else:
            shutil.copy2(src, dst)

        digest = sha256_file(src)
        meta = metadata_from_path(family, rel)
        row = {
            'dataset': dataset,
            'generator_family': family if role == 'query' else '',
            'variant': variant,
            'role': role,
            'label_order': label or '',
            'prepared_filename': prepared,
            'structure_id': Path(prepared).stem,
            'original_filename': src.name,
            'original_stem': src.stem,
            'original_relative_path': rel.as_posix(),
            'original_parent': rel.parent.as_posix() if str(rel.parent) != '.' else '',
            'source_root': str(source_root),
            'source_path': str(src),
            'prepared_path': str(dst),
            'sha256': digest,
            'size_bytes': src.stat().st_size,
            **meta,
        }
        manifest_rows.append(row)

        if idx % 500 == 0:
            print(f'  {dataset}: {idx}/{len(files)}')

    print(f'[ok] {dataset}: {len(files)} structures -> {dest_root}')
    return len(files)


def write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text('', encoding='utf-8')
        return
    fields = list(rows[0].keys())
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def make_config(project_root: Path) -> dict:
    def rel(*parts):
        return Path(*parts).as_posix()

    datasets = [
        {'name': 'magndata', 'path': rel('data','prepared','references','magndata'), 'role': 'reference', 'label': 'MAGNDATA'},
        {'name': 'afm', 'path': rel('data','prepared','references','mp','AFM'), 'role': 'reference', 'label': 'AFM'},
        {'name': 'fm', 'path': rel('data','prepared','references','mp','FM'), 'role': 'reference', 'label': 'FM'},
        {'name': 'fim', 'path': rel('data','prepared','references','mp','FiM'), 'role': 'reference', 'label': 'FiM'},
        {'name': 'nm', 'path': rel('data','prepared','references','mp','NM'), 'role': 'reference', 'label': 'NM'},
        {'name': 'crysjepa_base', 'path': rel('data','prepared','generators','crysjepa_base'), 'role': 'query'},
        {'name': 'crysjepa_refined', 'path': rel('data','prepared','generators','crysjepa_refined'), 'role': 'query'},
        {'name': 'crystalllm', 'path': rel('data','prepared','generators','crystalllm'), 'role': 'query'},
        {'name': 'concdvae_base', 'path': rel('data','prepared','generators','concdvae_base'), 'role': 'query'},
        {'name': 'concdvae_finetuned', 'path': rel('data','prepared','generators','concdvae_finetuned'), 'role': 'query'},
        {'name': 'crystalformer', 'path': rel('data','prepared','generators','crystalformer'), 'role': 'query'},
        {'name': 'mattergen_base', 'path': rel('data','prepared','generators','mattergen_base'), 'role': 'query'},
        {'name': 'mattergen_finetuned', 'path': rel('data','prepared','generators','mattergen_finetuned'), 'role': 'query'},
    ]
    return {
        'output_dir': 'results',
        'datasets': datasets,
        'extraction': {
            'neighbor_cutoff': 3.2,
            'max_mm_distance': 8.0,
            'contact_norm_cutoff': 1.2,
            'bond_scale': 1.3,
            'min_center_score': 0.05,
            'min_pair_weight': 0.05,
            'max_sites': 500,
            'symprec': 0.1,
            'min_oxidation_coverage': 1.0,
        },
        'reference': {
            'feature_set': 'main',
            'knn_k': 15,
            'clip_z': 8.0,
            'min_feature_coverage': 0.2,
            'near_constant_tol': 1e-8,
        },
    }


def main():
    ap = argparse.ArgumentParser(
        description='Flatten the known generator/reference CIF tree into unique per-dataset folders while preserving provenance.'
    )
    ap.add_argument('--source', required=True, help='Root containing crysjepa_base_cifs, mattergen_cifs, mp_cifs_2000, magndata, ...')
    ap.add_argument('--project-root', default='.', help='Destination project root (default: current directory)')
    ap.add_argument('--overwrite', action='store_true', help='Overwrite existing prepared files')
    ap.add_argument('--no-hash', action='store_true', help='Reserved compatibility flag; SHA256 is currently always recorded')
    args = ap.parse_args()

    source = Path(args.source)
    project = Path(args.project_root)
    if not source.exists():
        raise SystemExit(f'Source root does not exist: {source}')

    prepared = project / 'data' / 'prepared'
    manifest_rows: list[dict] = []
    counts = {}

    # Query datasets + MAGNDATA.
    for folder, (dataset, family, variant, role, label) in DATASETS.items():
        src = source / folder
        if not src.exists():
            print(f'[warn] missing source folder, skipped: {src}')
            continue
        if role == 'reference':
            dst = prepared / 'references' / 'magndata'
        else:
            dst = prepared / 'generators' / dataset
        counts[dataset] = prepare_dataset(src, dst, dataset, family, variant, role, label, manifest_rows, args.overwrite)

    # Materials Project reference branches.
    mp_root = source / 'mp_cifs_2000'
    if not mp_root.exists():
        print(f'[warn] missing MP reference root: {mp_root}')
    else:
        for folder, label in MP_LABELS.items():
            src = mp_root / folder
            dataset = label.lower() if label != 'FiM' else 'fim'
            dst = prepared / 'references' / 'mp' / folder
            if not src.exists():
                print(f'[warn] missing MP branch: {src}')
                continue
            counts[dataset] = prepare_dataset(src, dst, dataset, 'materials_project', 'reference', 'reference', label, manifest_rows, args.overwrite)

    manifest_path = project / 'data' / 'manifests' / 'cif_manifest.csv'
    write_csv(manifest_path, manifest_rows)

    # Duplicate content hashes are retained, not removed.
    by_hash = defaultdict(list)
    for row in manifest_rows:
        by_hash[row['sha256']].append(row)
    duplicate_groups = [v for v in by_hash.values() if len(v) > 1]
    dup_rows = []
    for group_id, group in enumerate(sorted(duplicate_groups, key=lambda x: (-len(x), x[0]['sha256'])), 1):
        for r in group:
            dup_rows.append({
                'duplicate_group': group_id,
                'n_identical_files': len(group),
                'sha256': r['sha256'],
                'dataset': r['dataset'],
                'structure_id': r['structure_id'],
                'original_relative_path': r['original_relative_path'],
                'prepared_path': r['prepared_path'],
            })
    dup_path = project / 'data' / 'manifests' / 'duplicate_content.csv'
    write_csv(dup_path, dup_rows)

    summary_rows = []
    dataset_counter = Counter(r['dataset'] for r in manifest_rows)
    for ds in sorted(dataset_counter):
        ds_rows = [r for r in manifest_rows if r['dataset'] == ds]
        summary_rows.append({
            'dataset': ds,
            'n_structures': len(ds_rows),
            'n_unique_structure_ids': len({r['structure_id'] for r in ds_rows}),
            'n_unique_sha256': len({r['sha256'] for r in ds_rows}),
            'role': ds_rows[0]['role'],
            'label_order': ds_rows[0]['label_order'],
        })
    summary_path = project / 'data' / 'manifests' / 'dataset_summary.csv'
    write_csv(summary_path, summary_rows)

    config = make_config(project)
    config_path = project / 'config.prepared.json'
    config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    print('\nPrepared data summary:')
    for row in summary_rows:
        print(f"  {row['dataset']:<22} {row['n_structures']:>6} structures; unique IDs={row['n_unique_structure_ids']}; unique content={row['n_unique_sha256']}")
    print(f'\nManifest: {manifest_path}')
    print(f'Duplicate-content report: {dup_path}')
    print(f'Dataset summary: {summary_path}')
    print(f'Pipeline config: {config_path}')
    print('\nNo CIF was deleted or modified in the source tree; prepared files are byte-for-byte copies.')


if __name__ == '__main__':
    main()
