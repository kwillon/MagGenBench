from pathlib import Path
import json
import pandas as pd
import pytest

from cifmagfilter.cli import validate_cif_only_config
from cifmagfilter.core import Structure, structure_features


def test_external_site_priors_rejected_by_default(tmp_path):
    prior = tmp_path / "priors.csv"
    prior.write_text("dataset,structure_id,site_index,oxidation_state\nq,x,0,3\n", encoding="utf-8")
    cfg = {"site_priors": str(prior)}
    with pytest.raises(ValueError, match="forbids external site_priors"):
        validate_cif_only_config(cfg)
    validate_cif_only_config(cfg, allow_external_site_priors=True)


@pytest.mark.skipif(Structure is None, reason="pymatgen not installed")
def test_ordered_fixture_is_accepted_by_structure_parser():
    root = Path(__file__).parent / "fixtures"
    sites, pairs, row = structure_features(root / "feo_ordered.cif", "test", pd.DataFrame(), reject_disordered=True)
    assert row["parse_success"] == 1
    assert row["formula_reduced"]


@pytest.mark.skipif(Structure is None, reason="pymatgen not installed")
def test_disordered_fixture_is_rejected_in_canonical_mode():
    root = Path(__file__).parent / "fixtures"
    sites, pairs, row = structure_features(root / "disordered_femn_o.cif", "test", pd.DataFrame(), reject_disordered=True)
    assert row["parse_success"] == 0
    assert row["parse_error"] == "disordered_structure_not_supported_in_canonical_mode"
