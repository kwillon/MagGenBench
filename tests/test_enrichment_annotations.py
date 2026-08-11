import csv
import json
import os
import subprocess
import sys
import textwrap
import warnings
from pathlib import Path

import pytest

from mvpipeline.magnetism.config import load_magnetism_config
from mvpipeline.pipeline.enrichment_annotations import (
    ANNOTATION_FIELDS,
    CompoundClassRules,
    EnrichmentAnnotationConfig,
    MagneticAnnotationConfig,
    classify_compound_class,
    enrich_manifest_rows,
    enrichment_annotation_config_from_magnetism_config,
    load_enrichment_annotation_config,
    output_fieldnames,
    run_enrichment_annotations,
)


class FakeElement:
    def __init__(self, symbol):
        self.symbol = symbol


class FakeComposition:
    def __init__(self, amounts):
        self._amounts = dict(amounts)
        self.num_atoms = sum(float(value) for value in amounts.values())
        self.elements = [FakeElement(symbol) for symbol in amounts]


class FakeSite:
    def __init__(self, species):
        self.species = dict(species)


class FakeStructure:
    def __init__(self, amounts, sites, volume=40.0, density=5.0):
        self.composition = FakeComposition(amounts)
        self._sites = list(sites)
        self.volume = volume
        self.density = density

    def __len__(self):
        return len(self._sites)

    def __iter__(self):
        return iter(self._sites)


TEST_CONFIG = EnrichmentAnnotationConfig(
    magnetic=MagneticAnnotationConfig(
        transition_3d=frozenset({"Fe"}),
        selected_4d_5d=frozenset({"Ru"}),
        lanthanides=frozenset({"Gd"}),
    ),
    class_rules=CompoundClassRules(
        high_priority=frozenset({"oxide", "halide"}),
        low_priority=frozenset({"salt/ionic compound"}),
        rejected=frozenset({"gas", "hydroxide/base"}),
    ),
)


def base_row(sample_uid="s1", compound_class="oxide", cif_path="s1.cif"):
    return {
        "sample_uid": sample_uid,
        "model_name": "Model A",
        "model_short": "ma",
        "run_uid": "run-1",
        "source_sample_id": "src-1",
        "cif_path": cif_path,
        "cif_file_name": Path(cif_path).name,
        "formula_reduced": "FeO",
        "formula_full": "Fe1 O1",
        "status": "validated",
        "status_source": "table03",
        "rejection_reason": "",
        "compound_class": compound_class,
        "n_atoms": "legacy",
        "volume": "legacy-volume",
        "density": "legacy-density",
        "volume_per_atom": "legacy-vpa",
        "spacegroup_number": "legacy-sg",
        "spacegroup_symbol": "legacy-symbol",
    }


def ordered_structure():
    return FakeStructure(
        {"Fe": 1, "O": 1},
        [FakeSite({"Fe": 1}), FakeSite({"O": 1})],
        volume=20.0,
        density=7.5,
    )


def partial_structure():
    return FakeStructure(
        {"Fe": 0.5, "O": 1, "Gd": 0.5},
        [FakeSite({"Fe": 0.5, "Gd": 0.5}), FakeSite({"O": 1})],
        volume=30.0,
        density=6.0,
    )


def symmetry_ok(structure):
    return {
        "crystal_system": "cubic",
        "point_group_symbol": "m-3m",
        "space_group_number_recomputed": 225,
        "space_group_symbol_recomputed": "Fm-3m",
    }


def test_ordered_structure_descriptors_and_symmetry_fields():
    rows = enrich_manifest_rows(
        [base_row()],
        structure_loader=lambda path: ordered_structure(),
        symmetry_analyzer=symmetry_ok,
        config=TEST_CONFIG,
    )
    row = rows[0]

    assert row["structure_id"] == "s1"
    assert row["cif_load_status"] == "ok"
    assert row["cif_warning_count"] == 0
    assert json.loads(row["cif_warnings"]) == []
    assert row["n_sites"] == 2
    assert row["composition_num_atoms"] == 2.0
    assert row["volume_A3"] == 20.0
    assert row["volume_per_site_A3"] == 10.0
    assert row["volume_per_composition_atom_A3"] == 10.0
    assert row["density_g_cm3"] == 7.5
    assert row["crystal_system"] == "cubic"
    assert row["point_group_symbol"] == "m-3m"
    assert row["space_group_number_recomputed"] == 225
    assert row["space_group_symbol_recomputed"] == "Fm-3m"
    assert row["descriptor_status"] == "ok"
    assert row["descriptor_source"] == "cif_recomputed"
    assert row["n_atoms"] == "legacy"
    assert row["volume"] == "legacy-volume"



def test_recomputed_formula_comes_from_loaded_structure_not_legacy_metadata():
    structure = ordered_structure()
    structure.composition.reduced_formula = "FeO2"
    structure.composition.formula = "Fe1 O2"

    legacy = base_row()
    legacy["formula_reduced"] = "FeO"
    legacy["formula_full"] = "Fe1 O1"

    row = enrich_manifest_rows(
        [legacy],
        structure_loader=lambda path: structure,
        symmetry_analyzer=symmetry_ok,
        config=TEST_CONFIG,
    )[0]

    assert row["formula_reduced"] == "FeO"
    assert row["formula_full"] == "Fe1 O1"
    assert row["formula_reduced_recomputed"] == "FeO2"
    assert row["formula_full_recomputed"] == "Fe1 O2"


def test_cif_loader_warning_success_records_warning_and_runs_magnetic_annotations():
    def loader(path):
        warnings.warn("occupancy adjusted", UserWarning)
        return ordered_structure()

    row = enrich_manifest_rows(
        [base_row()],
        structure_loader=loader,
        symmetry_analyzer=symmetry_ok,
        config=TEST_CONFIG,
    )[0]

    assert row["cif_load_status"] == "ok_with_warnings"
    assert row["cif_warning_count"] == 1
    assert json.loads(row["cif_warnings"]) == [
        {"category": "UserWarning", "message": "occupancy adjusted"}
    ]
    assert row["descriptor_status"] == "ok"
    assert row["magnetic_screening_status"] == "candidate"


def test_cif_loader_warning_order_is_preserved():
    def loader(path):
        warnings.warn("first warning", UserWarning)
        warnings.warn("second warning", RuntimeWarning)
        return ordered_structure()

    row = enrich_manifest_rows(
        [base_row()],
        structure_loader=loader,
        symmetry_analyzer=symmetry_ok,
        config=TEST_CONFIG,
    )[0]

    assert json.loads(row["cif_warnings"]) == [
        {"category": "UserWarning", "message": "first warning"},
        {"category": "RuntimeWarning", "message": "second warning"},
    ]


def test_cif_loader_warning_then_error_preserves_row_and_warning():
    def loader(path):
        warnings.warn("partial CIF read before failure", UserWarning)
        raise ValueError("bad cif")

    row = enrich_manifest_rows(
        [base_row()],
        structure_loader=loader,
        symmetry_analyzer=symmetry_ok,
        config=TEST_CONFIG,
    )[0]

    assert row["sample_uid"] == "s1"
    assert row["structure_id"] == "s1"
    assert row["cif_load_status"] == "error"
    assert row["cif_warning_count"] == 1
    assert json.loads(row["cif_warnings"]) == [
        {"category": "UserWarning", "message": "partial CIF read before failure"}
    ]
    assert row["descriptor_status"] == "error"
    assert row["descriptor_error_code"] == "cif_parse_error"
    assert row["magnetic_screening_status"] == "not_evaluated"
    assert row["magnetic_screening_reason"] == "cif_parse_failed"


def test_cif_loader_warnings_are_captured_without_stderr(capsys):
    def loader(path):
        warnings.warn("captured warning", UserWarning)
        return ordered_structure()

    enrich_manifest_rows(
        [base_row()],
        structure_loader=loader,
        symmetry_analyzer=symmetry_ok,
        config=TEST_CONFIG,
    )

    captured = capsys.readouterr()
    assert "captured warning" not in captured.err


def test_partial_occupancy_site_and_species_counts():
    rows = enrich_manifest_rows(
        [base_row()],
        structure_loader=lambda path: partial_structure(),
        symmetry_analyzer=symmetry_ok,
        config=TEST_CONFIG,
    )
    row = rows[0]

    assert row["n_sites"] == 2
    assert row["composition_num_atoms"] == 2.0
    assert row["magnetic_elements"] == '["Fe", "Gd"]'
    assert row["magnetic_element_species_count"] == 2
    assert row["magnetic_element_site_count"] == 1


def test_symmetry_failure_preserves_basic_descriptors():
    def symmetry_fail(structure):
        raise RuntimeError("spglib failed")

    row = enrich_manifest_rows(
        [base_row()],
        structure_loader=lambda path: ordered_structure(),
        symmetry_analyzer=symmetry_fail,
        config=TEST_CONFIG,
    )[0]

    assert row["n_sites"] == 2
    assert row["volume_A3"] == 20.0
    assert row["density_g_cm3"] == 7.5
    assert row["descriptor_status"] == "partial"
    assert row["descriptor_error_code"] == "symmetry_analysis_error"
    assert "spglib failed" in row["descriptor_error_message"]


def test_cif_parse_failure_preserves_row_and_marks_not_evaluated():
    row = enrich_manifest_rows(
        [base_row()],
        structure_loader=lambda path: (_ for _ in ()).throw(ValueError("bad cif")),
        symmetry_analyzer=symmetry_ok,
        config=TEST_CONFIG,
    )[0]

    assert row["sample_uid"] == "s1"
    assert row["structure_id"] == "s1"
    assert row["cif_load_status"] == "error"
    assert row["cif_warning_count"] == 0
    assert json.loads(row["cif_warnings"]) == []
    assert row["descriptor_status"] == "error"
    assert row["descriptor_error_code"] == "cif_parse_error"
    assert row["magnetic_screening_status"] == "not_evaluated"
    assert row["magnetic_screening_reason"] == "cif_parse_failed"


def test_magnetic_composition_reasons_are_deterministic():
    fe = enrich_manifest_rows(
        [base_row("fe")],
        structure_loader=lambda path: ordered_structure(),
        symmetry_analyzer=symmetry_ok,
        config=TEST_CONFIG,
    )[0]
    gd = enrich_manifest_rows(
        [base_row("gd")],
        structure_loader=lambda path: FakeStructure(
            {"Gd": 1, "O": 1}, [FakeSite({"Gd": 1}), FakeSite({"O": 1})]
        ),
        symmetry_analyzer=symmetry_ok,
        config=TEST_CONFIG,
    )[0]
    ru = enrich_manifest_rows(
        [base_row("ru")],
        structure_loader=lambda path: FakeStructure(
            {"Ru": 1, "O": 1}, [FakeSite({"Ru": 1}), FakeSite({"O": 1})]
        ),
        symmetry_analyzer=symmetry_ok,
        config=TEST_CONFIG,
    )[0]
    no_mag = enrich_manifest_rows(
        [base_row("si")],
        structure_loader=lambda path: FakeStructure(
            {"Si": 1, "O": 2}, [FakeSite({"Si": 1}), FakeSite({"O": 1})]
        ),
        symmetry_analyzer=symmetry_ok,
        config=TEST_CONFIG,
    )[0]

    assert fe["magnetic_screening_reason"] == "contains_3d_element"
    assert gd["magnetic_screening_reason"] == "contains_4f_element"
    assert ru["magnetic_screening_reason"] == (
        "contains_other_configured_magnetic_element"
    )
    assert no_mag["magnetic_screening_status"] == "nonmagnetic_by_composition"
    assert no_mag["magnetic_screening_reason"] == "no_configured_magnetic_elements"
    assert no_mag["nonmagnetic_by_composition_heuristic"] is True


def test_compound_class_rules_include_unlisted_as_accepted():
    rules = TEST_CONFIG.class_rules
    assert classify_compound_class("oxide", rules) == (
        "high_priority",
        "compound_class_high_priority",
    )
    assert classify_compound_class("salt/ionic compound", rules) == (
        "low_priority",
        "compound_class_low_priority",
    )
    assert classify_compound_class("gas", rules) == (
        "rejected",
        "compound_class_rejected",
    )
    assert classify_compound_class("weird new class", rules) == (
        "accepted",
        "compound_class_unlisted",
    )


def test_row_preservation_order_and_sample_uid_structure_id_mapping():
    rows = [base_row("s1"), base_row("s2", compound_class="halide")]
    output = enrich_manifest_rows(
        rows,
        structure_loader=lambda path: ordered_structure(),
        symmetry_analyzer=symmetry_ok,
        config=TEST_CONFIG,
    )

    assert len(output) == len(rows)
    assert [row["sample_uid"] for row in output] == ["s1", "s2"]
    assert [row["structure_id"] for row in output] == ["s1", "s2"]


def test_duplicate_sample_uid_errors_before_output_replacement(tmp_path):
    input_path = tmp_path / "manifest.csv"
    output_path = tmp_path / "out.csv"
    output_path.write_text("old\n", encoding="utf-8")
    rows = [base_row("dup"), base_row("dup", cif_path="two.cif")]
    with input_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match="Duplicate sample_uid"):
        run_enrichment_annotations(
            input_path=input_path,
            output_path=output_path,
            structure_loader=lambda path: ordered_structure(),
            symmetry_analyzer=symmetry_ok,
            config=TEST_CONFIG,
        )

    assert output_path.read_text(encoding="utf-8") == "old\n"


def test_atomic_header_only_output_for_empty_input(tmp_path):
    input_path = tmp_path / "empty.csv"
    output_path = tmp_path / "out.csv"
    fieldnames = list(base_row())
    with input_path.open("w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=fieldnames).writeheader()

    report = run_enrichment_annotations(
        input_path=input_path,
        output_path=output_path,
        structure_loader=lambda path: ordered_structure(),
        symmetry_analyzer=symmetry_ok,
        config=TEST_CONFIG,
    )

    assert report.input_count == 0
    assert report.output_count == 0
    assert output_path.read_text(encoding="utf-8").splitlines()[0].split(",") == (
        fieldnames + [field for field in ANNOTATION_FIELDS if field not in fieldnames]
    )
    header = output_path.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert "cif_load_status" in header
    assert "cif_warning_count" in header
    assert "cif_warnings" in header


def test_output_fieldnames_contains_cif_warning_fields_once():
    fieldnames = output_fieldnames(["sample_uid", "cif_load_status"])

    assert fieldnames.count("cif_load_status") == 1
    assert fieldnames.count("cif_warning_count") == 1
    assert fieldnames.count("cif_warnings") == 1


def test_limit_is_deterministic():
    output = enrich_manifest_rows(
        [base_row("s1"), base_row("s2")],
        structure_loader=lambda path: ordered_structure(),
        symmetry_analyzer=symmetry_ok,
        config=TEST_CONFIG,
        limit=1,
    )

    assert [row["sample_uid"] for row in output] == ["s1"]


def test_custom_config_can_disable_default_magnetic_elements():
    config = EnrichmentAnnotationConfig(
        magnetic=MagneticAnnotationConfig(
            transition_3d=frozenset(),
            selected_4d_5d=frozenset(),
            lanthanides=frozenset(),
        )
    )
    row = enrich_manifest_rows(
        [base_row()],
        structure_loader=lambda path: ordered_structure(),
        symmetry_analyzer=symmetry_ok,
        config=config,
    )[0]

    assert row["contains_magnetic_element"] is False
    assert row["magnetic_screening_status"] == "nonmagnetic_by_composition"


def test_import_safety_for_enrichment_annotations():
    repo_root = Path(__file__).resolve().parents[1]
    script = textwrap.dedent(
        """
        import builtins
        import importlib
        import sys

        blocked = {"yaml", "pymatgen", "matminer", "sklearn", "lightgbm", "chgnet"}
        real_import = builtins.__import__

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            root = name.split(".", 1)[0]
            if level == 0 and root in blocked:
                raise AssertionError(f"{name} must not be imported")
            return real_import(name, globals, locals, fromlist, level)

        builtins.__import__ = guarded_import
        importlib.import_module("mvpipeline.pipeline.enrichment_annotations")
        assert not [m for m in sys.modules if m.split(".", 1)[0] in blocked]
        """
    )
    env = dict(os.environ)
    src_path = str(repo_root / "src")
    env["PYTHONPATH"] = (
        src_path
        if not env.get("PYTHONPATH")
        else src_path + os.pathsep + env["PYTHONPATH"]
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        env=env,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr


def write_yaml(path, text):
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")


def test_load_magnetism_config_parses_screening_sections(tmp_path):
    path = tmp_path / "magnetism.yaml"
    write_yaml(
        path,
        """
        magnetism:
          magnetic_elements:
            transition_3d: [Fe]
            selected_4d_5d: [Ru]
            lanthanides: [Gd]
          screening_rules:
            require_magnetic_element: true
            reject_classes: ["gas"]
            low_priority_classes: ["salt/ionic compound"]
            high_priority_classes: ["oxide"]
        """,
    )

    config = load_magnetism_config(path)

    assert config.magnetic_elements.transition_3d == ("Fe",)
    assert config.magnetic_elements.selected_4d_5d == ("Ru",)
    assert config.magnetic_elements.lanthanides == ("Gd",)
    assert config.magnetic_elements.all_elements == frozenset({"Fe", "Ru", "Gd"})
    assert config.screening_rules.reject_classes == ("gas",)
    assert config.screening_rules.low_priority_classes == ("salt/ionic compound",)
    assert config.screening_rules.high_priority_classes == ("oxide",)


def test_load_enrichment_annotation_config_converts_yaml(tmp_path):
    path = tmp_path / "magnetism.yaml"
    write_yaml(
        path,
        """
        magnetism:
          magnetic_elements:
            transition_3d: [Co]
            selected_4d_5d: [Os]
            lanthanides: [Dy]
          screening_rules:
            require_magnetic_element: true
            reject_classes: ["hydroxide/base"]
            low_priority_classes: ["salt/ionic compound"]
            high_priority_classes: ["oxide"]
        """,
    )

    config = load_enrichment_annotation_config(path, symprec=0.02)

    assert config.symprec == 0.02
    assert config.magnetic.transition_3d == frozenset({"Co"})
    assert config.magnetic.selected_4d_5d == frozenset({"Os"})
    assert config.magnetic.lanthanides == frozenset({"Dy"})
    assert config.class_rules.rejected == frozenset({"hydroxide/base"})
    assert config.class_rules.low_priority == frozenset({"salt/ionic compound"})
    assert config.class_rules.high_priority == frozenset({"oxide"})


def test_enrichment_annotation_config_from_magnetism_config_converts_object(tmp_path):
    path = tmp_path / "magnetism.yaml"
    write_yaml(
        path,
        """
        magnetism:
          magnetic_elements:
            transition_3d: [Ni]
            selected_4d_5d: []
            lanthanides: []
          screening_rules:
            require_magnetic_element: true
            reject_classes: []
            low_priority_classes: []
            high_priority_classes: ["halide"]
        """,
    )

    config = enrichment_annotation_config_from_magnetism_config(
        load_magnetism_config(path)
    )

    assert config.magnetic.transition_3d == frozenset({"Ni"})
    assert config.class_rules.high_priority == frozenset({"halide"})


def test_custom_yaml_controls_runtime_without_hidden_python_fallback(tmp_path):
    config_path = tmp_path / "magnetism.yaml"
    input_path = tmp_path / "manifest.csv"
    output_path = tmp_path / "out.csv"
    write_yaml(
        config_path,
        """
        magnetism:
          magnetic_elements:
            transition_3d: [Xx]
            selected_4d_5d: []
            lanthanides: []
          screening_rules:
            require_magnetic_element: true
            reject_classes: []
            low_priority_classes: []
            high_priority_classes: ["oxide"]
        """,
    )
    rows = [base_row("fe"), base_row("xx", cif_path="xx.cif")]
    with input_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    def loader(path):
        if path == "xx.cif":
            return FakeStructure({"Xx": 1}, [FakeSite({"Xx": 1})])
        return ordered_structure()

    run_enrichment_annotations(
        input_path=input_path,
        output_path=output_path,
        config_path=config_path,
        structure_loader=loader,
        symmetry_analyzer=symmetry_ok,
    )

    with output_path.open(newline="", encoding="utf-8") as f:
        output = list(csv.DictReader(f))

    assert output[0]["contains_magnetic_element"] == "False"
    assert output[0]["magnetic_screening_status"] == "nonmagnetic_by_composition"
    assert output[1]["contains_magnetic_element"] == "True"
    assert output[1]["magnetic_screening_reason"] == "contains_3d_element"


def test_repository_yaml_class_rules_are_annotate_only():
    config = load_enrichment_annotation_config("config/magnetism.yaml")
    rules = config.class_rules

    assert classify_compound_class("oxide", rules)[0] == "high_priority"
    assert classify_compound_class("salt/ionic compound", rules)[0] == "low_priority"
    assert classify_compound_class("hydroxide/base", rules)[0] == "rejected"
    assert classify_compound_class("metal", rules) == (
        "accepted",
        "compound_class_unlisted",
    )
