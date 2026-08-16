from __future__ import annotations

from pathlib import Path

import pytest

from mvpipeline.analysis import figures_v1


EXPECTED_ANALYSIS_V1_FIGURE_FILENAMES = (
    "01_crystal_system_core_baseline.png",
    "02_crystal_system_finetuning.png",
    "03_crystal_system_crysjepa.png",
    "structural_distribution_summary.csv",
    "04_density_distribution.png",
    "05_volume_per_site_distribution.png",
    "06_sites_per_cell_distribution.png",
    "compound_class_distribution_percent.csv",
    "07_compound_class_heatmap.png",
    "3d_4f_fraction_by_cohort.csv",
    "08_3d_4f_fraction_by_cohort.png",
    "magnetic_screening_element_fraction_summary.csv",
    "09_magnetic_screening_element_fraction.png",
    "dxmag_predicted_moment_summary.csv",
    "10_dxmag_predicted_moment_distribution.png",
)


MIGRATED_V1_WRAPPERS = {
    "plot_unified_analysis_v1.py": "generate_crystal_system_figures",
    "plot_structural_distributions_v1.py": (
        "generate_structural_distribution_figures"
    ),
    "plot_compound_class_heatmap_v1.py": "generate_compound_class_heatmap",
    "plot_3d_4f_fraction_v1.py": "generate_3d_4f_fraction_figure",
    "plot_magnetic_screening_fraction_v1.py": (
        "generate_magnetic_screening_fraction_figure"
    ),
    "plot_dxmag_predicted_moment_v1.py": (
        "generate_dxmag_predicted_moment_figure"
    ),
}


def test_canonical_analysis_v1_figure_manifest_matches_current_outputs() -> None:
    assert (
        figures_v1.ANALYSIS_V1_FIGURE_FILENAMES
        == EXPECTED_ANALYSIS_V1_FIGURE_FILENAMES
    )


def test_owned_figure_paths_are_under_requested_output_dir(tmp_path) -> None:
    paths = figures_v1.owned_analysis_v1_figure_paths(tmp_path / "custom")

    assert [path.name for path in paths] == list(
        EXPECTED_ANALYSIS_V1_FIGURE_FILENAMES
    )
    assert {path.parent for path in paths} == {tmp_path / "custom"}


def test_missing_input_csv_fails_clearly(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="missing.csv"):
        figures_v1.generate_analysis_v1_figures(
            input_csv=tmp_path / "missing.csv",
            output_dir=tmp_path / "out",
        )


def test_existing_owned_output_fails_without_force(tmp_path) -> None:
    owned = tmp_path / "out" / EXPECTED_ANALYSIS_V1_FIGURE_FILENAMES[0]
    owned.parent.mkdir(parents=True)
    owned.write_text("existing\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="use --force"):
        figures_v1.prepare_analysis_v1_figure_outputs(tmp_path / "out")


def test_force_removes_only_owned_files(tmp_path) -> None:
    out = tmp_path / "out"
    owned = out / EXPECTED_ANALYSIS_V1_FIGURE_FILENAMES[0]
    unrelated = out / "notes.txt"
    owned.parent.mkdir(parents=True)
    owned.write_text("owned\n", encoding="utf-8")
    unrelated.write_text("keep\n", encoding="utf-8")

    figures_v1.prepare_analysis_v1_figure_outputs(out, force=True)

    assert not owned.exists()
    assert unrelated.read_text(encoding="utf-8") == "keep\n"


def test_standalone_orchestration_invokes_each_v1_generator_once(
    tmp_path,
    monkeypatch,
) -> None:
    input_csv = tmp_path / "analysis.csv"
    input_csv.write_text("sample_uid\n", encoding="utf-8")
    out = tmp_path / "custom_figures"
    calls = []
    filenames = EXPECTED_ANALYSIS_V1_FIGURE_FILENAMES
    chunks = [
        filenames[0:3],
        filenames[3:7],
        filenames[7:9],
        filenames[9:11],
        filenames[11:13],
        filenames[13:15],
    ]

    def fake_generator_factory(index, names):
        def fake_generator(input_path, output_dir):
            input_path = Path(input_path)
            output_dir = Path(output_dir)
            calls.append((index, input_path, output_dir))
            outputs = []
            for name in names:
                path = output_dir / name
                path.write_text(name, encoding="utf-8")
                outputs.append(path)
            return tuple(outputs)

        return fake_generator

    monkeypatch.setattr(
        figures_v1,
        "ANALYSIS_V1_FIGURE_GENERATORS",
        tuple(
            fake_generator_factory(index, names)
            for index, names in enumerate(chunks)
        ),
    )

    report = figures_v1.generate_analysis_v1_figures(
        input_csv=input_csv,
        output_dir=out,
    )

    assert [call[0] for call in calls] == list(range(6))
    assert {call[1] for call in calls} == {input_csv}
    assert {call[2] for call in calls} == {out}
    assert report.input_csv == input_csv
    assert report.output_dir == out
    assert report.output_files == figures_v1.owned_analysis_v1_figure_paths(out)
    assert not (tmp_path / "figures/unified_analysis_v1").exists()


def test_standalone_orchestration_respects_force_and_preserves_unrelated_files(
    tmp_path,
    monkeypatch,
) -> None:
    input_csv = tmp_path / "analysis.csv"
    input_csv.write_text("sample_uid\n", encoding="utf-8")
    out = tmp_path / "out"
    existing = out / EXPECTED_ANALYSIS_V1_FIGURE_FILENAMES[0]
    unrelated = out / "notes.txt"
    existing.parent.mkdir(parents=True)
    existing.write_text("old\n", encoding="utf-8")
    unrelated.write_text("keep\n", encoding="utf-8")

    def fake_generator(input_path, output_dir):
        outputs = figures_v1.owned_analysis_v1_figure_paths(output_dir)
        for path in outputs:
            path.write_text("new\n", encoding="utf-8")
        return outputs

    monkeypatch.setattr(
        figures_v1,
        "ANALYSIS_V1_FIGURE_GENERATORS",
        (fake_generator,),
    )

    figures_v1.generate_analysis_v1_figures(
        input_csv=input_csv,
        output_dir=out,
        force=True,
    )

    assert existing.read_text(encoding="utf-8") == "new\n"
    assert unrelated.read_text(encoding="utf-8") == "keep\n"


def test_reusable_figure_module_uses_explicit_paths_not_legacy_defaults() -> None:
    source = Path(figures_v1.__file__).read_text(encoding="utf-8")

    assert "repository_root_from_script" not in source
    assert "unified_analysis_v1_path" not in source
    assert "unified_analysis_figure_dir" not in source
    assert "runs/analysis_v1/unified_analysis_v1.csv" not in source
    assert "figures/unified_analysis_v1" not in source


def test_six_scripts_are_thin_reusable_wrappers() -> None:
    root = Path(__file__).resolve().parents[1]
    scripts_dir = root / "scripts" / "illustrations"

    for filename, generator_name in MIGRATED_V1_WRAPPERS.items():
        source = (scripts_dir / filename).read_text(encoding="utf-8")
        assert "from mvpipeline.analysis.figures_v1 import" in source
        assert generator_name in source
        assert "pd.read_csv" not in source
        assert "plt.subplots" not in source
        assert "matplotlib.use" not in source


def test_actual_plot_functions_close_figures() -> None:
    source = Path(figures_v1.__file__).read_text(encoding="utf-8")

    assert source.count("plt.close(fig)") >= 6


def test_dxmag_axis_label_matches_frozen_text() -> None:
    label = figures_v1.DXMAG_PREDICTED_MOMENT_YLABEL

    assert label == "DXMag predicted moment (μB/f.u.)"
    assert label[label.index("(") + 1] == "μ"
    assert ord(label[label.index("(") + 1]) == 0x03BC
