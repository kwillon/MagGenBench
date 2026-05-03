from pathlib import Path
import pandas as pd
import numpy as np
from pymatgen.core import Composition


ROOT = Path("/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench")

GEN_CSV = ROOT / "tables" / "benchmark_ready_generated.csv"
MP_CSV = ROOT / "tables" / "mp_reference_for_benchmark.csv"


def reduced_formula(x):
    try:
        return Composition(str(x)).reduced_formula
    except Exception:
        return str(x).strip()


def norm_numeric(df, cols):
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def strict_match(row, ref):
    if any(pd.isna(row[x]) or pd.isna(ref[x]) for x in ["a", "b", "c", "alpha", "beta", "gamma"]):
        return False

    length_ok = (
        abs(row["a"] - ref["a"]) / ref["a"] <= 0.05
        and abs(row["b"] - ref["b"]) / ref["b"] <= 0.05
        and abs(row["c"] - ref["c"]) / ref["c"] <= 0.05
    )

    angle_ok = (
        abs(row["alpha"] - ref["alpha"]) <= 2.0
        and abs(row["beta"] - ref["beta"]) <= 2.0
        and abs(row["gamma"] - ref["gamma"]) <= 2.0
    )

    return bool(length_ok and angle_ok)


def main():
    gen = pd.read_csv(GEN_CSV, low_memory=False)
    mp = pd.read_csv(MP_CSV, low_memory=False)

    numeric_cols = ["spacegroup", "a", "b", "c", "alpha", "beta", "gamma"]
    gen = norm_numeric(gen, numeric_cols)
    mp = norm_numeric(mp, numeric_cols)

    gen["formula"] = gen["formula"].map(reduced_formula)
    mp["formula"] = mp["formula"].map(reduced_formula)

    mp_formulas = set(mp["formula"].dropna())
    mp_formula_sg = set(zip(mp["formula"], mp["spacegroup"]))

    rows = []

    for model, d in gen.groupby("model"):
        formula_hit = 0
        formula_sg_hit = 0
        strict_hit = 0

        for _, row in d.iterrows():
            f = row["formula"]
            sg = row["spacegroup"]

            if f in mp_formulas:
                formula_hit += 1

            refs = mp[(mp["formula"] == f) & (mp["spacegroup"] == sg)]

            if len(refs) > 0:
                formula_sg_hit += 1

                if any(strict_match(row, ref) for _, ref in refs.iterrows()):
                    strict_hit += 1

        n = len(d)

        rows.append({
            "Model": model,
            "N": n,
            "Formula hit %": 100 * formula_hit / n,
            "Formula+SG hit %": 100 * formula_sg_hit / n,
            "Strict hit %": 100 * strict_hit / n,
            "Formula hit N": formula_hit,
            "Formula+SG hit N": formula_sg_hit,
            "Strict hit N": strict_hit,
        })

    out = pd.DataFrame(rows)
    print(out.to_string(index=False))

    out_path = ROOT / "tables" / "debug_mp_hits.csv"
    out.to_csv(out_path, index=False)
    print("\nSaved:", out_path)


if __name__ == "__main__":
    main()