from pathlib import Path
import csv
from collections import Counter, defaultdict

from pymatgen.core import Composition, Element # type: ignore


ROOT = Path("/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench")

INPUT_CSV = ROOT / "tables" / "master_structures.downsampled.with_status.csv"
OUT_CSV = ROOT / "tables" / "master_structures.downsampled.with_status.classes.csv"


HALOGENS = {"F", "Cl", "Br", "I"}
CHALCOGENS_NO_O = {"S", "Se", "Te"}
PNICTOGENS = {"N", "P", "As", "Sb", "Bi"}

COMMON_GASES = {
    "H2", "N2", "O2", "F2", "Cl2",
    "He", "Ne", "Ar", "Kr", "Xe", "Rn",
    "CO", "CO2", "NO", "NO2", "N2O",
    "SO2", "SO3", "NH3", "CH4", "H2S",
}

COMMON_ACIDS = {
    "HF", "HCl", "HBr", "HI",
    "H2S",
    "HNO2", "HNO3",
    "H2SO3", "H2SO4",
    "H2CO3",
    "H3PO3", "H3PO4",
    "HClO", "HClO2", "HClO3", "HClO4",
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


def get_cell(row, header, name):
    if name not in header:
        return ""
    idx = header.index(name)
    if idx >= len(row):
        return ""
    return row[idx]


def main():
    counts = Counter()
    by_model = defaultdict(Counter)
    by_status = defaultdict(Counter)

    with open(INPUT_CSV, "r", encoding="utf-8", errors="replace", newline="") as fin, \
         open(OUT_CSV, "w", encoding="utf-8", newline="") as fout:

        reader = csv.reader(fin)
        writer = csv.writer(fout)

        header = [h.strip() for h in next(reader)]

        if "formula_reduced" not in header:
            raise ValueError("Column formula_reduced was not found")

        writer.writerow(header + ["compound_class"])

        for row in reader:
            formula = get_cell(row, header, "formula_reduced")
            compound_class = classify_formula(formula)

            counts[compound_class] += 1

            model = get_cell(row, header, "model_short") or get_cell(row, header, "model_name")
            status = get_cell(row, header, "status")

            if model:
                by_model[model][compound_class] += 1

            if status:
                by_status[status][compound_class] += 1

            writer.writerow(row + [compound_class])

    print("Saved:")
    print(OUT_CSV)

    print("\nCompound class counts:")
    for cls, n in counts.most_common():
        print(f"{cls}: {n}")

    print("\nCompound class counts by model:")
    for model, counter in by_model.items():
        print(f"\n{model}")
        for cls, n in counter.most_common():
            print(f"  {cls}: {n}")

    print("\nCompound class counts by status:")
    for status, counter in by_status.items():
        print(f"\n{status}")
        for cls, n in counter.most_common():
            print(f"  {cls}: {n}")


if __name__ == "__main__":
    main()