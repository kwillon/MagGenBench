from __future__ import annotations

from pymatgen.core import Composition, Element  # type: ignore


HALOGENS = {"F", "Cl", "Br", "I"}
CHALCOGENS_NO_O = {"S", "Se", "Te"}
PNICTOGENS = {"N", "P", "As", "Sb", "Bi"}

COMMON_GASES = {
    "H2",
    "N2",
    "O2",
    "F2",
    "Cl2",
    "He",
    "Ne",
    "Ar",
    "Kr",
    "Xe",
    "Rn",
    "CO",
    "CO2",
    "NO",
    "NO2",
    "N2O",
    "SO2",
    "SO3",
    "NH3",
    "CH4",
    "H2S",
}

COMMON_ACIDS = {
    "HF",
    "HCl",
    "HBr",
    "HI",
    "H2S",
    "HNO2",
    "HNO3",
    "H2SO3",
    "H2SO4",
    "H2CO3",
    "H3PO3",
    "H3PO4",
    "HClO",
    "HClO2",
    "HClO3",
    "HClO4",
}

ALKALI = {"Li", "Na", "K", "Rb", "Cs", "Fr"}
ALKALINE_EARTH = {"Be", "Mg", "Ca", "Sr", "Ba", "Ra"}


def norm(x):
    if x is None:
        return ""
    x = str(x).strip()
    if not x or x.lower() in {"nan", "none", "null"}:
        return ""
    return x


def is_metal(symbol: str) -> bool:
    try:
        return Element(symbol).is_metal
    except Exception:
        return False


def classify_formula(formula: str) -> str:
    """
    Rough formula-based classification for visualization.
    It is intentionally heuristic, not a strict chemical ontology.
    """
    formula = norm(formula)

    if not formula:
        return "unknown"

    try:
        comp = Composition(formula)
        reduced = comp.reduced_formula
        elements = {el.symbol for el in comp.elements}
    except Exception:
        return "unknown"

    n_el = len(elements)

    metals = {e for e in elements if is_metal(e)}
    nonmetals = elements - metals

    has_H = "H" in elements
    has_O = "O" in elements
    has_C = "C" in elements
    has_B = "B" in elements
    has_Si = "Si" in elements
    has_halogen = bool(elements & HALOGENS)
    has_chalcogen_no_o = bool(elements & CHALCOGENS_NO_O)
    has_pnictogen = bool(elements & PNICTOGENS)

    # 1. Explicit common gases.
    if reduced in COMMON_GASES:
        return "gas"

    # 2. Single-element cases.
    if n_el == 1:
        only = next(iter(elements))
        if is_metal(only):
            return "metal"
        return "elemental nonmetal"

    # 3. Explicit common acids.
    if reduced in COMMON_ACIDS:
        return "acid"

    # 4. Hydroxides / bases.
    # Examples: NaOH, KOH, Ca(OH)2, Fe(OH)3.
    # In reduced formula they may appear as HFeO2, H3FeO3, etc.
    if metals and has_H and has_O and not has_C:
        return "hydroxide/base"

    # 5. Intermetallics: only metals, at least two elements.
    if n_el >= 2 and not nonmetals:
        return "intermetallic"

    # 6. Oxides and oxo-salts.
    if metals and has_O:
        if has_C:
            return "carbonate/oxo-carbon compound"
        if "S" in elements:
            return "sulfate/sulfite"
        if "N" in elements:
            return "nitrate/nitrite"
        if "P" in elements:
            return "phosphate"
        if has_halogen:
            return "oxyhalide"
        return "oxide"

    # 7. Halides.
    if metals and has_halogen and not has_O:
        return "halide"

    # 8. Chalcogenides excluding oxides.
    if metals and has_chalcogen_no_o and not has_O:
        return "chalcogenide"

    # 9. Nitrides / pnictides.
    if metals and has_pnictogen and not has_O:
        if "N" in elements:
            return "nitride"
        return "pnictide"

    # 10. Carbides.
    if metals and has_C and not has_O:
        return "carbide"

    # 11. Hydrides.
    if metals and has_H and not has_O:
        return "hydride"

    # 12. Borides and silicides.
    if metals and has_B and not has_O:
        return "boride"

    if metals and has_Si and not has_O:
        return "silicide"

    # 13. Organic or molecular compounds.
    if has_C and has_H and not metals:
        return "organic/molecular"

    # 14. General salt / ionic inorganic.
    if metals and nonmetals:
        return "salt/ionic compound"

    return "other inorganic"

