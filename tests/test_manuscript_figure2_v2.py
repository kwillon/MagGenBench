from __future__ import annotations

import csv

import numpy as np
import pytest

from mvpipeline.analysis.manuscript_figure2_v2 import (
    BASE_COHORTS, EXPECTED_RETAINED, FT_COHORTS, QC_COHORT_ORDER,
    _plot_retention, _read_qc_table, build_structural_qc_tables,
    run_manuscript_figure2, save_manuscript_figure2,
)
from mvpipeline.analysis.validation_figures_v2 import MODEL_ORDER


def write_qc(path, retained, *, total=2000, identity="structure_id"):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([identity, "status", "rejection_reason"])
        for index in range(total):
            writer.writerow([f"s{index}", "validated" if index < retained else "rejected",
                             "" if index < retained else "duplicate"])
    return path


@pytest.fixture
def new_qc_inputs(tmp_path):
    # Deliberately differ from verification targets to detect hardcoded counts.
    return {
        "crystalformer_finetuned": write_qc(tmp_path / "cf.csv", 1000),
        "crystallm_finetuned": write_qc(tmp_path / "cl.csv", 500, identity="sample_uid"),
    }


def test_ten_cohorts_use_qc_statuses_and_rejected_denominators(new_qc_inputs):
    summary, rejection, missing = build_structural_qc_tables(qc_inputs=new_qc_inputs)
    assert not missing
    assert tuple(summary.index) == QC_COHORT_ORDER
    assert len(summary) == 10
    assert summary["n_total"].eq(2000).all()
    for key in summary.index.difference(new_qc_inputs):
        assert summary.loc[key, "n_validated"] == EXPECTED_RETAINED[key]
    assert summary.loc["crystalformer_finetuned", "n_validated"] == 1000
    assert summary.loc["crystallm_finetuned", "validated_percent"] == 25
    assert not summary.loc["crystallm_finetuned", "matches_expected"]
    assert summary["n_validated"].sum() == 12184
    assert sum(EXPECTED_RETAINED.values()) == 12281
    assert np.allclose(rejection.sum(axis=1), 100)
    assert rejection.loc["Crys-JEPA", "charge_imbalance"] == pytest.approx(100 * 154 / 236)
    assert rejection.loc["Crys-JEPA", "physically_impossible_distance"] == pytest.approx(100 * 77 / 236)
    assert rejection.loc["Crys-JEPA", "duplicate"] == pytest.approx(100 * 5 / 236)


def test_missing_tables_are_reported_without_fabricated_counts(tmp_path):
    absent = {
        "crystalformer_finetuned": tmp_path / "missing_cf.csv",
        "crystallm_finetuned": tmp_path / "missing_cl.csv",
    }
    report = run_manuscript_figure2(qc_inputs=absent, figure_dir=tmp_path, audit_only=True,
                                   check_expected=True)
    assert report.figure_paths is None
    assert report.missing_inputs == tuple(absent.values())
    assert report.qc_summary["n_validated"].sum() == 10684
    assert (tmp_path / "figure2_structural_qc_audit.csv").is_file()
    with pytest.raises(FileNotFoundError, match="Missing structural QC"):
        run_manuscript_figure2(qc_inputs=absent, figure_dir=tmp_path)
    assert not list(tmp_path.glob("*.pdf"))


def test_raw_generation_is_not_silently_used_as_benchmark(tmp_path):
    with pytest.raises(RuntimeError, match="found 2016"):
        _read_qc_table(write_qc(tmp_path / "raw.csv", 1380, total=2016))


@pytest.mark.parametrize("defect", ["duplicate_id", "unknown_status", "ragged", "validated_reason"])
def test_invalid_qc_records_fail(tmp_path, defect):
    path = write_qc(tmp_path / "bad.csv", 1000)
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    if defect == "duplicate_id":
        rows[2][0] = rows[1][0]
    elif defect == "unknown_status":
        rows[1][1] = "success"
    elif defect == "ragged":
        rows[1].append("extra")
    else:
        rows[1][2] = "duplicate"
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows(rows)
    with pytest.raises(RuntimeError):
        _read_qc_table(path)


def test_verification_targets_do_not_replace_measured_counts(tmp_path, new_qc_inputs):
    with pytest.raises(RuntimeError, match="differ from verification targets"):
        run_manuscript_figure2(qc_inputs=new_qc_inputs, figure_dir=tmp_path,
                               check_expected=True, audit_only=True)


def test_retention_panels_have_matching_order_and_scales(new_qc_inputs):
    import matplotlib.pyplot as plt

    summary, _, _ = build_structural_qc_tables(qc_inputs=new_qc_inputs)
    fig, axes = plt.subplots(1, 2)
    for ax, cohorts, panel in zip(axes, (BASE_COHORTS, FT_COHORTS), ("A", "B")):
        _plot_retention(ax, summary, cohorts, MODEL_ORDER, panel, panel)
    assert axes[0].get_xlim() == axes[1].get_xlim() == (0, 100)
    assert [t.get_text() for t in axes[0].get_yticklabels()] == list(MODEL_ORDER)
    assert [t.get_text() for t in axes[1].get_yticklabels()] == list(MODEL_ORDER)
    assert any("1,000 (50.00%)" == t.get_text() for t in axes[1].texts)
    plt.close(fig)


def test_export_layout_with_explicit_synthetic_ft_watermark(tmp_path, new_qc_inputs, monkeypatch):
    import mvpipeline.analysis.manuscript_figure2_v2 as figure2

    summary, rejection, _ = build_structural_qc_tables(qc_inputs=new_qc_inputs)
    original = figure2.save_analysis_v2_figure_bundle

    def save_layout(fig, output_dir, basename):
        fig.suptitle("LAYOUT QA ONLY - CrystalFormer FT and CrystaLLM FT are synthetic", fontsize=12)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        # Verify annotations, titles and tick labels remain inside the exported canvas.
        for ax in fig.axes:
            for label in [*ax.texts, ax.title, ax.xaxis.label, ax.yaxis.label,
                          *ax.get_xticklabels(), *ax.get_yticklabels()]:
                if not label.get_visible() or not label.get_text():
                    continue
                bbox = label.get_window_extent(renderer)
                assert bbox.x0 >= 0 and bbox.y0 >= 0
                assert bbox.x1 <= fig.bbox.width and bbox.y1 <= fig.bbox.height
        return original(fig, output_dir, basename)

    monkeypatch.setattr(figure2, "save_analysis_v2_figure_bundle", save_layout)
    paths = save_manuscript_figure2(summary, rejection, output_dir=tmp_path)
    for path in (paths.png, paths.pdf, paths.svg):
        assert path.stat().st_size > 10000
    svg = paths.svg.read_text(encoding="utf-8")
    assert "registered primary rejection reasons" in svg
    assert "LAYOUT QA ONLY" in svg
    print(f"Layout QA preview: {paths.png}")
