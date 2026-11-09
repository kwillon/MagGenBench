"""Frozen Figure 5A: histogram overlap and exact empirical sliced W1.

No property inference, filtering by display limits, or input modification.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd

from .manuscript_figure5_v2 import FIGURE_SOURCE, ENERGY, MOMENT, load_paired_predictions

FAMILIES = ("MatterGen", "Con-CDVAE", "CrystalFormer", "CrystaLLM", "Crys-JEPA")
COHORTS = (
    "mattergen_baseline", "mattergen_finetuned", "concdvae_baseline", "concdvae_finetuned",
    "crystalformer_baseline", "crystalformer_finetuned", "crystallm_baseline",
    "crystallm_finetuned", "crysjepa_base", "crysjepa_refined",
)
EXPECTED = (1657, 1376, 1864, 1299, 1080, 1380, 97, 217, 1764, 1543)
RESOLUTIONS = (10, 15, 20)
PAIRS = tuple(itertools.combinations(range(5), 2))
OUTPUT = Path("reproduced/figure5_overlap")


def load_population(source=FIGURE_SOURCE):
    raw, paired = load_paired_predictions(source)
    counts = paired.groupby("analysis_cohort").size().reindex(COHORTS)
    if len(raw) != 12281 or len(paired) != 12277 or tuple(counts) != EXPECTED:
        raise ValueError(f"STOP: publication population mismatch: {len(raw)}, {len(paired)}, {counts.to_dict()}")
    for column in ("structure_id", "sample_uid"):
        ids = raw[column].astype("string")
        if ids.isna().any() or ids.str.strip().eq("").any() or ids.duplicated().any():
            raise ValueError(f"STOP: missing or globally duplicated {column}")
    mapping = dict(zip(COHORTS, np.repeat(FAMILIES, 2)))
    paired["family"] = paired.analysis_cohort.map(mapping)
    return raw, paired


def standardize(values):
    values = np.asarray(values, dtype=float)
    mean, std = values.mean(axis=0), values.std(axis=0, ddof=0)
    if not np.isfinite(values).all() or np.any(std <= 0):
        raise ValueError("Finite, nonconstant variables required")
    return (values - mean) / std, mean, std


def common_edges(values, bins, shifted=False):
    """Equal width full pooled range; shifted grids extend rather than clip."""
    lo, hi = values.min(axis=0), values.max(axis=0)
    if shifted:
        width = (hi - lo) / bins
        return tuple(np.linspace(lo[d] - width[d]/2, hi[d] + width[d]/2, bins+2) for d in range(2))
    return tuple(np.linspace(lo[d], hi[d], bins+1) for d in range(2))


def bin_indices(values, edges):
    indices = [np.searchsorted(e, values[:, d], side="right") - 1 for d, e in enumerate(edges)]
    for d, edge in enumerate(edges):
        indices[d][values[:, d] == edge[-1]] = len(edge)-2
        if np.any((indices[d] < 0) | (indices[d] >= len(edge)-1)):
            raise ValueError("Grid excludes observations")
    return indices[0] * (len(edges[1])-1) + indices[1]


def histogram_mass(indices, size, weights=None):
    mass = np.bincount(indices, weights=weights, minlength=size).astype(float)
    return mass / mass.sum()


def overlap(p, q):
    return float(np.minimum(p, q).sum())


def fixed_directions(n=128, seed=1984):
    if n < 100:
        raise ValueError("At least 100 directions required")
    theta = np.random.default_rng(seed).uniform(0, np.pi, n)
    return np.column_stack((np.cos(theta), np.sin(theta)))


class SlicedW1:
    """Integrate |F-G| exactly on each merged projected support.

    Bootstrap multiplicities are empirical atom weights. Sorting is cached;
    unequal sample sizes require no interpolation or downsampling.
    """
    def __init__(self, x, y, directions):
        support = np.concatenate((x @ directions.T, y @ directions.T), axis=0)
        self.order = np.argsort(support, axis=0, kind="stable")
        self.gaps = np.diff(np.take_along_axis(support, self.order, axis=0), axis=0)
        self.n, self.m = len(x), len(y)

    def __call__(self, wx=None, wy=None):
        wx = np.ones(self.n) if wx is None else np.asarray(wx, float)
        wy = np.ones(self.m) if wy is None else np.asarray(wy, float)
        signed = np.concatenate((wx/wx.sum(), -wy/wy.sum()))
        cdf_difference = np.cumsum(signed[self.order], axis=0)[:-1]
        return float(np.mean(np.sum(np.abs(cdf_difference)*self.gaps, axis=0)))


def heatmap(values, path, title, cmap, maximum=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42, "font.size": 10})
    fig, ax = plt.subplots(figsize=(7.4, 6.2), layout="constrained")
    im = ax.imshow(values, cmap=cmap, vmin=0, vmax=maximum)
    ax.set_xticks(range(5), FAMILIES, rotation=30, ha="right")
    ax.set_yticks(range(5), FAMILIES)
    ax.set_title(title, pad=15)
    midpoint = (maximum or values.max()) / 2
    for i, j in itertools.product(range(5), repeat=2):
        ax.text(j, i, f"{values[i,j]:.3f}", ha="center", va="center",
                color="white" if values[i,j] > midpoint else "black")
    fig.colorbar(im, ax=ax, shrink=.85)
    fig.savefig(path)
    plt.close(fig)


def run(source=FIGURE_SOURCE, output=OUTPUT, repeats=500, projections=128, seed=1984):
    if repeats < 500:
        raise ValueError("At least 500 bootstrap replicates required")
    raw, paired = load_population(source)  # fail before writing outputs
    z, mean, std = standardize(paired[[ENERGY, MOMENT]].to_numpy())
    groups = [z[paired.family.eq(family)] for family in FAMILIES]
    sizes = [len(g) for g in groups]
    assert sum(sizes) == 12277
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    directions = fixed_directions(projections, seed)
    np.savetxt(output / "projection_directions.csv", directions, delimiter=",", header="energy,moment", comments="")
    grids = {b: common_edges(z, b) for b in RESOLUTIONS}
    indices = {b: [bin_indices(g, grids[b]) for g in groups] for b in RESOLUTIONS}
    masses = {b: [histogram_mass(i, b*b) for i in indices[b]] for b in RESOLUTIONS}
    solvers = [SlicedW1(groups[i], groups[j], directions) for i, j in PAIRS]
    swd = np.array([s() for s in solvers])
    estimates = {b: np.array([overlap(masses[b][i], masses[b][j]) for i,j in PAIRS]) for b in RESOLUTIONS}
    boot_ovl = {b: np.empty((repeats, 10)) for b in RESOLUTIONS}
    boot_swd = np.empty((repeats, 10))
    balanced = {b: np.empty((repeats, 10)) for b in RESOLUTIONS}
    # Independent streams keep projection, bootstrap and size checks reproducible.
    rng = np.random.default_rng(seed+1)
    balance_rng = np.random.default_rng(seed+2)
    n_equal = min(sizes)
    for r in range(repeats):
        weights = [rng.multinomial(n, np.full(n, 1/n)) for n in sizes]
        selections = [balance_rng.choice(n, n_equal, replace=False) for n in sizes]
        for b in RESOLUTIONS:
            hist = [histogram_mass(idx, b*b, w) for idx,w in zip(indices[b], weights)]
            equal_hist = [histogram_mass(idx[sel], b*b) for idx,sel in zip(indices[b], selections)]
            boot_ovl[b][r] = [overlap(hist[i],hist[j]) for i,j in PAIRS]
            balanced[b][r] = [overlap(equal_hist[i],equal_hist[j]) for i,j in PAIRS]
        boot_swd[r] = [solver(weights[i],weights[j]) for solver,(i,j) in zip(solvers, PAIRS)]
        if (r+1) % 50 == 0:
            print(f"Bootstrap {r+1}/{repeats}", flush=True)
    rows = []
    for p, (i,j) in enumerate(PAIRS):
        row = dict(family_a=FAMILIES[i], family_b=FAMILIES[j], n_a=sizes[i], n_b=sizes[j], swd=swd[p])
        row["swd_ci_low"], row["swd_ci_high"] = np.quantile(boot_swd[:,p], [.025,.975])
        row["swd_bootstrap_mean"] = boot_swd[:,p].mean()
        for b in RESOLUTIONS:
            row[f"ovl_{b}"] = estimates[b][p]
            row[f"ovl_{b}_ci_low"],row[f"ovl_{b}_ci_high"] = np.quantile(boot_ovl[b][:,p],[.025,.975])
            row[f"ovl_{b}_bootstrap_mean"] = boot_ovl[b][:,p].mean()
            row[f"balanced_{b}_median"] = np.median(balanced[b][:,p])
            row[f"balanced_{b}_q025"],row[f"balanced_{b}_q975"] = np.quantile(balanced[b][:,p],[.025,.975])
        rows.append(row)
    result = pd.DataFrame(rows)
    # Half-bin origin shift, same widths, extended edges include every observation.
    shift_rows = []
    for b in RESOLUTIONS:
        edges = common_edges(z,b,shifted=True)
        hist = [histogram_mass(bin_indices(g,edges),(b+1)**2) for g in groups]
        for p,(i,j) in enumerate(PAIRS):
            shift_rows.append(dict(bins=b, family_a=FAMILIES[i], family_b=FAMILIES[j],
                                   ovl=estimates[b][p], shifted_ovl=overlap(hist[i],hist[j])))
    pd.DataFrame(shift_rows).to_csv(output / "grid_origin_sensitivity.csv", index=False)
    result.to_csv(output / "pairwise_overlap.csv", index=False)
    np.savez_compressed(output / "resampling_distributions.npz", swd=boot_swd,
                        **{f"ovl_{b}":boot_ovl[b] for b in RESOLUTIONS},
                        **{f"balanced_{b}":balanced[b] for b in RESOLUTIONS})
    audit = raw.groupby("analysis_cohort").size().reindex(COHORTS).rename("source_rows").to_frame()
    audit["finite_pairs"] = EXPECTED
    audit["excluded"] = audit.source_rows-audit.finite_pairs
    audit.to_csv(output / "population_audit.csv")
    paired[["analysis_cohort", "sample_uid", "structure_id", "family"]].to_csv(output / "sample_manifest.csv", index=False)
    import matplotlib
    metadata = dict(source=str(source), source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                    publication_pdf_sha256=hashlib.sha256(Path("paper/figures/fig05_energy_magnetism.pdf").read_bytes()).hexdigest(),
                    source_rows=len(raw), finite_pairs=len(paired), global_duplicate_ids=0,
                    family_sizes=dict(zip(FAMILIES,sizes)), seed=seed, bootstrap_seed=seed+1,
                    balance_seed=seed+2, bootstrap_repeats=repeats, projections=projections,
                    swd_order=1, primary_bins=15, standardization_ddof=0,
                    mean=dict(zip((ENERGY,MOMENT),mean.tolist())),
                    std=dict(zip((ENERGY,MOMENT),std.tolist())),
                    edges={str(b):[e.tolist() for e in grids[b]] for b in RESOLUTIONS},
                    versions=dict(python=platform.python_version(), numpy=np.__version__,
                                  pandas=pd.__version__, matplotlib=matplotlib.__version__))
    (output / "analysis_parameters.json").write_text(json.dumps(metadata,indent=2)+"\n",encoding="utf-8")
    ovl_matrix, swd_matrix = np.eye(5), np.zeros((5,5))
    for p,(i,j) in enumerate(PAIRS):
        ovl_matrix[i,j] = ovl_matrix[j,i] = estimates[15][p]
        swd_matrix[i,j] = swd_matrix[j,i] = swd[p]
    heatmap(ovl_matrix,output / "overlap_matrix.pdf","Figure 5A: distribution overlap (15 x 15 bins)","Blues",1)
    heatmap(swd_matrix,output / "wasserstein_matrix.pdf",f"Figure 5A: sliced Wasserstein-1 ({projections} directions)","Purples")
    write_summary(output,result,metadata,audit,pd.DataFrame(shift_rows))
    print(result.to_string(index=False),flush=True)
    return result


def write_summary(output, result, params, audit, shifts):
    lines = ["# Figure 5A: quantitative distribution overlap", "",
             "## Population and provenance", "",
             "The exact publication CSV is read through `manuscript_figure5_v2.load_paired_predictions`. "
             "The publication wrapper is `scripts/illustrations/plot_paper_figures_3_5.py --publish`; "
             "the plotting implementation is `src/mvpipeline/analysis/manuscript_figure5_v2.py` "
             "(also callable via `scripts/illustrations/plot_manuscript_figure5_v2.py`). "
             "Its only property-data input is the frozen CSV below; no Parquet input is used. "
             "no publication files were regenerated. Older eight-cohort analysis tables are not substituted.",
             f"Source: `{params['source']}`; SHA256 `{params['source_sha256']}`.",
             "12,281 source rows; exactly 12,277 pairs with both predictions finite. "
             "Both structure_id and sample_uid are nonempty and globally unique across all source rows. "
             "The exact ten cohort counts are asserted. No CHGNet/DXMag inference or input changes.", "",
             "| Cohort | Source | Finite | Excluded |", "|---|---:|---:|---:|"]
    for name,row in audit.iterrows():
        lines.append(f"| {name} | {row.source_rows} | {row.finite_pairs} | {row.excluded} |")
    lines += ["", "Pooled Base + FT (Crys-JEPA: Base + Refined): " + "; ".join(f"{k}: {v}" for k,v in params['family_sizes'].items()) + ". Total: 12,277.",
              "", "## Methods", "",
              "Variables: CHGNet total energy per atom (eV/atom), DXMag predicted moment (mu_B/f.u.). "
              "Negative predictions are retained. All finite points, including those beyond the figure's display window, are included.",
              "Standardization uses the pooled, structure-weighted population mean and SD (ddof=0), "
              "saved with exact bin edges and software versions in analysis_parameters.json:", ""]
    for col in (ENERGY,MOMENT):
        lines.append(f"- {col}: mean = {params['mean'][col]:.12g}; SD = {params['std'][col]:.12g}.")
    lines += ["", "OVL = sum(min(P_bin,Q_bin)); each family histogram is normalized to unit probability mass. "
              "All families share equal-width edges over the full pooled min-max range. The primary resolution "
              "is 15 x 15, with 10 x 10 and 20 x 20 sensitivity analyses. There is no density smoothing or clipping.",
              f"SWD is sliced Wasserstein-1 (p=1): the arithmetic mean of exact empirical one-dimensional W1 "
              f"over {params['projections']} uniform random angles in [0,pi), generated once with NumPy default_rng({params['seed']}). "
              "Each W1 integrates the absolute empirical CDF difference over merged projected supports. "
              "This handles unequal sample sizes exactly. SWD is in pooled standardized coordinates, not physical units.",
              f"{params['bootstrap_repeats']} nonparametric bootstrap replicates resample structures independently "
              "within each family, preserving its original n. Multinomial multiplicities are exactly equivalent "
              "to sampling rows with replacement and preserve each energy-moment pair. The same replicate "
              "weights are used for all metrics and pairs. 95% percentile intervals (2.5%,97.5%) are pointwise; "
              "there is no multiple-comparison coverage claim. Standardization, edges and directions remain fixed, "
              "so intervals are conditional on those choices. They describe structure-level sampling uncertainty, "
              "not prediction error, seed/batch dependence, or the full generator population.",
              "OVL is a nonsmooth plug-in estimator: finite samples, sparse bins and bootstrap bias can lower "
              "estimates; percentile intervals are approximate and need not include the point estimate. "
              "Bootstrap means are supplied to expose this effect. No bias correction is claimed.",
              f"Size sensitivity: {params['bootstrap_repeats']} repeated samples without replacement of "
              f"{min(params['family_sizes'].values())} structures per family. CrystaLLM remains intact; other "
              "families are reduced. These subsampling quantiles are diagnostic ranges, NOT population confidence "
              "intervals. They separate unequal n effects from full-sample results without discarding data in the main analysis.",
              "Grid-origin sensitivity shifts each axis by half a bin, extending the outer bounds to retain all data. "
              "Grid-origin and size checks supplement resolution sensitivity; a coarse-bin OVL is not an estimate "
              "of exact continuous support intersection.", "", "## Results", "",
              "| Resolution | Median OVL | Min | Max |", "|---|---:|---:|---:|"]
    for b in RESOLUTIONS:
        v=result[f"ovl_{b}"]
        lines.append(f"| {b} x {b} | {v.median():.6f} | {v.min():.6f} | {v.max():.6f} |")
    lines += ["", "| Pair | OVL (15 x 15), 95% CI | SWD1, 95% CI |", "|---|---|---|"]
    for _,r in result.iterrows():
        lines.append(f"| {r.family_a} / {r.family_b} | {r.ovl_15:.4f} [{r.ovl_15_ci_low:.4f}, {r.ovl_15_ci_high:.4f}] | {r.swd:.4f} [{r.swd_ci_low:.4f}, {r.swd_ci_high:.4f}] |")
    for label,idx in (("Lowest",result.ovl_15.idxmin()),("Highest",result.ovl_15.idxmax())):
        r=result.loc[idx]
        lines += ["",f"{label} primary OVL: {r.family_a} / {r.family_b}: {r.ovl_15:.6f}; corresponding SWD1 {r.swd:.6f}."]
    lines += ["", "## Robustness", "",
              "| CrystaLLM pair | OVL 10 / 15 / 20 | Balanced-n median OVL 10 / 15 / 20 |", "|---|---|---|"]
    for _,r in result.loc[result.family_a.eq("CrystaLLM") | result.family_b.eq("CrystaLLM")].iterrows():
        lines.append(f"| {r.family_a} / {r.family_b} | " + " / ".join(f"{r[f'ovl_{b}']:.4f}" for b in RESOLUTIONS) + " | " + " / ".join(f"{r[f'balanced_{b}_median']:.4f}" for b in RESOLUTIONS) + " |")
    lines += ["",f"Largest absolute OVL change across 10/15/20 grids: {result[[f'ovl_{b}' for b in RESOLUTIONS]].apply(lambda r:r.max()-r.min(),axis=1).max():.4f}.",
              f"Largest absolute half-bin-origin change: {(shifts.ovl-shifts.shifted_ovl).abs().max():.4f}.",
              "Full balanced-n ranges and bootstrap means are in pairwise_overlap.csv; raw resampling distributions "
              "are in resampling_distributions.npz. All 30 resolution-specific confidence intervals are supplied.",
              "", "## Interpretation and suggested manuscript wording", "",
              "The original statement is only partially supported: the histograms share probability mass, "
              "but the results do not support describing every pair as substantially overlapping. "
              "In particular, MatterGen / CrystaLLM has the lowest OVL and the largest SWD, "
              "whereas MatterGen / Con-CDVAE has the highest OVL and the smallest SWD. "
              "Use a qualified pairwise interpretation rather than a categorical claim about separation.", "",
              "OVL quantifies shared probability mass at a stated resolution; SWD quantifies displacement and shape "
              "differences without binning. Neither has a universal threshold for 'substantial'. Positive overlap "
              "in coarse cells does not prove continuous support overlap; low overlap does not prove complete "
              "separability. No classifier or separability test was performed. The phrase 'do not occupy clearly "
              "separated regions' should be qualified by pairwise heterogeneity, grid sensitivity and the small "
              "CrystaLLM sample. Pooling Base and adapted variants describes the observed mixture, whose weights "
              "differ by family, and may mask differences between variants.", "",
              "Suggested English text (Section 3.5; not inserted automatically):", "",
              f"> Across the five generator families, pairwise two-dimensional histogram overlap at 15 x 15 "
              f"resolution ranged from {result.ovl_15.min():.2f} to {result.ovl_15.max():.2f} "
              f"(median {result.ovl_15.median():.2f}), indicating shared regions of the predicted energy-moment "
              "landscape but appreciable variation in the degree of overlap. "
              f"Sliced Wasserstein-1 distances in pooled standardized coordinates ranged from {result.swd.min():.2f} "
              f"to {result.swd.max():.2f}, indicating differences between the empirical family distributions. "
              "These results should be interpreted alongside bin-resolution sensitivity and the smaller CrystaLLM "
              "sample, and do not establish either identical distributions or complete separation.",
              "", "## Reproduction", "", "```powershell",
              ".venv/Scripts/python.exe scripts/analysis/analyze_figure5_overlap.py",
              ".venv/Scripts/python.exe -m pytest -q tests/test_figure5_overlap.py",
              "```", "", "The script validates the publication population before creating outputs. "
              "No source CSV, manuscript text, or publication PDF is overwritten.",
              "", "## Sources", "",
              "- Repository and publication sources: https://github.com/kwillon/MagGenBench",
              "- Sliced Wasserstein definition (p explicitly selected as 1 here): https://pythonot.github.io/gen_modules/ot.sliced.html",
              "- One-dimensional empirical W1/CDF formulation: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wasserstein_distance.html", ""]
    (output / "analysis_summary.md").write_text("\n".join(lines),encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,default=FIGURE_SOURCE)
    parser.add_argument("--output",type=Path,default=OUTPUT)
    parser.add_argument("--bootstrap",type=int,default=500)
    parser.add_argument("--projections",type=int,default=128)
    parser.add_argument("--seed",type=int,default=1984)
    args=parser.parse_args()
    run(args.source,args.output,args.bootstrap,args.projections,args.seed)


if __name__ == "__main__":
    main()
