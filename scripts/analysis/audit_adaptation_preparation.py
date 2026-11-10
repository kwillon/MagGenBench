"""Verify recovered preparation lineage using CSV and safe archive text reads.

No extraction, model execution, unsafe deserialization or source modification.
--write creates aggregate provenance and a Git-ignored selection ledger.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
INTERMEDIATE = '7dataset_with_lattice_and_positions - 7dataset_with_lattice_and_positions.csv.csv'
RAW_NEMAD = 'nemad_magnetic_materials.csv'
ARCHIVE = 'Novomag/Novamag_Database_Files.zip'
EXPECTED_SHA256 = {
    INTERMEDIATE: 'f1fea742b82e3312d9d3ad5ee6f2e758af7b7b280e175818757ead3ca711eb2d',
    RAW_NEMAD: '47ebbe99cb4f040065d88f4588484d7bc5b4053f37d5188ff3784a9a5ec83c38',
    ARCHIVE: '12e4f05fee562bf0f1832a8834cd4bfcbe3db9623dced17e8a0595d330dfdc9c',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def csv_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def number(text):
    try:
        result = Decimal(str(text))
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def normalized_cif(text):
    return text.replace('\r\n', '\n').strip()


def inspect(source_root, write=False):
    source_files = {}
    for name, expected in EXPECTED_SHA256.items():
        path = source_root / name
        require(path.is_file(), 'Missing source: ' + str(path))
        require(digest(path) == expected, 'Source hash changed: ' + name)
        source_files[name] = {'bytes': path.stat().st_size, 'sha256': expected}
    fields, intermediate = csv_rows(source_root / INTERMEDIATE)
    nemad_fields, nemad = csv_rows(source_root / RAW_NEMAD)
    require(len(intermediate) == 5203 and len(fields) == 69, 'Intermediate schema/count changed')
    require(len(nemad) == 33668 and len(nemad_fields) == 19, 'NEMAD schema/count changed')
    keys = [(r['Source'], r['Row_ID']) for r in intermediate]
    require(len(set(keys)) == len(keys), 'Duplicate source-local record keys')
    require(Counter(r['Source'] for r in intermediate) == {'novamag': 2069, 'nemad': 3134},
            'Intermediate source counts changed')
    retained = {}
    package_sources = json.loads((ROOT / 'adaptation_data/provenance/sources.json').read_text())
    for split, count in [('train', 1139), ('val', 142), ('test', 145)]:
        _, records = csv_rows(ROOT / 'adaptation_data' / package_sources['shared']['files'][split])
        require(len(records) == count, 'Prepared split changed')
        for record in records:
            key = record['Source'], record['Row_ID']
            require(key not in retained, 'Repeated prepared identity')
            retained[key] = split, record
    require(set(retained) <= set(keys), 'Prepared record missing from intermediate')
    raw_nemad = defaultdict(list)
    for record_number, row in enumerate(nemad, 1):
        raw_nemad[(row['Material_Name'], row['DOI'])].append(record_number)
    cif_index, json_index = defaultdict(list), defaultdict(list)
    archive_counts, bad_json = Counter(), []
    bytes_read = 0

    def read_entry(archive, info):
        nonlocal bytes_read
        require(info.file_size <= 64 * 1024 * 1024, 'Archive member exceeds size bound')
        bytes_read += info.file_size
        require(bytes_read <= 256 * 1024 * 1024, 'Archive audit exceeds read bound')
        return archive.read(info)

    def walk_data(archive, prefix='', depth=0):
        require(depth <= 4, 'Unexpected nested archive depth')
        for info in archive.infolist():
            if info.is_dir():
                continue
            if depth == 0 and not info.filename.startswith('Novamag_Database_Files/Data_files/'):
                continue
            name = prefix + info.filename
            suffix = Path(info.filename).suffix.lower()
            if suffix == '.zip':
                archive_counts['nested_data_zips'] += 1
                with zipfile.ZipFile(io.BytesIO(read_entry(archive, info))) as nested:
                    walk_data(nested, name + '!', depth + 1)
            elif suffix == '.cif':
                archive_counts['cif'] += 1
                cif_index[Path(info.filename).name].append((name, read_entry(archive, info)))
            elif suffix == '.json':
                archive_counts['json'] += 1
                data = read_entry(archive, info)
                parsed = None
                for encoding in ('utf-8-sig', 'cp1252', 'latin1'):
                    try:
                        parsed = json.loads(data.decode(encoding), parse_float=Decimal)
                        break
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        pass
                if isinstance(parsed, dict):
                    json_index[parsed.get('name')].append((name, parsed))
                else:
                    bad_json.append(name)

    with zipfile.ZipFile(source_root / ARCHIVE) as archive:
        outer_entries = len(archive.infolist())
        walk_data(archive)
    require(archive_counts == {'nested_data_zips': 41, 'cif': 2056, 'json': 2085},
            'Archive data inventory changed')
    require(len(bad_json) == 22, 'Unexpected source JSON parsing count')
    ledger, deltas = [], []
    matched_cifs, zero_targets, normalized_only = 0, 0, 0
    nemad_multiplicities = Counter()
    for record_number, row in enumerate(intermediate, 1):
        key = row['Source'], row['Row_ID']
        spin, volume = number(row['unit cell spin polarization']), number(row['unit cell volume'])
        selected = key in retained
        entry = {
            'source_csv_record_number_1based': record_number,
            'Source': row['Source'], 'Row_ID': row['Row_ID'],
            'selection_status': 'retained' if selected else 'not_in_recovered_splits',
            'split': '', 'material_id': '', 'matched_cif': '',
            'raw_json_member': '', 'raw_cif_member': '', 'cif_match_kind': '',
            'source_spin_finite': spin is not None,
            'source_volume_positive_finite': volume is not None and volume > 0,
            'lattice_params_present': bool(row['lattice_params']),
            'lattice_angles_present': bool(row['lattice_angles']),
            'atomic_positions_present': bool(row['atomic_positions']),
            'export_confidential_field': row['confidential'],
            'density_ratio_verified': '', 'density_abs_delta': '',
            'nemad_raw_candidate_records_1based': '', 'nemad_raw_match_multiplicity': '',
            'historical_exclusion_reason': '' if selected else 'not_documented',
        }
        if row['Source'] == 'nemad':
            matches = raw_nemad[(row['Formula'], row['DOI'])]
            require(matches, 'Unmatched NEMAD formula/DOI')
            entry['nemad_raw_candidate_records_1based'] = ';'.join(map(str, matches))
            entry['nemad_raw_match_multiplicity'] = len(matches)
            nemad_multiplicities['unique' if len(matches) == 1 else 'ambiguous'] += 1
        if selected:
            split, target = retained[key]
            require(row['Source'] == 'novamag' and row['Formula'] == target['Formula'],
                    'Prepared source/formula mismatch')
            require(row['wanted_cif'] == row['wanted_cif_after'] == target['matched_cif'],
                    'CIF reference changed')
            require(spin is not None and volume is not None and volume > 0, 'Missing retained property')
            require(all(row[k] for k in ['lattice_params', 'lattice_angles', 'atomic_positions', 'Sat_Magnetization']),
                    'Missing retained structural/magnetic field')
            raw_json = json_index[row['name']]
            require(len(raw_json) == 1, 'Ambiguous upstream JSON name')
            member, source = raw_json[0]
            require(number(source['properties']['magnetics']['unit cell spin polarization']['value']) == spin,
                    'Raw spin property differs')
            require(number(source['properties']['crystal']['unit cell volume']['value']) == volume,
                    'Raw volume property differs')
            raw_cifs = cif_index[target['matched_cif']]
            require(len(raw_cifs) == 1, 'Ambiguous upstream CIF basename')
            cif_member, cif_bytes = raw_cifs[0]
            require(normalized_cif(cif_bytes.decode('utf-8-sig')) == normalized_cif(target['cif']),
                    'Raw CIF text differs')
            exact = cif_bytes == target['cif'].encode('utf-8')
            normalized_only += not exact
            matched_cifs += 1
            saved = number(target['candidate_mag_density'])
            require(saved is not None, 'Nonfinite prepared target')
            with localcontext() as context:
                context.prec = 40
                delta = abs(saved - spin / volume)
            require(delta <= Decimal('1e-15'), 'Observed density ratio differs')
            zero_targets += saved == 0
            deltas.append(delta)
            entry.update(split=split, material_id=target['material_id'], matched_cif=target['matched_cif'],
                         raw_json_member=member, raw_cif_member=cif_member,
                         cif_match_kind='byte_identical' if exact else 'newline_whitespace_normalized',
                         density_ratio_verified=True, density_abs_delta=str(delta))
        ledger.append(entry)
    require(len(deltas) == matched_cifs == 1426, 'Incomplete retained lineage')
    require(normalized_only == 2 and zero_targets == 5, 'Prepared CIF/zero-target counts changed')
    require(nemad_multiplicities == {'unique': 2928, 'ambiguous': 206}, 'NEMAD join changed')
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=list(ledger[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(ledger)
    ledger_bytes = output.getvalue().encode('utf-8')
    units_prefix = 'Novamag_Database_Files/Source_files/NOVAMAG-Java-Loader-master.zip!NOVAMAG-Java-Loader-master/'
    result = {
        'status': 'PASS', 'sources': source_files,
        'intermediate': {'rows': 5203, 'columns': fields, 'source_counts': {'novamag': 2069, 'nemad': 3134}},
        'raw_nemad': {'rows': 33668, 'columns': nemad_fields, 'match_counts': dict(nemad_multiplicities)},
        'archive': {'outer_entries': outer_entries, 'data_counts': dict(archive_counts),
                    'unparsed_data_json': len(bad_json), 'code_executed': False, 'extraction_performed': False},
        'selection': {'retained': 1426, 'not_in_recovered_splits': 3777,
                      'not_retained_by_source': {'novamag': 643, 'nemad': 3134},
                      'retained_sources': {'novamag': 1426}, 'unknown_historical_exclusion_reasons': 3777},
        'lineage': {'source_key_formula_cif_reference_matches': 1426, 'upstream_json_property_matches': 1426,
                    'upstream_cif_byte_matches': 1424, 'upstream_cif_normalized_matches': 1426},
        'candidate_mag_density': {'observed_identity': 'unit cell spin polarization / unit cell volume',
                                 'verified_records': 1426, 'maximum_absolute_decimal_difference': str(max(deltas)),
                                 'zero_target_records': zero_targets, 'upstream_ratio_units': 'mu_B / Angstrom^3',
                                 'historical_calculation_code_available': False,
                                 'units_evidence': [units_prefix + 'src/json_loader/dao/DBitem.java:624,933-934',
                                                    units_prefix + 'data_for_tests/dao.items/FeNi_L10_v2.json:39-44,136-141']},
        'selection_ledger': {'path': 'local_only/selection_ledger.csv', 'records': 5203,
                             'sha256': hashlib.sha256(ledger_bytes).hexdigest(), 'bytes': len(ledger_bytes),
                             'redistribution_status': 'unresolved; Git-ignored'},
        'licensing': {'data_redistribution_permission': 'CC-BY-4.0 for the curated NOVAMAG subset; mixed-source and NEMAD materials remain uncleared',
                      'selected_subset_license_evidence': 'provenance/redistribution_review.json',
                      'selection_ledger_redistribution_permission': 'unresolved; contains NEMAD records',
                      'program_license': 'GPL version 2 or later for the Java loader program; not a dataset license',
                      'source_archive_copied': False, 'merged_csv_copied': False},
    }
    destination = ROOT / 'adaptation_data/preparation'
    if write:
        require(not (destination / 'manifest.json').exists(), 'Refusing to overwrite provenance')
        (destination / 'local_only').mkdir(parents=True, exist_ok=True)
        (destination / 'local_only/selection_ledger.csv').write_bytes(ledger_bytes)
        (destination / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    elif (destination / 'manifest.json').exists():
        require((destination / 'local_only/selection_ledger.csv').read_bytes() == ledger_bytes,
                'Saved selection ledger differs from recomputed evidence')
        require(json.loads((destination / 'manifest.json').read_text()) == result,
                'Saved aggregate manifest differs from recomputed evidence')
    for name, record in source_files.items():
        require(digest(source_root / name) == record['sha256'], 'Source changed during audit')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=Path.home() / 'Downloads')
    parser.add_argument('--write', action='store_true')
    options = parser.parse_args()
    result = inspect(options.source_root, options.write)
    print(json.dumps({k: result[k] for k in ('status', 'selection', 'lineage', 'candidate_mag_density', 'selection_ledger')}, indent=2))
