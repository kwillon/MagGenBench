import importlib.util
from pathlib import Path

from mvpipeline.annotations.compound_class import classify_formula


REPRESENTATIVE_FORMULAS = [
    "",
    "H2",
    "Fe",
    "O",
    "HCl",
    "NaOH",
    "FeNi",
    "Fe2O3",
    "CaCO3",
    "Na2SO4",
    "NaNO3",
    "Li3PO4",
    "FeOCl",
    "NaCl",
    "FeS",
    "FeN",
    "FeP",
    "Fe3C",
    "LiH",
    "FeB",
    "FeSi",
    "C2H6",
    "NaHe",
    "BN",
]


def legacy_classify_formula():
    repo_root = Path(__file__).resolve().parents[1]
    legacy_path = repo_root / "scripts" / "legacy" / "add_compound_class.py"
    spec = importlib.util.spec_from_file_location(
        "legacy_add_compound_class",
        legacy_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.classify_formula


def test_compound_class_representative_labels():
    assert classify_formula("") == "unknown"
    assert classify_formula("H2") == "gas"
    assert classify_formula("Fe") == "metal"
    assert classify_formula("O") == "elemental nonmetal"
    assert classify_formula("HCl") == "acid"
    assert classify_formula("NaOH") == "hydroxide/base"
    assert classify_formula("FeNi") == "intermetallic"
    assert classify_formula("Fe2O3") == "oxide"
    assert classify_formula("CaCO3") == "carbonate/oxo-carbon compound"
    assert classify_formula("Na2SO4") == "sulfate/sulfite"
    assert classify_formula("NaNO3") == "nitrate/nitrite"
    assert classify_formula("Li3PO4") == "phosphate"
    assert classify_formula("FeOCl") == "oxyhalide"
    assert classify_formula("NaCl") == "halide"
    assert classify_formula("FeS") == "chalcogenide"
    assert classify_formula("FeN") == "nitride"
    assert classify_formula("FeP") == "pnictide"
    assert classify_formula("Fe3C") == "carbide"
    assert classify_formula("LiH") == "hydride"
    assert classify_formula("FeB") == "boride"
    assert classify_formula("FeSi") == "silicide"
    assert classify_formula("C2H6") == "organic/molecular"
    assert classify_formula("NaHe") == "salt/ionic compound"
    assert classify_formula("BN") == "other inorganic"


def test_new_compound_classifier_matches_legacy_for_representative_formulas():
    legacy = legacy_classify_formula()

    for formula in REPRESENTATIVE_FORMULAS:
        assert classify_formula(formula) == legacy(formula)
