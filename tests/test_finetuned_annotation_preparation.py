from dataclasses import replace
from pathlib import Path

import pytest

from mvpipeline.annotations.finetuned import (
    CONCDVAE_FINETUNED,
    FINETUNED_ANNOTATION_FIELDS,
    FINETUNED_COHORTS,
    MATTERGEN_FINETUNED,
    build_finetuned_annotation_rows,
)


def input_row(
    structure_id,
    input_path,
    *,
    formula="FeO",
    status="validated",
):
    return {
        "structure_id": structure_id,
        "input_path": input_path,
        "reduced_formula": formula,
        "status": status,
        "rejection_reason": "",
        "is_suspicious": "False",
        "is_duplicate": "False",
        "is_novel": "True",
        "is_magnetic": "True",
        "n_atoms": "2",
        "density": "5.0",
        "volume_per_atom": "10.0",
        "spacegroup": "225",
        "min_distance": "2.1",
        "charge_solution_json": "{}",
        "details_json": "{}",
    }


def test_finetuned_cohort_configurations_are_exact():
    assert tuple(FINETUNED_COHORTS) == (
        "mattergen-finetuned",
        "concdvae-finetuned",
    )

    assert MATTERGEN_FINETUNED.input_path == Path(
        "outputs/mattergen_finetuned/all_structures.csv"
    )
    assert MATTERGEN_FINETUNED.adapted_output_path == Path(
        "tables/03_features/phase5b_mattergen_finetuned_with_classes.csv"
    )
    assert MATTERGEN_FINETUNED.enriched_output_path == Path(
        "tables/04_magnetic_screening/"
        "phase5b_mattergen_finetuned_enrichment_annotations.csv"
    )
    assert MATTERGEN_FINETUNED.sample_uid_prefix == "mattergen_ft__"
    assert MATTERGEN_FINETUNED.model_name == "MatterGen-finetuned"
    assert MATTERGEN_FINETUNED.model_short == "mg_ft"
    assert (
        MATTERGEN_FINETUNED.run_uid
        == "mattergen_finetuned_mag016_seed17_bench2000_from_prod2016"
    )
    assert MATTERGEN_FINETUNED.expected_total == 2000
    assert MATTERGEN_FINETUNED.pass_label == (
        "PHASE5B_MATTERGEN_ANNOTATIONS: PASSED"
    )

    assert CONCDVAE_FINETUNED.input_path == Path(
        "outputs/concdvae_finetuned/all_structures.csv"
    )
    assert CONCDVAE_FINETUNED.adapted_output_path == Path(
        "tables/03_features/phase5b_concdvae_finetuned_with_classes.csv"
    )
    assert CONCDVAE_FINETUNED.enriched_output_path == Path(
        "tables/04_magnetic_screening/"
        "phase5b_concdvae_finetuned_enrichment_annotations.csv"
    )
    assert CONCDVAE_FINETUNED.sample_uid_prefix == "concdvae_ft__"
    assert CONCDVAE_FINETUNED.model_name == "Con-CDVAE-finetuned"
    assert CONCDVAE_FINETUNED.model_short == "cdvae_ft"
    assert (
        CONCDVAE_FINETUNED.run_uid
        == "concdvae_finetuned_mag016_seed17_bench2000_from_prod2016"
    )
    assert CONCDVAE_FINETUNED.expected_total == 2000
    assert CONCDVAE_FINETUNED.pass_label == (
        "PHASE5B_CONCDVAE_ANNOTATIONS: PASSED"
    )


def test_finetuned_preparation_preserves_order_fields_and_ids(tmp_path):
    first_cif = tmp_path / "samples" / "first.cif"
    second_cif = tmp_path / "samples" / "second.cif"
    first_cif.parent.mkdir()
    first_cif.write_text("data_first\n", encoding="utf-8")
    second_cif.write_text("data_second\n", encoding="utf-8")

    cohort = replace(MATTERGEN_FINETUNED, expected_total=2)
    rows = [
        input_row(" run/a_first.cif ", "samples/first.cif", formula="FeO"),
        input_row("run/b_second.cif", "samples/second.cif", formula="NaCl"),
    ]

    adapted = build_finetuned_annotation_rows(
        rows,
        cohort=cohort,
        repo_root=tmp_path,
    )

    assert list(adapted[0]) == list(FINETUNED_ANNOTATION_FIELDS)
    assert [row["source_sample_id"] for row in adapted] == [
        "run/a_first.cif",
        "run/b_second.cif",
    ]
    assert [row["sample_uid"] for row in adapted] == [
        "mattergen_ft__a_first",
        "mattergen_ft__b_second",
    ]
    assert [row["compound_class"] for row in adapted] == ["oxide", "halide"]
    assert [row["cif_file_name"] for row in adapted] == [
        "first.cif",
        "second.cif",
    ]
    assert adapted[0]["model_name"] == "MatterGen-finetuned"
    assert adapted[0]["model_short"] == "mg_ft"
    assert adapted[0]["run_uid"] == MATTERGEN_FINETUNED.run_uid
    assert adapted[0]["status_source"] == "mvp_all_structures"
    assert adapted[0]["cif_path_original"] == "samples/first.cif"
    assert adapted[0]["cif_exists"] is True
    assert adapted[0]["mvp_n_atoms"] == "2"


def test_finetuned_preparation_uses_concdvae_identity(tmp_path):
    cif = tmp_path / "sample.cif"
    cif.write_text("data_sample\n", encoding="utf-8")
    cohort = replace(CONCDVAE_FINETUNED, expected_total=1)

    adapted = build_finetuned_annotation_rows(
        [input_row("concdvae/sample.cif", "sample.cif")],
        cohort=cohort,
        repo_root=tmp_path,
    )

    assert adapted[0]["sample_uid"] == "concdvae_ft__sample"
    assert adapted[0]["model_name"] == "Con-CDVAE-finetuned"
    assert adapted[0]["model_short"] == "cdvae_ft"
    assert adapted[0]["run_uid"] == CONCDVAE_FINETUNED.run_uid


def test_finetuned_preparation_rejects_duplicate_sample_uid(tmp_path):
    one = tmp_path / "one.cif"
    two = tmp_path / "two.cif"
    one.write_text("data_one\n", encoding="utf-8")
    two.write_text("data_two\n", encoding="utf-8")
    cohort = replace(MATTERGEN_FINETUNED, expected_total=2)

    with pytest.raises(RuntimeError, match="Duplicate sample_uid: mattergen_ft__same"):
        build_finetuned_annotation_rows(
            [
                input_row("a/same.cif", "one.cif"),
                input_row("b/same.cif", "two.cif"),
            ],
            cohort=cohort,
            repo_root=tmp_path,
        )


def test_finetuned_preparation_rejects_empty_structure_id(tmp_path):
    cif = tmp_path / "sample.cif"
    cif.write_text("data_sample\n", encoding="utf-8")
    cohort = replace(MATTERGEN_FINETUNED, expected_total=1)

    with pytest.raises(RuntimeError, match="Empty MVP structure_id"):
        build_finetuned_annotation_rows(
            [input_row(" ", "sample.cif")],
            cohort=cohort,
            repo_root=tmp_path,
        )


def test_finetuned_preparation_rejects_missing_cif(tmp_path):
    cohort = replace(MATTERGEN_FINETUNED, expected_total=1)

    with pytest.raises(FileNotFoundError):
        build_finetuned_annotation_rows(
            [input_row("missing.cif", "missing.cif")],
            cohort=cohort,
            repo_root=tmp_path,
        )


def test_finetuned_preparation_enforces_expected_total(tmp_path):
    cohort = replace(MATTERGEN_FINETUNED, expected_total=2)

    with pytest.raises(RuntimeError, match="Expected 2 MVP rows, got 1"):
        build_finetuned_annotation_rows(
            [input_row("missing.cif", "missing.cif")],
            cohort=cohort,
            repo_root=tmp_path,
        )


def test_phase5b_wrapper_uses_semantic_scripts_and_preserves_stage_order():
    repo_root = Path(__file__).resolve().parents[1]
    wrapper = (
        repo_root / "runs" / "annotations" / "finetuned" / "run.sh"
    ).read_text(encoding="utf-8")

    assert 'PYTHONPATH="$ROOT/src"' in wrapper
    assert "scripts/legacy" not in wrapper
    assert "scripts/phase5b/prepare_mattergen_finetuned_annotations.py" not in wrapper
    assert "scripts/phase5b/prepare_concdvae_finetuned_annotations.py" not in wrapper
    assert "scripts/phase5a6/prepare_production_manifest.py" not in wrapper
    assert "scripts/annotations/prepare_finetuned_annotations.py" in wrapper
    assert "scripts/annotations/prepare_production_manifest.py" in wrapper

    stage_needles = [
        "--cohort mattergen-finetuned",
        "phase5b_mattergen_finetuned_enrichment_annotations.csv",
        "--cohort concdvae-finetuned",
        "phase5b_concdvae_finetuned_enrichment_annotations.csv",
        "Final Phase 5B audit",
    ]
    positions = [wrapper.index(needle) for needle in stage_needles]
    assert positions == sorted(positions)


def test_semantic_annotation_run_path_replaces_old_active_path():
    repo_root = Path(__file__).resolve().parents[1]

    assert (repo_root / "runs" / "annotations" / "finetuned" / "run.sh").is_file()
    assert not (repo_root / "runs" / "phase5b_finetuned_annotations").exists()
