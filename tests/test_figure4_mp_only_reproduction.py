"""Scientific gates: reject changed summaries and altered historical DFT labels."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

spec = importlib.util.spec_from_file_location(
    "figure4_audit", Path(__file__).resolve().parents[1] / "scripts/analysis/audit_figure4_mp_only.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_summary_reports_actual_changes_without_adjusting_results():
    original = pd.DataFrame({"dataset": ["a", "b"], "n_scored": [100, 50],
                             "fraction_magnetic_like": [.5, .8], "median_contrast": [.2, 1.5]})
    changed = original.iloc[::-1].copy()
    changed.loc[changed.dataset.eq("a"), "n_scored"] = 99
    changed.loc[changed.dataset.eq("b"), "median_contrast"] = 1.4
    result = audit.compare_summary(original, changed)
    failures = result.loc[~result.matches]
    assert set(zip(failures.dataset, failures.metric)) == {("a", "n_scored"), ("b", "median_contrast")}
    np.testing.assert_allclose(failures.difference, [-1, -.1])
    assert changed.loc[changed.dataset.eq("a"), "n_scored"].item() == 99


def test_summary_rejects_missing_cohort():
    original = pd.DataFrame({"dataset": ["a", "b"], "n_scored": [100, 50]})
    with pytest.raises(ValueError, match="cohort sets differ"):
        audit.compare_summary(original, original.iloc[:1])


def test_dft_labels_checked_by_hash_and_dataset_after_reordering():
    source = pd.DataFrame({"dataset": ["mattergen_base"]*324,
                           "sha256": [f"hash{i}" for i in range(324)],
                           "is_magnetic": ["yes" if i % 2 else "no" for i in range(324)]})
    joined = source.drop(columns="is_magnetic").copy()
    joined["dft_is_magnetic"] = [i % 2 for i in range(324)]
    audit.validate_dft_labels(joined.iloc[::-1], source)
    joined.loc[1, "dft_is_magnetic"] = 0
    with pytest.raises(ValueError, match="outcomes differ"):
        audit.validate_dft_labels(joined, source)


def test_environment_comparison_rejects_disjoint_or_partial_samples():
    check_spec = importlib.util.spec_from_file_location(
        "figure4_environment", Path(__file__).resolve().parents[1] / "scripts/analysis/check_figure4_environment.py")
    check = importlib.util.module_from_spec(check_spec)
    check_spec.loader.exec_module(check)
    a = pd.DataFrame({"dataset": ["a", "a"], "structure_id": ["one", "two"],
                      "magnetic_reference_vs_NM_contrast": [.1, -.2]})
    b = a.copy()
    b["structure_id"] = ["three", "four"]
    with pytest.raises(ValueError, match="all selected scored identities"):
        check.compare_scored_records(a, b)
    b.loc[0, "structure_id"] = "one"
    with pytest.raises(ValueError, match="all selected scored identities"):
        check.compare_scored_records(a, b)
