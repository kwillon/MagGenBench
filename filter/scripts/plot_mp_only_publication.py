#!/usr/bin/env python3
"""Render MP-only CIF magnetic-reference benchmark and DFT validation figures.

A: enrichment with reduced-formula cluster bootstrap 95% CI
B: contrast 5-95%, IQR, and median
C: nearest MP magnetic branch composition (AFM, FM, FiM)
D: DFT magnetic confirmation conditional on MP-only contrast > 0;
   rendered directly from joined MP-only DFT CSV with Wilson 95% CIs.

Creates individual vector/PNG panels, the combined 2x2 figure, and a
supplementary panel comparing DFT magnetic fractions in MP-only
magnetic-like (contrast >0) and NM-like (contrast <=0) groups.
No old DFT image or old reference scores are used. The underlying historical
DFT cohort was selected using the previous model: not an unbiased test set.

Run from project root:
    python3 filter/scripts/plot_mp_only_publication.py

Inputs by default:
    results/mp_only/generator_summary.csv
    results/mp_only/generator_scores.csv
    results/mp_only/dft_validation/dft_joined_mp_only.csv
    results/mp_only/dft_validation/dft_validation_audit.json

Refuses a smoke/sample cohort (<500 CIFs per generator) unless --allow-small.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CONTRAST = "magnetic_reference_vs_NM_contrast"
BRANCHES = ("AFM", "FM", "FiM")

# Palettes follow the original article's figures.py.
GENERATOR_COLORS = {
    "mattergen_base": "#9DAA90",
    "mattergen_finetuned": "#4F6B46",
    "concdvae_base": "#E1B15A",
    "concdvae_finetuned": "#C05C17",
    "crysjepa_base": "#8CA5AE",
    "crysjepa_refined": "#344E68",
    "crystalformer": "#DD8B63",
    "crystalformer_finetuned": "#AA5439",
    "crystalllm": "#B84D45",
    "crystalllm_finetuned": "#792C47",
}
REFERENCE_COLORS = {"AFM": "#D6A64F", "FM": "#5F7F57", "FiM": "#A65A73"}
ORDER = list(GENERATOR_COLORS)
LABELS = {
    "mattergen_base": "MatterGen base", "mattergen_finetuned": "MatterGen tuned",
    "concdvae_base": "ConcDVAE base", "concdvae_finetuned": "ConcDVAE tuned",
    "crysjepa_base": "CrysJEPA base", "crysjepa_refined": "CrysJEPA refined",
    "crystalformer": "CrystalFormer base", "crystalformer_finetuned": "CrystalFormer tuned",
    "crystalllm": "CrystALLM base", "crystalllm_finetuned": "CrystALLM tuned",
}


def style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 8.8,
        "axes.labelsize": 8.8,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7.3,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "axes.facecolor": "white",
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def read_data(summary_path: Path, scores_path: Path, allow_small: bool):
    for path in (summary_path, scores_path):
        if not path.is_file():
            raise FileNotFoundError(f"Input not found: {path}\nUse the FULL results/mp_only/ directory.")

    summary = pd.read_csv(summary_path)
    required = {"dataset", "n_input", "n_scored", "fraction_magnetic_like", "median_contrast", "magnetic_like"}
    missing = required - set(summary.columns)
    if missing:
        raise ValueError(f"Summary missing columns: {sorted(missing)}")
    summary["dataset"] = summary["dataset"].astype(str).str.lower().str.strip()
    if summary["dataset"].duplicated().any():
        raise ValueError("Duplicate generators in summary")
    unknown = sorted(set(summary["dataset"]) - set(ORDER))
    if unknown:
        raise ValueError(f"Unexpected generator names in summary: {unknown}")
    included = [d for d in ORDER if d in set(summary["dataset"])]
    summary = summary.set_index("dataset").loc[included].reset_index()

    if not allow_small and (summary["n_input"] < 500).any():
        small = summary.loc[summary["n_input"] < 500, ["dataset", "n_input"]]
        raise ValueError(
            "Refusing small/smoke dataset. Use results/mp_only/, not mp_only_smoke.\n"
            + small.to_string(index=False)
            + "\nFor deliberate small tests, pass --allow-small."
        )

    scores = pd.read_csv(scores_path, low_memory=False)
    expected = {"dataset", CONTRAST, "nearest_magnetic_reference_branch"}
    missing = expected - set(scores.columns)
    if missing:
        raise ValueError(f"Scores missing columns: {sorted(missing)}")
    scores["dataset"] = scores["dataset"].astype(str).str.lower().str.strip()
    if "score_status" in scores:
        scores = scores.loc[scores["score_status"].astype(str).eq("ok")].copy()
    scores[CONTRAST] = pd.to_numeric(scores[CONTRAST], errors="coerce")
    scores = scores.loc[np.isfinite(scores[CONTRAST])].copy()
    scores["nearest_magnetic_reference_branch"] = (
        scores["nearest_magnetic_reference_branch"].astype(str).str.strip()
        .replace({"FIM": "FiM", "fim": "FiM"})
    )
    bad_branches = sorted(set(scores["nearest_magnetic_reference_branch"]) - set(BRANCHES))
    if bad_branches:
        raise ValueError(f"Expected MP-only branches {BRANCHES}; found {bad_branches}")

    # Fail rather than silently drawing mixed/smoke results.
    for row in summary.itertuples(index=False):
        subset = scores[scores["dataset"].eq(row.dataset)]
        n, k = len(subset), int(subset[CONTRAST].gt(0).sum())
        if n != int(row.n_scored) or k != int(row.magnetic_like):
            raise ValueError(f"{row.dataset}: scores contain n={n}, magnetic={k}, "
                             f"but summary says n={row.n_scored}, magnetic={row.magnetic_like}")
        if not np.isclose(k/n, float(row.fraction_magnetic_like), atol=1e-12):
            raise ValueError(f"{row.dataset}: enrichment mismatch")
        if not np.isclose(subset[CONTRAST].median(), float(row.median_contrast), atol=1e-9):
            raise ValueError(f"{row.dataset}: contrast median mismatch")

    extra = set(scores["dataset"]) - set(included)
    if extra:
        raise ValueError(f"Scores contain generators missing from summary: {extra}")
    return summary, scores, included


def cluster_ci(g: pd.DataFrame, seed: int, replicates: int):
    if "formula_reduced" in g:
        formula = g["formula_reduced"].astype("string")
    else:
        formula = pd.Series(pd.NA, index=g.index, dtype="string")
    fallback = "__row_" + g.index.astype(str)
    formula = formula.where(formula.notna() & formula.str.strip().ne(""), fallback)
    tmp = pd.DataFrame({"formula": formula.to_numpy(), "positive": g[CONTRAST].gt(0).to_numpy()})
    clusters = tmp.groupby("formula", sort=False).agg(n=("positive", "size"), k=("positive", "sum"))
    n, k = clusters["n"].to_numpy(float), clusters["k"].to_numpy(float)
    if not len(n) or replicates < 1:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    values = np.empty(replicates)
    for start in range(0, replicates, 128):
        count = min(128, replicates-start)
        draws = rng.integers(0, len(n), size=(count, len(n)))
        values[start:start+count] = k[draws].sum(axis=1) / n[draws].sum(axis=1)
    return tuple(np.quantile(values, [0.025, 0.975]))


def statistics(summary, scores, order, replicates, seed):
    result = summary.set_index("dataset").loc[order].copy()
    for col in ["fmag_ci_low", "fmag_ci_high", "contrast_q05", "contrast_q25",
                "contrast_q50", "contrast_q75", "contrast_q95"]:
        result[col] = np.nan
    for branch in BRANCHES:
        result[f"branch_{branch}"] = np.nan

    for i, ds in enumerate(order):
        g = scores[scores["dataset"].eq(ds)]
        lo, hi = cluster_ci(g, seed+i, replicates)
        result.loc[ds, ["fmag_ci_low", "fmag_ci_high"]] = [lo, hi]
        contrast = g[CONTRAST]
        for col, val in zip(["contrast_q05", "contrast_q25", "contrast_q50", "contrast_q75", "contrast_q95"],
                            contrast.quantile([.05, .25, .5, .75, .95])):
            result.loc[ds, col] = val
        pos = g.loc[g[CONTRAST] > 0]
        if len(pos):
            counts = pos["nearest_magnetic_reference_branch"].value_counts(normalize=True)
            for br in BRANCHES:
                result.loc[ds, f"branch_{br}"] = float(counts.get(br, 0))
            if not np.isclose(sum(result.loc[ds, f"branch_{br}"] for br in BRANCHES), 1.0, atol=1e-9):
                raise ValueError(f"Branch fractions do not sum to 1 for {ds}")
    return result.reset_index()


def horizontal_axis(ax, order, y):
    ax.set_yticks(y, [LABELS[d] for d in order])
    ax.set_ylim(-.8, y[-1]+.8)
    ax.invert_yaxis()
    ax.tick_params(axis="y", length=0, pad=3)
    for i in range(2, len(order), 2):
        ax.axhline((y[i-1]+y[i])/2, linewidth=.6, color="#B8C0C4", alpha=.55)
    ax.xaxis.grid(True, color="#9099A1", alpha=.17, linewidth=.6)
    ax.set_axisbelow(True)


def positions(n):
    return np.array([i + .78*(i//2) for i in range(n)], float)


def panel_a(ax, stat, order):
    y = positions(len(order))
    v = stat["fraction_magnetic_like"].to_numpy(float)
    ax.barh(y, v, height=.68, color=[GENERATOR_COLORS[d] for d in order], edgecolor="none")
    lo = stat["fmag_ci_low"].to_numpy(float)
    hi = stat["fmag_ci_high"].to_numpy(float)
    ok = np.isfinite(lo) & np.isfinite(hi)
    if ok.any():
        ax.errorbar(v[ok], y[ok], xerr=np.vstack([np.maximum(0, v[ok]-lo[ok]), np.maximum(0, hi[ok]-v[ok])]),
                    fmt="none", ecolor="#333333", capsize=2.5, elinewidth=.9, zorder=4)
    ax.set_xlim(0, 1.025)
    ax.set_xticks(np.linspace(0, 1, 6))
    ax.set_xlabel("Fraction closer to magnetic than NM reference")
    horizontal_axis(ax, order, y)


def panel_b(ax, stat, order):
    y = positions(len(order))
    q05, q25, mid, q75, q95 = [stat[f"contrast_{q}"].to_numpy(float)
                                 for q in ("q05", "q25", "q50", "q75", "q95")]
    for j, ds in enumerate(order):
        col = GENERATOR_COLORS[ds]
        ax.plot([q05[j],q95[j]], [y[j], y[j]], color=col, linewidth=2.2, solid_capstyle="round")
        ax.plot([q25[j],q75[j]], [y[j], y[j]], color=col, linewidth=8.0, solid_capstyle="butt")
        ax.plot([mid[j],mid[j]], [y[j]-.22,y[j]+.22], color="#243039", linewidth=1.7)
        for val in [q05[j],q95[j]]:
            ax.plot([val,val], [y[j]-.10,y[j]+.10], color=col, linewidth=1.2)
    ax.axvline(0, color="#606060", linewidth=.9)
    lo, hi = float(np.min(q05)),float(np.max(q95))
    pad = .06 * max(hi-lo,1.)
    ax.set_xlim(lo-pad,hi+pad)
    ax.set_xlabel(r"Magnetic-reference contrast, $d_{NM}-d_{mag}$")
    horizontal_axis(ax, order, y)


def panel_c(ax, stat, order):
    x = np.arange(len(order))
    base = np.zeros(len(order))
    for br in BRANCHES:
        vals = stat[f"branch_{br}"].fillna(0).to_numpy(float)
        ax.bar(x, vals, bottom=base, width=.72, label=br, color=REFERENCE_COLORS[br], edgecolor="none")
        base += vals
    ax.set_ylim(0, 1)
    ax.set_xlim(-.55, len(order)-.45)
    ax.set_ylabel("Fraction among magnetic-like candidates")
    ax.set_xticks(x, [LABELS[d] for d in order], rotation=30, ha="right", rotation_mode="anchor")
    ax.tick_params(axis="x", labelsize=7.1, pad=3)
    ax.yaxis.grid(True, linewidth=.6, color="#9099A1", alpha=.16)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(.5,1.015),
              handlelength=1.1, handletextpad=.4, columnspacing=1.3, borderaxespad=.1)


# The DFT cohort was originally selected using an older reference model.
DFT_ORDER = ("mattergen_base", "concdvae_base", "crystalformer", "crystalllm")
DFT_COLORS = {ds: GENERATOR_COLORS[ds] for ds in DFT_ORDER}


def wilson_ci(k: int, n: int, z: float = 1.959963984540054):
    if n <= 0:
        return float("nan"), float("nan")
    p = k / n
    denominator = 1 + z*z/n
    center = (p + z*z/(2*n)) / denominator
    half = z * np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denominator
    return max(0.0, float(center-half)), min(1.0, float(center+half))


def load_dft(dft_path: Path, audit_path: Path, scores_path: Path,
             ignore_audit_source: bool = False):
    """Recompute all plotted DFT fractions from individually joined MP-only data."""
    if not dft_path.is_file():
        raise FileNotFoundError(
            f"No MP-only DFT join: {dft_path}\n"
            "First run recalculate_dft_mp_only.py on the MP-only scores."
        )
    if not audit_path.is_file():
        raise FileNotFoundError(f"Missing MP-only DFT provenance audit: {audit_path}")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("model_classes") != ["AFM", "FM", "FiM", "NM"]:
        raise ValueError("DFT audit is not for the four-branch MP-only model")
    if int(audit.get("unmatched_count", -1)) != 0:
        raise ValueError("DFT audit reports unmatched candidates; refusing publication figure")
    if int(audit.get("matched_count", -1)) != 324:
        raise ValueError("Expected 324 matched historical DFT candidates")
    if not ignore_audit_source:
        audited_scores = audit.get("source_scores")
        if not audited_scores or Path(audited_scores).expanduser().resolve() != scores_path.resolve():
            raise ValueError(
                "DFT audit source_scores differs from --scores. Recalculate DFT join "
                "on this scores file before making figures. For migrated paths use "
                "--ignore-audit-source only after verifying provenance.\n"
                f"  DFT audit: {audited_scores}\n  Figure scores: {scores_path}"
            )

    d = pd.read_csv(dft_path, low_memory=False)
    cols = {"dataset", "dft_is_magnetic", CONTRAST, "sha256"}
    missing = cols - set(d.columns)
    if missing:
        raise ValueError(f"DFT join missing columns: {sorted(missing)}")
    d["dataset"] = d["dataset"].astype(str).str.strip().str.lower()
    if len(d) != 324:
        raise ValueError(f"Expected 324 DFT records, found {len(d)}")
    if not set(d["dataset"]).issubset(DFT_ORDER):
        raise ValueError(f"Unexpected DFT datasets: {set(d['dataset'])-set(DFT_ORDER)}")
    if d.duplicated(["dataset", "sha256"]).any():
        raise ValueError("DFT join contains duplicate dataset/SHA256 candidates")
    d[CONTRAST] = pd.to_numeric(d[CONTRAST], errors="coerce")
    d["dft_is_magnetic"] = pd.to_numeric(d["dft_is_magnetic"], errors="coerce")
    if not np.isfinite(d[CONTRAST].to_numpy(dtype=float)).all():
        raise ValueError("Non-finite MP-only contrasts in joined DFT data")
    if not d["dft_is_magnetic"].isin([0, 1]).all():
        raise ValueError("Expected binary 0/1 DFT magnetic labels")
    if "MP_pipeline_class" in d:
        predicted = np.where(d[CONTRAST].gt(0), "Magnetic-like", "NM-like")
        if not np.array_equal(d["MP_pipeline_class"].astype(str).to_numpy(), predicted):
            raise ValueError("DFT join MP_pipeline_class disagrees with MP-only contrast")
    # Verify that joined DFT contrasts are precisely those of the CURRENT query
    # score table, not merely a file with a matching historical path.
    q = pd.read_csv(scores_path, low_memory=False)
    if not {"dataset", "structure_id", CONTRAST}.issubset(q.columns):
        raise ValueError("Current generator_scores.csv lacks dataset, structure_id, or contrast")
    q["dataset"] = q["dataset"].astype(str).str.strip().str.lower()
    q[CONTRAST] = pd.to_numeric(q[CONTRAST], errors="coerce")
    if "score_status" in q:
        q = q[q["score_status"].astype(str).eq("ok")].copy()

    # SHA hashes are more robust after the CIF reorganizer changed filenames.
    if "sha256" in q and q["sha256"].notna().all():
        q["sha256"] = q["sha256"].astype(str).str.strip().str.lower()
        key = ["dataset", "sha256"]
        d["sha256"] = d["sha256"].astype(str).str.strip().str.lower()
    elif "mp_structure_id" in d:
        q["structure_id"] = q["structure_id"].astype(str)
        d["structure_id"] = d["mp_structure_id"].astype(str)
        key = ["dataset", "structure_id"]
    else:
        raise ValueError("Cannot verify DFT join: scores lack SHA256 and DFT join lacks mp_structure_id")

    repeated = q[q.duplicated(key, keep=False)]
    if not repeated.empty:
        spread = repeated.groupby(key)[CONTRAST].agg(lambda x: x.max()-x.min())
        if (spread > 1e-9).any():
            raise ValueError("Duplicate CIF keys in scores have different magnetic contrasts")
        q = q.drop_duplicates(key, keep="first")
    check = d[key + [CONTRAST]].merge(
        q[key + [CONTRAST]], on=key, how="left", suffixes=("_joined", "_current"),
        validate="many_to_one", indicator=True,
    )
    if not check["_merge"].eq("both").all():
        raise ValueError("DFT join contains candidates absent from current generator scores")
    if not np.allclose(check[f"{CONTRAST}_joined"],
                       check[f"{CONTRAST}_current"], rtol=0, atol=1e-9):
        raise ValueError("DFT join contrasts differ from current generator scores; regenerate DFT join")

    d["mp_magnetic_like"] = d[CONTRAST].gt(0)
    by_generator = []
    for ds in DFT_ORDER:
        cohort = d[d["dataset"].eq(ds)]
        selected = cohort[cohort["mp_magnetic_like"]]
        n = len(selected)
        k = int(selected["dft_is_magnetic"].sum())
        lo, hi = wilson_ci(k, n)
        by_generator.append({
            "dataset": ds, "n_dft_total": len(cohort),
            "n_mp_magnetic_like": n, "n_dft_magnetic": k,
            "dft_confirmation_fraction": k/n if n else np.nan,
            "ci95_low": lo, "ci95_high": hi,
        })
    overall = []
    for flag, name in [(True, "Magnetic-like"), (False, "NM-like")]:
        cohort = d[d["mp_magnetic_like"].eq(flag)]
        n = len(cohort)
        k = int(cohort["dft_is_magnetic"].sum())
        lo, hi = wilson_ci(k, n)
        overall.append({
            "MP_pipeline_class": name, "n": n, "n_dft_magnetic": k,
            "fraction_dft_magnetic": k/n if n else np.nan,
            "ci95_low": lo, "ci95_high": hi,
        })
    by_generator = pd.DataFrame(by_generator)
    overall = pd.DataFrame(overall)
    return d, by_generator, overall, audit


def panel_d(ax, dft_generator: pd.DataFrame):
    """Publication-style DFT confirmation, built as vector artists, not a PNG."""
    d = dft_generator.set_index("dataset").loc[list(DFT_ORDER)]
    y = np.arange(len(d))
    values = d["dft_confirmation_fraction"].to_numpy(float)
    lo = d["ci95_low"].to_numpy(float)
    hi = d["ci95_high"].to_numpy(float)
    good = np.isfinite(values) & np.isfinite(lo) & np.isfinite(hi)
    colors = [DFT_COLORS[ds] for ds in DFT_ORDER]
    ax.barh(y[good], values[good], color=np.asarray(colors)[good],
            height=.68, edgecolor="none")
    if good.any():
        ax.errorbar(values[good], y[good],
                    xerr=np.vstack([np.maximum(0, values[good]-lo[good]),
                                    np.maximum(0, hi[good]-values[good])]),
                    fmt="none", ecolor="#333333", elinewidth=1.0,
                    capsize=2.4, zorder=4)
    ax.set_yticks(y, [LABELS[x] for x in DFT_ORDER])
    ax.invert_yaxis()
    ax.tick_params(axis="y", length=0, pad=3)
    ax.set_xlim(0, 1.025)
    ax.set_xticks(np.linspace(0, 1, 6))
    ax.set_xlabel("Fraction confirmed magnetic by DFT")
    ax.xaxis.grid(True, color="#9099A1", alpha=.17, linewidth=.6)
    ax.set_axisbelow(True)


def supplementary_dft(ax, dft_overall: pd.DataFrame):
    d = dft_overall.set_index("MP_pipeline_class").loc[["Magnetic-like", "NM-like"]]
    y = np.arange(2)
    values = d["fraction_dft_magnetic"].to_numpy(float)
    lo = d["ci95_low"].to_numpy(float)
    hi = d["ci95_high"].to_numpy(float)
    colors = ["#5F7F57", "#C7CDD3"]
    ax.barh(y, values, color=colors, height=.60, edgecolor="none")
    ax.errorbar(values, y, xerr=np.vstack([values-lo, hi-values]),
                fmt="none", ecolor="#333333", elinewidth=1.0,
                capsize=3.0, zorder=4)
    labels = [f"MP-only {name}  (n={int(d.loc[name, 'n'])})"
              for name in ("Magnetic-like", "NM-like")]
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.tick_params(axis="y", length=0, pad=4)
    ax.set_xlim(0, 1.025)
    ax.set_xticks(np.linspace(0, 1, 6))
    ax.set_xlabel("Fraction magnetic in DFT")
    ax.xaxis.grid(True, color="#9099A1", alpha=.17, linewidth=.6)
    ax.set_axisbelow(True)


def add_letter(ax, s):
    ax.text(-.067, 1.045, s, transform=ax.transAxes,
            fontsize=15, fontweight="bold", ha="left", va="bottom", clip_on=False)


def save(fig, path: Path, dpi: int):
    fig.savefig(path.with_suffix(".png"), dpi=dpi, bbox_inches="tight", pad_inches=.13)
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight", pad_inches=.13)
    plt.close(fig)


def separate_figures(stat, order, dft_generator, output_dir, dpi):
    jobs = [
        ("panel_A_enrichment", panel_a, (8.3, 5.6)),
        ("panel_B_contrast_distribution", panel_b, (8.3, 5.6)),
        ("panel_C_branch_composition", panel_c, (8.3, 5.6)),
    ]
    for name, drawer, size in jobs:
        fig, ax = plt.subplots(figsize=size)
        if name == "panel_C_branch_composition":
            fig.subplots_adjust(left=.12, right=.98, top=.90, bottom=.255)
        else:
            fig.subplots_adjust(left=.25, right=.97, top=.96, bottom=.12)
        drawer(ax, stat, order)
        save(fig, output_dir / name, dpi)
    fig, ax = plt.subplots(figsize=(8.3, 5.6))
    fig.subplots_adjust(left=.25, right=.97, top=.96, bottom=.12)
    panel_d(ax, dft_generator)
    save(fig, output_dir / "panel_D_dft_confirmation", dpi)


def combined_figure(stat, order, dft_generator, output_dir, dpi):
    fig = plt.figure(figsize=(17, 12))
    gs = fig.add_gridspec(2, 2, left=.115, right=.985, bottom=.13, top=.96,
                          wspace=.32, hspace=.43, height_ratios=(1, 1.0))
    axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]
    panel_a(axes[0], stat, order)
    panel_b(axes[1], stat, order)
    panel_c(axes[2], stat, order)
    panel_d(axes[3], dft_generator)
    for letter, ax in zip("ABCD", axes):
        add_letter(ax, letter)
    save(fig, output_dir / "Figure_MP_only_generator_benchmark", dpi)


def publication_preview(stat, order, dft_generator, family_colors, adapted_hatch="///"):
    """Presentation only: draw already frozen statistics without recomputing them.

    Kept separate from the historical renderer so its exports remain available.
    The caller supplies the manuscript palette and handles preview-only export.
    """
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch, Rectangle

    names = {"mattergen": "MatterGen", "concdvae": "Con-CDVAE",
             "crysjepa": "Crys-JEPA", "crystalformer": "CrystalFormer",
             "crystalllm": "CrystaLLM"}

    def adapted(ds):
        return ds.endswith(("_finetuned", "_refined"))

    def color(ds):
        return family_colors[names[ds.split("_")[0]]]

    def label(ds):
        variant = "Refined" if ds.endswith("_refined") else "FT" if adapted(ds) else "Base"
        return names[ds.split("_")[0]] + "  " + variant

    plt.rcParams.update({"font.size": 12, "axes.labelsize": 12,
                         "xtick.labelsize": 11, "ytick.labelsize": 11,
                         "legend.fontsize": 10.5, "hatch.linewidth": .65})
    fig, axes = plt.subplots(2, 2, figsize=(18, 10.5))
    fig.subplots_adjust(left=.132, right=.985, bottom=.085, top=.86,
                        wspace=.36, hspace=.39)
    a, b, c, d = axes.flat
    data = stat.set_index("dataset").loc[order]
    y = np.arange(len(order))

    def row_axis(ax):
        ax.set_yticks(y, [label(ds) for ds in order])
        ax.set_ylim(len(order)-.4, -.6)
        ax.tick_params(axis="y", length=0, pad=6)
        for j in range(2, len(order), 2):
            ax.axhline(j-.5, color="#D7DCDF", linewidth=.6, zorder=0)
        ax.xaxis.grid(True, color="#D7DCDF", linewidth=.6, alpha=.65)
        ax.set_axisbelow(True)

    def fraction_axis(ax):
        ax.set_xlim(0, 1.025)
        ax.set_xticks(np.linspace(0, 1, 6))

    def ci(ax, values, lo, hi, positions):
        ax.errorbar(values, positions, xerr=np.vstack([values-lo, hi-values]),
                    fmt="none", ecolor="#25313C", capsize=3,
                    elinewidth=1.1, zorder=5)

    for j, ds in enumerate(order):
        a.barh(j, data.loc[ds, "fraction_magnetic_like"], height=.7,
               color=color(ds), edgecolor="#263746", linewidth=.45,
               hatch=adapted_hatch if adapted(ds) else None)
    ci(a, data.fraction_magnetic_like.to_numpy(), data.fmag_ci_low.to_numpy(),
       data.fmag_ci_high.to_numpy(), y)
    row_axis(a)
    fraction_axis(a)
    a.set_xlabel("Fraction closer to magnetic than NM reference")
    a.set_title("A  Magnetic-like candidates (95% CI)", loc="left", fontsize=13, weight="bold", pad=14)

    for j, ds in enumerate(order):
        row = data.loc[ds]
        col = color(ds)
        b.plot([row.contrast_q05, row.contrast_q95], [j, j], color=col,
               linewidth=1.8, linestyle="--" if adapted(ds) else "-", zorder=2)
        b.vlines([row.contrast_q05, row.contrast_q95], j-.12, j+.12, color=col, linewidth=1.3)
        b.add_patch(Rectangle((row.contrast_q25, j-.25), row.contrast_q75-row.contrast_q25,
                             .5, facecolor=col, edgecolor="#263746", linewidth=.5,
                             hatch=adapted_hatch if adapted(ds) else None, zorder=3))
        b.plot(row.contrast_q50, j, marker="D" if adapted(ds) else "o",
               markersize=5.3, color="#1F2D38", markerfacecolor="white", zorder=5)
    row_axis(b)
    b.axvline(0, color="#646D75", linewidth=.9, zorder=1)
    span = max(data.contrast_q95.max()-data.contrast_q05.min(), 1)
    b.set_xlim(data.contrast_q05.min()-.04*span, data.contrast_q95.max()+.04*span)
    b.set_xlabel(r"Magnetic-reference contrast, $d_{NM}-d_{mag}$")
    b.set_title("B  Contrast: 5-95%, IQR and median", loc="left", fontsize=13, weight="bold", pad=14)

    left = np.zeros(len(order))
    for branch in BRANCHES:
        values = data[f"branch_{branch}"].to_numpy(float)
        for j, ds in enumerate(order):
            c.barh(j, values[j], left=left[j], height=.7, color=REFERENCE_COLORS[branch],
                   edgecolor="#263746", linewidth=.35,
                   hatch=adapted_hatch if adapted(ds) else None)
        left += values
    row_axis(c)
    fraction_axis(c)
    c.set_xlabel("Fraction among magnetic-like candidates")
    c.set_title("C  Magnetic class", loc="left", fontsize=13, weight="bold", pad=14)
    c.legend(handles=[Patch(facecolor=REFERENCE_COLORS[br], label=br) for br in BRANCHES],
             ncol=3, frameon=False, loc="lower right", bbox_to_anchor=(1, 1.025),
             borderaxespad=0, columnspacing=1.1, handlelength=1.1)

    dft = dft_generator.set_index("dataset").loc[list(DFT_ORDER)]
    yd = np.arange(len(dft))
    d.barh(yd, dft.dft_confirmation_fraction, height=.58,
           color=[color(ds) for ds in DFT_ORDER], edgecolor="#263746", linewidth=.45)
    ci(d, dft.dft_confirmation_fraction.to_numpy(), dft.ci95_low.to_numpy(),
       dft.ci95_high.to_numpy(), yd)
    d.set_yticks(yd, [label(ds) + f"  (n={int(dft.loc[ds, 'n_mp_magnetic_like'])})" for ds in DFT_ORDER])
    d.set_ylim(3.65, -.65)
    d.tick_params(axis="y", length=0, pad=6)
    d.xaxis.grid(True, color="#D7DCDF", linewidth=.6, alpha=.65)
    d.set_axisbelow(True)
    fraction_axis(d)
    d.set_xlabel("Fraction confirmed magnetic by DFT (Wilson 95% CI)")
    d.set_title("D  DFT confirmation: Base groups", loc="left", fontsize=13, weight="bold", pad=14)
    fig.suptitle("MP-only magnetic-reference screening and DFT validation", y=.984, fontsize=16, weight="bold")
    fig.text(.5, .945, "PREVIEW - recalculated results; not an exact reproduction of the original Figure 4",
             ha="center", fontsize=11, color="#4D5963")
    fig.legend(handles=[Patch(facecolor="#DADFE3", edgecolor="#263746", label="Base"),
                        Patch(facecolor="#DADFE3", edgecolor="#263746", hatch=adapted_hatch,
                              label="Fine-tuned / Refined"),
                        Line2D([], [], marker="o", markerfacecolor="white", color="#263746",
                               linestyle="none", label="B: Base median"),
                        Line2D([], [], marker="D", markerfacecolor="white", color="#263746",
                               linestyle="none", label="B: FT / Refined median")],
               loc="upper center", bbox_to_anchor=(.55, .927), ncol=4, frameon=False,
               columnspacing=1.8, handlelength=1.8)
    return fig


def supplementary_figure(dft_overall, output_dir, dpi):
    fig, ax = plt.subplots(figsize=(8.3, 3.6))
    fig.subplots_adjust(left=.33, right=.965, bottom=.23, top=.95)
    supplementary_dft(ax, dft_overall)
    save(fig, output_dir / "FigureS_DFT_magnetic_vs_NM_like", dpi)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--summary", type=Path, default=ROOT / "results/mp_only/generator_summary.csv")
    p.add_argument("--scores", type=Path, default=ROOT / "results/mp_only/generator_scores.csv")
    p.add_argument("--dft-joined", type=Path, default=ROOT / "results/mp_only/dft_validation/dft_joined_mp_only.csv")
    p.add_argument("--dft-audit", type=Path, default=ROOT / "results/mp_only/dft_validation/dft_validation_audit.json")
    p.add_argument("--output-dir", type=Path, default=ROOT / "results/mp_only/figures")
    p.add_argument("--ignore-audit-source", action="store_true",
                   help="Only when moving the project and verified DFT audit provenance separately")
    p.add_argument("--allow-small", action="store_true", help="Permit deliberately small benchmark cohorts")
    p.add_argument("--n-bootstrap", type=int, default=1000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--dpi", type=int, default=600)
    args = p.parse_args()
    style()
    summary, scores, order = read_data(args.summary, args.scores, args.allow_small)
    joined, dft_generator, dft_overall, audit = load_dft(
        args.dft_joined, args.dft_audit, args.scores, args.ignore_audit_source
    )
    stat = statistics(summary, scores, order, args.n_bootstrap, args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stat.to_csv(args.output_dir / "figure_statistics.csv", index=False)
    dft_generator.to_csv(args.output_dir / "dft_confirmation_by_generator.csv", index=False)
    dft_overall.to_csv(args.output_dir / "dft_confirmation_by_pipeline_class.csv", index=False)
    separate_figures(stat, order, dft_generator, args.output_dir, args.dpi)
    combined_figure(stat, order, dft_generator, args.output_dir, args.dpi)
    supplementary_figure(dft_overall, args.output_dir, args.dpi)
    (args.output_dir / "figure_sources.json").write_text(json.dumps({
        "summary": str(args.summary.resolve()),
        "scores": str(args.scores.resolve()),
        "dft_joined": str(args.dft_joined.resolve()),
        "dft_audit": str(args.dft_audit.resolve()),
        "dft_reference_classes": ["AFM", "FM", "FiM", "NM"],
        "dft_matched": int(len(joined)),
        "historical_dft_cohort": True,
        "dft_selection_note": "Originally selected using the prior reference model; retrospective validation",
        "n_scored_total": int(summary["n_scored"].sum()),
        "n_input_total": int(summary["n_input"].sum()),
        "n_bootstrap": args.n_bootstrap,
        "seed": args.seed,
    }, indent=2), encoding="utf-8")
    print("Created four individual panels, combined figure, and supplementary DFT figure [PNG/PDF]")
    print("DFT matched:", len(joined))
    print("\nMP-only DFT confirmation by generator:\n", dft_generator.to_string(index=False))
    print("\nMP-only DFT confirmation by pipeline class:\n", dft_overall.to_string(index=False))
    print("Output:", args.output_dir.resolve())


if __name__ == "__main__":
    main()
