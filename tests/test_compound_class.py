from mvpipeline.annotations.compound_class import classify_formula


def test_compound_class_representative_labels():
    expected = {
        "": "unknown",
        "H2": "gas",
        "Fe": "metal",
        "O": "gas",
        "B": "elemental nonmetal",
        "HCl": "acid",
        "NaOH": "hydroxide/base",
        "FeNi": "intermetallic",
        "Fe2O3": "oxide",
        "CaCO3": "carbonate/oxo-carbon compound",
        "Na2SO4": "sulfate/sulfite",
        "NaNO3": "nitrate/nitrite",
        "Li3PO4": "phosphate",
        "FeOCl": "oxyhalide",
        "NaCl": "halide",
        "FeS": "chalcogenide",
        "FeN": "nitride",
        "FeP": "pnictide",
        "Fe3C": "carbide",
        "LiH": "hydride",
        "FeB": "boride",
        "FeSi": "silicide",
        "C2H6": "organic/molecular",
        "NaHe": "salt/ionic compound",
        "BN": "other inorganic",
    }

    for formula, label in expected.items():
        assert classify_formula(formula) == label
