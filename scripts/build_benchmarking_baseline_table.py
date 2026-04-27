from pathlib import Path
import numpy as np
import pandas as pd
from pymatgen.core import Composition


ROOT = Path("/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench")

GEN_CSV = ROOT / "tables" / "benchmark_ready_generated.csv"
MP_REF_CSV = ROOT / "tables" / "mp_reference_for_benchmark.csv"
OUT_CSV = ROOT / "tables" / "benchmarking_baseline_table.csv"


MODEL_ORDER = [
    "CrystalFormer",
    "MatterGen",
    "CrystalLLM",
    "Con-CDVAE",
]


def reduced_formula(x):
    try:
        return Composition(str(x)).reduced_formula
    except Exception:
        return str(x).strip()


def norm_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def lattice_sanity_mask(df):
    return (
        df["a"].between(1.5, 40)
        & df["b"].between(1.5, 40)
        & df["c"].between(1.5, 40)
        & df["alpha"].between(30, 150)
        & df["beta"].between(30, 150)
        & df["gamma"].between(30, 150)
        & df[["a", "b", "c", "alpha", "beta", "gamma"]].notna().all(axis=1)
    )


def cell_vector(df):
    return df[["a", "b", "c", "alpha", "beta", "gamma"]].astype(float).values


def normalized_cell_distance(row, ref):
    length_terms = [
        abs(row["a"] - ref["a"]) / ref["a"],
        abs(row["b"] - ref["b"]) / ref["b"],
        abs(row["c"] - ref["c"]) / ref["c"],
    ]
    angle_terms = [
        abs(row["alpha"] - ref["alpha"]) / 180.0,
        abs(row["beta"] - ref["beta"]) / 180.0,
        abs(row["gamma"] - ref["gamma"]) / 180.0,
    ]
    return float(np.mean(length_terms + angle_terms))


def is_strict_cell_match(row, ref):
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


def jsd_from_counts(p_counts, q_counts):
    keys = sorted(set(p_counts.index).union(set(q_counts.index)))

    p = np.array([p_counts.get(k, 0) for k in keys], dtype=float)
    q = np.array([q_counts.get(k, 0) for k in keys], dtype=float)

    if p.sum() == 0 or q.sum() == 0:
        return np.nan

    p = p / p.sum()
    q = q / q.sum()
    m = 0.5 * (p + q)

    def kl(a, b):
        mask = a > 0
        return np.sum(a[mask] * np.log2(a[mask] / b[mask]))

    return float(0.5 * kl(p, m) + 0.5 * kl(q, m))


def wasserstein_1d(x, y):
    x = np.asarray(pd.Series(x).dropna(), dtype=float)
    y = np.asarray(pd.Series(y).dropna(), dtype=float)

    if len(x) == 0 or len(y) == 0:
        return np.nan

    x = np.sort(x)
    y = np.sort(y)

    qs = np.linspace(0, 1, 1001)
    xq = np.quantile(x, qs)
    yq = np.quantile(y, qs)

    return float(np.mean(np.abs(xq - yq)))


def exact_duplicate_percent(df):
    tmp = df.copy()

    for c in ["a", "b", "c", "alpha", "beta", "gamma"]:
        tmp[c + "_round"] = tmp[c].round(3)

    key_cols = [
        "formula",
        "spacegroup",
        "a_round",
        "b_round",
        "c_round",
        "alpha_round",
        "beta_round",
        "gamma_round",
    ]

    dup_mask = tmp.duplicated(subset=key_cols, keep=False)
    return 100 * dup_mask.mean()


def near_duplicate_percent(df, threshold=0.15):
    """
    Counts rows that have at least one near duplicate within same formula + spacegroup.
    """
    if len(df) == 0:
        return np.nan

    near = np.zeros(len(df), dtype=bool)

    work = df.reset_index(drop=True)

    group_cols = ["formula"]
    if "spacegroup" in work.columns and work["spacegroup"].notna().any():
        group_cols = ["formula", "spacegroup"]

    for _, g in work.groupby(group_cols, dropna=False):
        if len(g) < 2:
            continue

        idxs = g.index.to_list()
        vals = g[["a", "b", "c", "alpha", "beta", "gamma"]].astype(float).values

        for i in range(len(vals)):
            if near[idxs[i]]:
                continue

            vi = vals[i]
            if np.any(~np.isfinite(vi)):
                continue

            for j in range(i + 1, len(vals)):
                vj = vals[j]
                if np.any(~np.isfinite(vj)):
                    continue

                d_lengths = np.abs(vi[:3] - vj[:3]) / np.maximum(vj[:3], 1e-9)
                d_angles = np.abs(vi[3:] - vj[3:]) / 180.0
                d = float(np.mean(np.concatenate([d_lengths, d_angles])))

                if d < threshold:
                    near[idxs[i]] = True
                    near[idxs[j]] = True

    return 100 * near.mean()


def build_mp_index(mp):
    index = {}

    for _, r in mp.iterrows():
        formula = r["formula"]
        sg = r["spacegroup"]

        index.setdefault((formula, sg), []).append(r)

    return index


def mp_match_metrics(df_model, mp, mp_index):
    formula_sg_hits = []
    strict_hits = []
    deltas = []

    for _, row in df_model.iterrows():
        formula = row["formula"]
        sg = row["spacegroup"]

        refs = mp_index.get((formula, sg), [])

        formula_sg_hits.append(bool(refs))

        if not refs:
            strict_hits.append(False)
            continue

        best_delta = None
        best_strict = False

        for ref in refs:
            if pd.isna(ref["a"]) or pd.isna(row["a"]):
                continue

            d = normalized_cell_distance(row, ref)
            strict = is_strict_cell_match(row, ref)

            if best_delta is None or d < best_delta:
                best_delta = d

            if strict:
                best_strict = True

        strict_hits.append(best_strict)

        if best_delta is not None:
            deltas.append(best_delta)

    return {
        "hit_formula_sg_pct": 100 * np.mean(formula_sg_hits) if formula_sg_hits else np.nan,
        "hit_strict_pct": 100 * np.mean(strict_hits) if strict_hits else np.nan,
        "delta_mean": float(np.mean(deltas)) if deltas else np.nan,
        "delta_std": float(np.std(deltas, ddof=1)) if len(deltas) > 1 else np.nan,
    }


def main():
    gen = pd.read_csv(GEN_CSV, low_memory=False)
    mp = pd.read_csv(MP_REF_CSV, low_memory=False)

    numeric_cols = ["spacegroup", "a", "b", "c", "alpha", "beta", "gamma"]
    gen = norm_numeric(gen, numeric_cols)
    mp = norm_numeric(mp, numeric_cols)

    gen["formula"] = gen["formula"].map(reduced_formula)
    mp["formula"] = mp["formula"].map(reduced_formula)

    gen["valid_parse"] = gen[["formula", "a", "b", "c", "alpha", "beta", "gamma"]].notna().all(axis=1)
    gen["lattice_sanity"] = lattice_sanity_mask(gen)

    mp_index = build_mp_index(mp)

    rows = []

    model_order = [m for m in MODEL_ORDER if m in set(gen["model"])]
    model_order += [m for m in sorted(gen["model"].dropna().unique()) if m not in model_order]

    for model in model_order:
        d = gen[gen["model"] == model].copy()
        n = len(d)

        if n == 0:
            continue

        valid_pct = 100 * d["valid_parse"].mean()
        lattice_sanity_pct = 100 * d["lattice_sanity"].mean()

        exact_dup_pct = exact_duplicate_percent(d)
        near_dup_pct = near_duplicate_percent(d, threshold=0.15)

        unique_formulas_pct = 100 * d["formula"].nunique(dropna=True) / n
        unique_element_sets_pct = 100 * d["element_set"].nunique(dropna=True) / n

        mp_metrics = mp_match_metrics(d, mp, mp_index)

        mp_subset = mp[mp["formula"].isin(d["formula"].dropna().unique())].copy()

        jsd_sg = jsd_from_counts(
            d["spacegroup"].dropna().astype(int).value_counts(),
            mp_subset["spacegroup"].dropna().astype(int).value_counts(),
        )

        row = {
            "Model": model,
            "N": n,
            "Valid %": valid_pct,
            "Lattice sanity %": lattice_sanity_pct,
            "Exact dup %": exact_dup_pct,
            "Near dup %": near_dup_pct,
            "Unique formulas %": unique_formulas_pct,
            "Unique element sets %": unique_element_sets_pct,
            "Hit in MP strict %": mp_metrics["hit_strict_pct"],
            "Hit in MP formula+SG %": mp_metrics["hit_formula_sg_pct"],
            "δ_cell vs MP (mean)": mp_metrics["delta_mean"],
            "δ_cell vs MP (std)": mp_metrics["delta_std"],
            "JSD(SG) vs MP": jsd_sg,
            "W1(a) vs MP": wasserstein_1d(d["a"], mp_subset["a"]),
            "W1(b) vs MP": wasserstein_1d(d["b"], mp_subset["b"]),
            "W1(c) vs MP": wasserstein_1d(d["c"], mp_subset["c"]),
            "W1(alpha) vs MP": wasserstein_1d(d["alpha"], mp_subset["alpha"]),
            "W1(beta) vs MP": wasserstein_1d(d["beta"], mp_subset["beta"]),
            "W1(gamma) vs MP": wasserstein_1d(d["gamma"], mp_subset["gamma"]),
        }

        rows.append(row)

    out = pd.DataFrame(rows)

    percent_cols = [
        "Valid %",
        "Lattice sanity %",
        "Exact dup %",
        "Near dup %",
        "Unique formulas %",
        "Unique element sets %",
        "Hit in MP strict %",
        "Hit in MP formula+SG %",
    ]

    for c in percent_cols:
        out[c] = out[c].round(2)

    metric_cols = [
        "δ_cell vs MP (mean)",
        "δ_cell vs MP (std)",
        "JSD(SG) vs MP",
        "W1(a) vs MP",
        "W1(b) vs MP",
        "W1(c) vs MP",
        "W1(alpha) vs MP",
        "W1(beta) vs MP",
        "W1(gamma) vs MP",
    ]

    for c in metric_cols:
        out[c] = out[c].round(5)

    out.to_csv(OUT_CSV, index=False)

    print("Saved:")
    print(OUT_CSV)
    print()
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()