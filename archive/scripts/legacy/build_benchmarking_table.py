from pathlib import Path
import argparse
import math
import re
from collections import Counter

import numpy as np
import pandas as pd


ROOT = Path("/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench")

DEFAULT_INPUT = ROOT / "tables" / "master_structures.downsampled.with_status.classes.clean.csv"
DEFAULT_OUT = ROOT / "tables" / "table_benchmarking_baseline.csv"


MODEL_LABELS = {
    "cdvae": "Con-CDVAE",
    "concdvae": "Con-CDVAE",
    "con-cdvae": "Con-CDVAE",

    "mg": "MatterGen",
    "mattergen": "MatterGen",

    "cf": "CrystalFormer",
    "crystalformer": "CrystalFormer",

    "cllm": "CrystalLLM",
    "crystalllm": "CrystalLLM",
    "crystallm": "CrystalLLM",
}

MODEL_ORDER = [
    "CrystalFormer",
    "MatterGen",
    "CrystalLLM",
    "Con-CDVAE",
]


def norm_model(x):
    x = str(x).strip().lower().replace("_", "").replace("-", "")
    return MODEL_LABELS.get(x, str(x).strip())


def find_col(df, candidates, required=False):
    for c in candidates:
        if c in df.columns:
            return c
    if required:
        raise ValueError(f"None of these columns found: {candidates}")
    return None


def to_numeric_series(df, candidates):
    c = find_col(df, candidates)
    if c is None:
        return pd.Series([np.nan] * len(df), index=df.index)
    return pd.to_numeric(df[c], errors="coerce")


def norm_formula(x):
    if pd.isna(x):
        return ""
    x = str(x).strip()
    x = x.replace(" ", "")
    return x


def element_set_from_formula(formula):
    formula = norm_formula(formula)
    if not formula:
        return ""

    # Extract element symbols from formula strings like Na6Yb(FeSn2)3.
    elems = re.findall(r"[A-Z][a-z]?", formula)
    if not elems:
        return ""

    return "-".join(sorted(set(elems)))


def lattice_sanity_mask(df):
    a = to_numeric_series(df, ["a", "lattice_a", "cell_a"])
    b = to_numeric_series(df, ["b", "lattice_b", "cell_b"])
    c = to_numeric_series(df, ["c", "lattice_c", "cell_c"])

    alpha = to_numeric_series(df, ["alpha", "lattice_alpha", "cell_alpha"])
    beta = to_numeric_series(df, ["beta", "lattice_beta", "cell_beta"])
    gamma = to_numeric_series(df, ["gamma", "lattice_gamma", "cell_gamma"])

    volume = to_numeric_series(df, ["volume", "cell_volume", "lattice_volume"])

    length_ok = (
        a.between(1.5, 40)
        & b.between(1.5, 40)
        & c.between(1.5, 40)
    )

    angle_ok = (
        alpha.between(30, 150)
        & beta.between(30, 150)
        & gamma.between(30, 150)
    )

    if volume.notna().any():
        volume_ok = volume > 0
    else:
        volume_ok = pd.Series([True] * len(df), index=df.index)

    return length_ok & angle_ok & volume_ok


def get_spacegroup_series(df):
    c = find_col(df, [
        "spacegroup",
        "spacegroup_number",
        "sg",
        "sg_number",
        "space_group",
        "space_group_number",
    ])
    if c is None:
        return pd.Series([np.nan] * len(df), index=df.index)

    return pd.to_numeric(df[c], errors="coerce")


def cell_columns(df):
    return {
        "a": to_numeric_series(df, ["a", "lattice_a", "cell_a"]),
        "b": to_numeric_series(df, ["b", "lattice_b", "cell_b"]),
        "c": to_numeric_series(df, ["c", "lattice_c", "cell_c"]),
        "alpha": to_numeric_series(df, ["alpha", "lattice_alpha", "cell_alpha"]),
        "beta": to_numeric_series(df, ["beta", "lattice_beta", "cell_beta"]),
        "gamma": to_numeric_series(df, ["gamma", "lattice_gamma", "cell_gamma"]),
    }


def exact_duplicate_percent(df, formula_col):
    formula = df[formula_col].map(norm_formula)

    sg = get_spacegroup_series(df)

    cells = cell_columns(df)
    a = cells["a"].round(3)
    b = cells["b"].round(3)
    c = cells["c"].round(3)
    alpha = cells["alpha"].round(2)
    beta = cells["beta"].round(2)
    gamma = cells["gamma"].round(2)

    key = (
        formula.astype(str)
        + "|sg=" + sg.fillna(-1).astype(int).astype(str)
        + "|a=" + a.astype(str)
        + "|b=" + b.astype(str)
        + "|c=" + c.astype(str)
        + "|al=" + alpha.astype(str)
        + "|be=" + beta.astype(str)
        + "|ga=" + gamma.astype(str)
    )

    dup_mask = key.duplicated(keep=False)
    return 100 * dup_mask.mean()


def normalized_cell_distance(df):
    cells = cell_columns(df)

    arr = np.column_stack([
        cells["a"].to_numpy(dtype=float),
        cells["b"].to_numpy(dtype=float),
        cells["c"].to_numpy(dtype=float),
        cells["alpha"].to_numpy(dtype=float) / 90.0,
        cells["beta"].to_numpy(dtype=float) / 90.0,
        cells["gamma"].to_numpy(dtype=float) / 90.0,
    ])

    # Normalize lengths by median per model to avoid scale domination.
    for j in [0, 1, 2]:
        med = np.nanmedian(arr[:, j])
        if not np.isfinite(med) or med == 0:
            med = 1.0
        arr[:, j] = arr[:, j] / med

    return arr


def near_duplicate_percent(df, threshold=0.15):
    """
    Approximate near-duplicate percentage.
    We compare structures only within the same formula.
    A row is near-duplicate if it has another row with reduced-cell distance < threshold.
    """
    if len(df) <= 1:
        return 0.0

    formula_col = find_col(df, ["formula_reduced", "formula", "pretty_formula"], required=True)
    formulas = df[formula_col].map(norm_formula).to_numpy()
    arr = normalized_cell_distance(df)

    near = np.zeros(len(df), dtype=bool)

    for formula in pd.unique(formulas):
        idx = np.where(formulas == formula)[0]
        if len(idx) <= 1:
            continue

        sub = arr[idx]
        valid = np.all(np.isfinite(sub), axis=1)
        idx_valid = idx[valid]
        sub = sub[valid]

        if len(sub) <= 1:
            continue

        # O(n^2) inside each formula group; okay for moderate groups.
        for i in range(len(sub)):
            if near[idx_valid[i]]:
                continue
            d = np.sqrt(np.sum((sub[i + 1:] - sub[i]) ** 2, axis=1))
            if np.any(d < threshold):
                near[idx_valid[i]] = True
                near[idx_valid[i + 1:][d < threshold]] = True

    return 100 * near.mean()


def jsd_discrete(p_counts, q_counts):
    keys = sorted(set(p_counts) | set(q_counts))
    if not keys:
        return np.nan

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

    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def wasserstein_1_1d(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    x = x[np.isfinite(x)]
    y = y[np.isfinite(y)]

    if len(x) == 0 or len(y) == 0:
        return np.nan

    x = np.sort(x)
    y = np.sort(y)

    # Quantile approximation, enough for summary benchmarking.
    n = max(len(x), len(y), 200)
    qs = np.linspace(0, 1, n)
    xq = np.quantile(x, qs)
    yq = np.quantile(y, qs)

    return float(np.mean(np.abs(xq - yq)))


def prepare_reference(ref_path):
    if ref_path is None:
        return None

    ref = pd.read_csv(ref_path, low_memory=False)

    formula_col = find_col(ref, ["formula", "formula_reduced", "pretty_formula", "formula_pretty"], required=True)
    ref["formula_norm"] = ref[formula_col].map(norm_formula)

    sg_col = find_col(ref, [
        "spacegroup",
        "spacegroup_number",
        "sg",
        "sg_number",
        "space_group_number",
    ])

    if sg_col is not None:
        ref["sg_norm"] = pd.to_numeric(ref[sg_col], errors="coerce")
    else:
        ref["sg_norm"] = np.nan

    for c in ["a", "b", "c", "alpha", "beta", "gamma"]:
        alt = find_col(ref, [c, f"lattice_{c}", f"cell_{c}"])
        if alt is not None:
            ref[c] = pd.to_numeric(ref[alt], errors="coerce")
        else:
            ref[c] = np.nan

    ref = ref.dropna(subset=["formula_norm"])
    return ref


def cell_delta_to_reference(gen_row, ref_sub):
    """
    Return minimum normalized cell deviation to matching reference rows.
    Lengths: relative error.
    Angles: absolute error / 90.
    """
    if ref_sub is None or ref_sub.empty:
        return np.nan

    vals = {}
    for c in ["a", "b", "c", "alpha", "beta", "gamma"]:
        vals[c] = pd.to_numeric(pd.Series([gen_row.get(c, np.nan)]), errors="coerce").iloc[0]

    if any(not np.isfinite(vals[c]) for c in vals):
        return np.nan

    best = np.nan

    for _, r in ref_sub.iterrows():
        try:
            da = abs(vals["a"] - r["a"]) / max(abs(r["a"]), 1e-9)
            db = abs(vals["b"] - r["b"]) / max(abs(r["b"]), 1e-9)
            dc = abs(vals["c"] - r["c"]) / max(abs(r["c"]), 1e-9)
            dalpha = abs(vals["alpha"] - r["alpha"]) / 90.0
            dbeta = abs(vals["beta"] - r["beta"]) / 90.0
            dgamma = abs(vals["gamma"] - r["gamma"]) / 90.0

            d = np.mean([da, db, dc, dalpha, dbeta, dgamma])
        except Exception:
            continue

        if np.isfinite(d) and (not np.isfinite(best) or d < best):
            best = d

    return best


def mp_metrics_for_model(sub, ref):
    if ref is None or ref.empty:
        return {
            "Hit in MP strict %": np.nan,
            "Hit in MP formula+SG %": np.nan,
            "δ_cell vs MP (mean)": np.nan,
            "δ_cell vs MP (std)": np.nan,
            "JSD(SG) vs MP": np.nan,
            "W₁(a) vs MP": np.nan,
            "W₁(b) vs MP": np.nan,
            "W₁(c) vs MP": np.nan,
            "W₁(α) vs MP": np.nan,
            "W₁(β) vs MP": np.nan,
            "W₁(γ) vs MP": np.nan,
        }

    formula_col = find_col(sub, ["formula_reduced", "formula", "pretty_formula"], required=True)

    work = sub.copy()
    work["formula_norm"] = work[formula_col].map(norm_formula)
    work["sg_norm"] = get_spacegroup_series(work)

    cells = cell_columns(work)
    for c in ["a", "b", "c", "alpha", "beta", "gamma"]:
        work[c] = cells[c]

    ref_pairs = set(
        zip(
            ref["formula_norm"].astype(str),
            ref["sg_norm"].fillna(-999).astype(int),
        )
    )

    formula_sg_hit = []
    strict_hit = []
    deltas = []

    ref_group_formula = dict(tuple(ref.groupby("formula_norm")))
    ref_group_formula_sg = dict(tuple(ref.groupby(["formula_norm", "sg_norm"])))

    for _, row in work.iterrows():
        formula = row["formula_norm"]
        sg = row["sg_norm"]

        if not formula or pd.isna(sg):
            formula_sg_hit.append(False)
            strict_hit.append(False)
            deltas.append(np.nan)
            continue

        pair = (formula, int(sg))
        has_formula_sg = pair in ref_pairs
        formula_sg_hit.append(has_formula_sg)

        ref_sub = ref_group_formula_sg.get((formula, sg))
        if ref_sub is None or ref_sub.empty:
            ref_sub = ref_group_formula.get(formula, pd.DataFrame())

        d = cell_delta_to_reference(row, ref_sub)
        deltas.append(d)

        # Strict: same formula + SG and cell close enough.
        # lengths within roughly 5%, angles within roughly 2 degrees.
        is_strict = False
        if has_formula_sg:
            ref_same = ref_group_formula_sg.get((formula, sg), pd.DataFrame())
            for _, r in ref_same.iterrows():
                try:
                    length_ok = (
                        abs(row["a"] - r["a"]) / max(abs(r["a"]), 1e-9) <= 0.05
                        and abs(row["b"] - r["b"]) / max(abs(r["b"]), 1e-9) <= 0.05
                        and abs(row["c"] - r["c"]) / max(abs(r["c"]), 1e-9) <= 0.05
                    )
                    angle_ok = (
                        abs(row["alpha"] - r["alpha"]) <= 2
                        and abs(row["beta"] - r["beta"]) <= 2
                        and abs(row["gamma"] - r["gamma"]) <= 2
                    )
                    if length_ok and angle_ok:
                        is_strict = True
                        break
                except Exception:
                    pass

        strict_hit.append(is_strict)

    gen_sg_counts = Counter(work["sg_norm"].dropna().astype(int).tolist())
    ref_sg_counts = Counter(ref["sg_norm"].dropna().astype(int).tolist())

    metrics = {
        "Hit in MP strict %": 100 * np.mean(strict_hit) if len(strict_hit) else np.nan,
        "Hit in MP formula+SG %": 100 * np.mean(formula_sg_hit) if len(formula_sg_hit) else np.nan,
        "δ_cell vs MP (mean)": float(np.nanmean(deltas)) if np.isfinite(deltas).any() else np.nan,
        "δ_cell vs MP (std)": float(np.nanstd(deltas)) if np.isfinite(deltas).any() else np.nan,
        "JSD(SG) vs MP": jsd_discrete(gen_sg_counts, ref_sg_counts),
    }

    for gen_col, label in [
        ("a", "W₁(a) vs MP"),
        ("b", "W₁(b) vs MP"),
        ("c", "W₁(c) vs MP"),
        ("alpha", "W₁(α) vs MP"),
        ("beta", "W₁(β) vs MP"),
        ("gamma", "W₁(γ) vs MP"),
    ]:
        metrics[label] = wasserstein_1_1d(work[gen_col], ref[gen_col])

    return metrics


def model_summary(sub, ref=None):
    formula_col = find_col(sub, ["formula_reduced", "formula", "pretty_formula"], required=True)

    n = len(sub)

    if "status" in sub.columns:
        valid_pct = 100 * (sub["status"].astype(str).str.strip() == "validated").mean()
    else:
        valid_pct = 100.0

    sane_pct = 100 * lattice_sanity_mask(sub).mean()

    formulas = sub[formula_col].map(norm_formula)
    element_sets = formulas.map(element_set_from_formula)

    exact_dup = exact_duplicate_percent(sub, formula_col)
    near_dup = near_duplicate_percent(sub, threshold=0.15)

    unique_formulas_pct = 100 * formulas.nunique(dropna=True) / n if n else np.nan
    unique_element_sets_pct = 100 * element_sets.nunique(dropna=True) / n if n else np.nan

    row = {
        "Model": sub["Model"].iloc[0],
        "N": n,
        "Valid %": valid_pct,
        "Lattice sanity %": sane_pct,
        "Exact dup %": exact_dup,
        "Near dup %": near_dup,
        "Unique formulas %": unique_formulas_pct,
        "Unique element sets %": unique_element_sets_pct,
    }

    row.update(mp_metrics_for_model(sub, ref))

    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(DEFAULT_INPUT))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--ref", default=None, help="Optional MP/COD reference CSV with formula, spacegroup, a,b,c,alpha,beta,gamma")
    args = ap.parse_args()

    inp = Path(args.input)
    out = Path(args.out)

    df = pd.read_csv(inp, low_memory=False)

    model_col = find_col(df, ["model_short", "model_name", "model"], required=True)
    formula_col = find_col(df, ["formula_reduced", "formula", "pretty_formula"], required=True)

    df["Model"] = df[model_col].map(norm_model)
    df[formula_col] = df[formula_col].map(norm_formula)

    # Remove empty formula rows.
    df = df[df[formula_col].astype(str).str.len() > 0].copy()

    ref = prepare_reference(args.ref) if args.ref else None

    rows = []
    for model, sub in df.groupby("Model", sort=False):
        rows.append(model_summary(sub, ref=ref))

    result = pd.DataFrame(rows)

    result["Model"] = pd.Categorical(result["Model"], categories=MODEL_ORDER, ordered=True)
    result = result.sort_values("Model")
    result["Model"] = result["Model"].astype(str)

    # Stable column order.
    columns = [
        "Model",
        "N",
        "Valid %",
        "Lattice sanity %",
        "Exact dup %",
        "Near dup %",
        "Unique formulas %",
        "Unique element sets %",
        "Hit in MP strict %",
        "Hit in MP formula+SG %",
        "δ_cell vs MP (mean)",
        "δ_cell vs MP (std)",
        "JSD(SG) vs MP",
        "W₁(a) vs MP",
        "W₁(b) vs MP",
        "W₁(c) vs MP",
        "W₁(α) vs MP",
        "W₁(β) vs MP",
        "W₁(γ) vs MP",
    ]

    for c in columns:
        if c not in result.columns:
            result[c] = np.nan

    result = result[columns]

    out.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out, index=False)

    print("Saved:")
    print(out)
    print()
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()