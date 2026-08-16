from pathlib import Path


CRYSJEPA_PREPARERS = {
    "base": {
        "path": Path("scripts/crysjepa/prepare_crysjepa_base_annotations.py"),
        "input": 'ROOT / "outputs/crysjepa_base/all_structures.csv"',
        "adapted": '"crysjepa_base_with_classes.csv"',
        "enriched": '"crysjepa_base_enrichment_annotations.csv"',
        "model_name": '"Crys-JEPA-Base"',
        "model_short": '"crysjepa_base"',
        "run_uid_a": '"crysjepa_base_mp20_release_"',
        "run_uid_b": '"seed17_bench2000"',
        "pass_label": '"CRYSJEPA_BASE_ANNOTATIONS: PASSED"',
    },
    "refined": {
        "path": Path("scripts/crysjepa/prepare_crysjepa_refined_annotations.py"),
        "input": 'ROOT / "outputs/crysjepa_refined/all_structures.csv"',
        "adapted": '"crysjepa_refined_with_classes.csv"',
        "enriched": '"crysjepa_refined_enrichment_annotations.csv"',
        "model_name": '"Crys-JEPA-Refined"',
        "model_short": '"crysjepa_refined"',
        "run_uid_a": '"crysjepa_refined_mp20_release_"',
        "run_uid_b": '"seed17_bench2000"',
        "pass_label": '"CRYSJEPA_REFINED_ANNOTATIONS: PASSED"',
    },
}


def script_text(path):
    repo_root = Path(__file__).resolve().parents[1]
    return (repo_root / path).read_text(encoding="utf-8")


def test_active_crysjepa_preparers_use_canonical_classifier():
    for spec in CRYSJEPA_PREPARERS.values():
        text = script_text(spec["path"])

        assert (
            "from mvpipeline.annotations.compound_class import classify_formula"
            in text
        )
        assert "from add_compound_class import classify_formula" not in text
        assert 'ROOT / "scripts" / "legacy"' not in text
        assert '"compound_class": classify_formula(formula)' in text


def test_active_crysjepa_annotation_constants_are_unchanged():
    for spec in CRYSJEPA_PREPARERS.values():
        text = script_text(spec["path"])

        assert spec["input"] in text
        assert spec["adapted"] in text
        assert spec["enriched"] in text
        assert spec["model_name"] in text
        assert spec["model_short"] in text
        assert spec["run_uid_a"] in text
        assert spec["run_uid_b"] in text
        assert "EXPECTED_TOTAL = 2000" in text
        assert "sample_uid = stem" in text
        assert spec["pass_label"] in text

