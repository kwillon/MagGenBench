from __future__ import annotations

import csv

import numpy as np
import pandas as pd
import pytest

from mvpipeline.analysis.figures_v2_magnetic import (
    AUDIT_VARIABLES,
)
from mvpipeline.analysis.manuscript_figure3_v2 import (
    COHORT_ORDER,
    FIGURE_BASENAME,
    LANTHANIDE_VARIABLE,
    MAGNETIC_NEIGHBOR_VARIABLE,
    TRANSITION_3D_VARIABLE,
    build_figure3_audit,
    load_figure3_inputs,
    run_manuscript_figure3,
    save_manuscript_figure3,
)


def test_manuscript_figure3_basename():
    assert (
        FIGURE_BASENAME
        == "manuscript_figure3_magnetic_domain_v2_preview"
    )


def test_transition_3d_variable_is_audited():
    assert TRANSITION_3D_VARIABLE in AUDIT_VARIABLES


def test_lanthanide_variable_is_audited():
    assert LANTHANIDE_VARIABLE in AUDIT_VARIABLES


def test_magnetic_neighbor_variable_is_audited():
    assert MAGNETIC_NEIGHBOR_VARIABLE in AUDIT_VARIABLES


def test_manuscript_figure3_variables_are_distinct():
    assert len(
        {
            TRANSITION_3D_VARIABLE,
            LANTHANIDE_VARIABLE,
            MAGNETIC_NEIGHBOR_VARIABLE,
        }
    ) == 3

@pytest.fixture
def extra_inputs(tmp_path):
    qc_inputs, descriptor_inputs = {}, {}
    for cohort, retained in (("crystalformer_finetuned", 3), ("crystallm_finetuned", 2)):
        path = tmp_path / f"{cohort}_qc.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["sample_uid", "status"])
            writer.writerows(
                [f"{cohort}_{i}", "validated" if i < retained else "rejected"]
                for i in range(2000)
            )
        qc_inputs[cohort] = path
        path = tmp_path / f"{cohort}_desc.csv"
        df = pd.DataFrame({
            "sample_uid": [f"{cohort}_0", f"{cohort}_1"],
            "analysis_cohort": [cohort] * 2,
            TRANSITION_3D_VARIABLE: [0.5, np.nan] if retained == 3 else [0, 0],
            LANTHANIDE_VARIABLE: [0, 0.25] if retained == 3 else [0, 0],
            MAGNETIC_NEIGHBOR_VARIABLE: [0, np.nan] if retained == 3 else [np.nan, 0.25],
            "magnetic_geometry_status": ["ok", "not_applicable"] if retained == 3 else ["error", "ok"],
        })
        df.to_csv(path, index=False)
        descriptor_inputs[cohort] = path
    return qc_inputs, descriptor_inputs


def test_real_eight_cohorts_and_two_missing_sources(tmp_path):
    absent_qc = {key: tmp_path / f"{key}_qc.csv"
                 for key in ("crystalformer_finetuned", "crystallm_finetuned")}
    absent_desc = {key: tmp_path / f"{key}_desc.csv" for key in absent_qc}
    report = run_manuscript_figure3(
        qc_inputs=absent_qc, descriptor_inputs=absent_desc, figure_dir=tmp_path, audit_only=True,
    )
    audit = report.audit
    assert tuple(audit.index) == COHORT_ORDER
    assert audit["qc_count"].sum() == 10684
    assert audit.loc["mattergen_baseline", "A_nonzero"] == 1248
    assert audit.loc["mattergen_finetuned", "B_nonzero"] == 1
    assert audit.loc["crysjepa_refined", "C_applicable"] == 502
    assert audit.loc["crysjepa_refined", "C_not_applicable"] == 1041
    assert audit.loc["crysjepa_refined", "C_zero"] == 154
    assert pd.isna(audit.loc["crystallm_finetuned", "qc_count"])
    assert pd.isna(audit.loc["crystallm_finetuned", "A_prevalence_percent"])
    assert len(report.missing_inputs) == 4
    assert report.figure_paths is None
    with pytest.raises(FileNotFoundError, match="Missing Figure 3 sources"):
        run_manuscript_figure3(qc_inputs=absent_qc, descriptor_inputs=absent_desc,
                               figure_dir=tmp_path)
    assert not list(tmp_path.glob("*.pdf"))


def test_availability_prevalence_and_missing_are_independent_of_qc(extra_inputs):
    qc, descriptors = extra_inputs
    df, audit, missing = load_figure3_inputs(qc_inputs=qc, descriptor_inputs=descriptors)
    assert not missing
    assert len(df) == 10689
    cf = audit.loc["crystalformer_finetuned"]
    assert cf["qc_count"] == 3
    assert cf["descriptor_records"] == 2
    assert cf["descriptor_missing_records"] == 1
    assert cf["A_available"] == cf["A_nonzero"] == 1
    assert cf["A_prevalence_percent"] == 100
    assert cf["A_missing"] == 2
    assert cf["B_available"] == 2
    assert cf["B_nonzero"] == cf["B_zero"] == 1
    assert cf["B_prevalence_percent"] == 50
    assert cf["C_applicable"] == cf["C_zero"] == cf["C_not_applicable"] == 1
    assert cf["C_status_missing"] == 1
    assert audit.loc["crystallm_finetuned", "A_prevalence_percent"] == 0
    assert audit.loc["crystallm_finetuned", "C_error"] == 1


def test_complete_descriptor_coverage_check(extra_inputs, tmp_path):
    qc, descriptors = extra_inputs
    with pytest.raises(RuntimeError, match="Incomplete descriptor ID coverage"):
        run_manuscript_figure3(qc_inputs=qc, descriptor_inputs=descriptors,
                               figure_dir=tmp_path, audit_only=True,
                               require_complete_descriptors=True)


def test_no_available_values_have_undefined_prevalence():
    df = pd.DataFrame({
        "analysis_cohort": ["mattergen_baseline"] * 4,
        "descriptor_source": ["fixture"] * 4,
        TRANSITION_3D_VARIABLE: [np.nan] * 4,
        LANTHANIDE_VARIABLE: [0, 0, 0, 0],
        MAGNETIC_NEIGHBOR_VARIABLE: [0, np.nan, np.nan, np.nan],
        "magnetic_geometry_status": ["ok", "ok", "error", "not_computed"],
    })
    audit = build_figure3_audit(df, {"mattergen_baseline": 4})
    row = audit.loc["mattergen_baseline"]
    assert pd.isna(row["A_prevalence_percent"])
    assert row["B_prevalence_percent"] == 0
    assert row["C_applicable"] == row["C_zero"] == row["C_ok_missing"] == 1
    assert row["C_error"] == row["C_not_computed"] == 1


@pytest.mark.parametrize("defect", ["outside_qc", "duplicate", "out_of_range", "wrong_geometry_status"])
def test_invalid_descriptors_fail(extra_inputs, defect):
    qc, descriptors = extra_inputs
    path = descriptors["crystalformer_finetuned"]
    df = pd.read_csv(path)
    if defect == "outside_qc":
        df.loc[0, "sample_uid"] = "not_retained"
    elif defect == "duplicate":
        df.loc[1, "sample_uid"] = df.loc[0, "sample_uid"]
    elif defect == "out_of_range":
        df.loc[0, TRANSITION_3D_VARIABLE] = 1.1
    else:
        df.loc[0, "magnetic_geometry_status"] = "not_applicable"
    df.to_csv(path, index=False)
    with pytest.raises(RuntimeError):
        load_figure3_inputs(qc_inputs=qc, descriptor_inputs=descriptors)


def test_raw_2016_population_rejected(extra_inputs):
    qc, descriptors = extra_inputs
    path = qc["crystalformer_finetuned"]
    df = pd.read_csv(path)
    extras = pd.DataFrame({"sample_uid": [f"extra_{i}" for i in range(16)], "status": "rejected"})
    pd.concat([df, extras]).to_csv(path, index=False)
    with pytest.raises(RuntimeError, match="expected 2000"):
        load_figure3_inputs(qc_inputs=qc, descriptor_inputs=descriptors)


def test_primary_descriptor_table_matches_analysis_table():
    _, analysis, _ = load_figure3_inputs()
    _, descriptor, _ = load_figure3_inputs(
        "tables/09_descriptor_v2_magnetic/descriptor_v2_magnetic.csv",
    )
    pd.testing.assert_frame_equal(analysis.drop(columns="descriptor_source"),
                                  descriptor.drop(columns="descriptor_source"))


def test_ten_set_layout_and_exports(extra_inputs, tmp_path, monkeypatch):
    import mvpipeline.analysis.manuscript_figure3_v2 as figure3

    qc, descriptors = extra_inputs
    df, audit, _ = load_figure3_inputs(qc_inputs=qc, descriptor_inputs=descriptors)
    original = figure3.save_analysis_v2_figure_bundle

    def export(fig, output_dir, basename, **kwargs):
        fig.suptitle("LAYOUT QA ONLY - CrystalFormer FT and CrystaLLM FT are synthetic", fontsize=12)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        for ax in fig.axes:
            if not ax.axison:
                continue  # legend-only axes have no rendered ticks or axis labels
            for label in [*ax.texts, ax.title, ax._left_title, ax.xaxis.label, ax.yaxis.label,
                          *ax.get_xticklabels(), *ax.get_yticklabels()]:
                if not label.get_visible() or not label.get_text():
                    continue
                bbox = label.get_window_extent(renderer)
                assert bbox.x0 >= 0 and bbox.y0 >= 0
                assert bbox.x1 <= fig.bbox.width and bbox.y1 <= fig.bbox.height
            tick_boxes = [label.get_window_extent(renderer) for label in ax.get_xticklabels()
                          if label.get_visible() and label.get_text()]
            for left, right in zip(tick_boxes, tick_boxes[1:]):
                assert left.x1 < right.x0
        assert len(fig.axes) == 6  # dedicated legends outside the scientific panels
        assert len(fig.axes[1].patches) == 10
        assert fig.axes[1].get_ylim() == fig.axes[3].get_ylim()
        assert len(fig.axes[-1].get_xticklabels()) == 10
        assert tuple(fig.get_size_inches()) == (16, 9)
        assert kwargs == {"preserve_canvas": True}
        return original(fig, output_dir, basename, **kwargs)

    monkeypatch.setattr(figure3, "save_analysis_v2_figure_bundle", export)
    paths = save_manuscript_figure3(df, audit=audit, output_dir=tmp_path)
    for path in (paths.png, paths.pdf, paths.svg):
        assert path.stat().st_size > 10000
    assert "n=502" in paths.svg.read_text(encoding="utf-8")
    print(f"Layout QA preview: {paths.png}")
