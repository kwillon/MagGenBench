from pathlib import Path
import os
import json
import time

import pandas as pd
from pymatgen.core import Composition
from mp_api.client import MPRester


ROOT = Path("/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench")

INPUT_CSV = ROOT / "tables" / "benchmark_ready_generated.csv"
OUT_CSV = ROOT / "tables" / "mp_reference_for_benchmark.csv"
CACHE_JSON = ROOT / "tables" / "mp_reference_for_benchmark.cache.json"


FIELDS = [
    "material_id",
    "formula_pretty",
    "symmetry",
    "structure",
]


def reduced_formula(x):
    try:
        return Composition(str(x)).reduced_formula
    except Exception:
        return str(x).strip()


def load_cache():
    if CACHE_JSON.exists():
        with open(CACHE_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_JSON, "w", encoding="utf-8") as f:
        json.dump(cache, f)


def get_sg_number(doc):
    sym = getattr(doc, "symmetry", None)

    if sym is None:
        return None

    if isinstance(sym, dict):
        return sym.get("number") or sym.get("space_group_number")

    return getattr(sym, "number", None)


def doc_to_rows(formula_query, docs):
    rows = []

    for doc in docs:
        structure = getattr(doc, "structure", None)
        if structure is None:
            continue

        lattice = structure.lattice

        formula_mp = getattr(doc, "formula_pretty", None)
        material_id = str(getattr(doc, "material_id", ""))

        try:
            formula_reduced = Composition(str(formula_mp)).reduced_formula
        except Exception:
            formula_reduced = reduced_formula(formula_query)

        rows.append({
            "formula": formula_reduced,
            "mp_formula_pretty": formula_mp,
            "material_id": material_id,
            "spacegroup": get_sg_number(doc),
            "a": float(lattice.a),
            "b": float(lattice.b),
            "c": float(lattice.c),
            "alpha": float(lattice.alpha),
            "beta": float(lattice.beta),
            "gamma": float(lattice.gamma),
        })

    return rows


def main():
    api_key = os.environ.get("MP_API_KEY") or os.environ.get("MAPI_KEY")
    if not api_key:
        raise SystemExit("Set MP_API_KEY first: export MP_API_KEY=...")

    df = pd.read_csv(INPUT_CSV, low_memory=False)

    formulas = (
        df["formula"]
        .dropna()
        .astype(str)
        .map(reduced_formula)
        .drop_duplicates()
        .tolist()
    )

    print(f"Unique formulas to query: {len(formulas)}")

    cache = load_cache()

    with MPRester(api_key) as mpr:
        for i, formula in enumerate(formulas, 1):
            if formula in cache:
                if i % 50 == 0:
                    print(f"{i}/{len(formulas)} cached")
                continue

            try:
                docs = mpr.materials.summary.search(
                    formula=formula,
                    fields=FIELDS,
                )
                rows = doc_to_rows(formula, docs)
                cache[formula] = rows
            except Exception as e:
                print(f"[warn] failed for {formula}: {e}")
                cache[formula] = []

            if i % 10 == 0:
                save_cache(cache)

            if i % 25 == 0:
                print(f"{i}/{len(formulas)}")

            time.sleep(0.15)

    save_cache(cache)

    all_rows = []
    for formula, rows in cache.items():
        all_rows.extend(rows)

    out = pd.DataFrame(all_rows)

    if out.empty:
        raise RuntimeError("MP reference is empty. Check MP_API_KEY and formulas.")

    out = out.drop_duplicates()
    out.to_csv(OUT_CSV, index=False)

    print(f"Saved: {OUT_CSV}")
    print(f"Rows: {len(out)}")


if __name__ == "__main__":
    main()