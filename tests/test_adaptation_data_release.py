"""Public data must be verifiable without the private preparation ledger."""
import importlib.util
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]


def verifier():
    spec = importlib.util.spec_from_file_location(
        'adaptation_release_check', ROOT / 'scripts/analysis/verify_adaptation_data.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_public_dataset_matches_license_manifest_and_original_structure_counts():
    result = verifier().verify(require_tracked=True)
    assert result['shared_counts'] == {'train': 1139, 'val': 142, 'test': 145}
    assert result['crystalformer_counts'] == {'train': 1134, 'val': 142, 'test': 145}
    assert result['payload_files'] == 15
    assert result['data_license'] == 'CC-BY-4.0'
    assert result['unsafe_deserialization_used'] is False


def test_public_checkout_does_not_require_private_ledger_or_source_exports(tmp_path, monkeypatch):
    public = tmp_path / 'adaptation_data'
    shutil.copytree(ROOT / 'adaptation_data', public, ignore=shutil.ignore_patterns('local_only'))
    # Include the repository targets linked by the package README.
    (tmp_path / 'datasets').mkdir()
    (tmp_path / 'samples').mkdir()
    (tmp_path / 'scripts/analysis').mkdir(parents=True)
    shutil.copyfile(ROOT / 'scripts/analysis/verify_adaptation_data.py',
                    tmp_path / 'scripts/analysis/verify_adaptation_data.py')
    module = verifier()
    monkeypatch.setattr(module, 'PACKAGE', public)
    result = module.verify(require_tracked=True)
    assert result['sha256_and_counts'] == 'PASS'
    assert result['preparation_ledger_available_locally'] is False
    assert result['private_preparation_evidence_required'] is False
    assert result['source_inventory_checked'] is False
