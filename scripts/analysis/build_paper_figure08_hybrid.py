"""Build a separate hybrid Figure 8 from frozen scenario outputs.

No training, generation, random weight sampling, or original-figure writes.
Run from any directory; the repository root is resolved from this file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, PowerNorm, to_rgb
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from mvpipeline.analysis.plotting_v2 import (
    apply_analysis_v2_publication_style,
)

COHORTS = [
    ("mattergen_baseline", "MatterGen Base", "MG-B"),
    ("mattergen_finetuned", "MatterGen FT", "MG-FT"),
    ("concdvae_baseline", "Con-CDVAE Base", "CD-B"),
    ("concdvae_finetuned", "Con-CDVAE FT", "CD-FT"),
    ("crystalformer_baseline", "CrystalFormer Base", "CF-B"),
    ("crystalformer_finetuned", "CrystalFormer FT", "CF-FT"),
    ("crystallm_baseline", "CrystaLLM Base", "CL-B"),
    ("crystallm_finetuned", "CrystaLLM FT", "CL-FT"),
    ("crysjepa_base", "Crys-JEPA Base", "JE-B"),
    ("crysjepa_refined", "Crys-JEPA Refined", "JE-R"),
]
ORDER = [c[0] for c in COHORTS]
LABELS = [c[1] for c in COHORTS]
METRICS = ["qc_retention_pct", "unique_formula_yield_pct", "3d_atomic_content_yield",
           "lanthanide_atomic_content_yield", "configured_3d_lanthanide_union_yield"]
SCENARIOS = ["S1", "S2", "S3"]
FAMILY_COLORS = {"mattergen": "#4F6745", "concdvae": "#61838F",
                 "crystalformer": "#E89339", "crystallm": "#AD463D", "crysjepa": "#304862"}
SEQUENTIAL = ["#F4EFE5", "#B2C1BC", "#829DA6", "#61838F", "#243350"]
DARK = "#243350"


def contrast_text(rgba):
    """Choose the higher-contrast palette text color by relative luminance."""
    def luminance(color):
        rgb = np.asarray(to_rgb(color))
        linear = np.where(rgb <= .04045, rgb/12.92, ((rgb+.055)/1.055)**2.4)
        return float(linear @ [.2126, .7152, .0722])
    bg, dark = luminance(rgba[:3]), luminance(DARK)
    dark_ratio = (max(bg, dark)+.05)/(min(bg, dark)+.05)
    return "white" if 1.05/(bg+.05) > dark_ratio else DARK


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=REPO / "paper/figures")
    parser.add_argument("--audit-dir", type=Path, default=REPO / "reproduced/figure8/hybrid_v2")
    args = parser.parse_args()
    paths = [args.output_dir / f"fig08_multiobjective_hybrid_v2.{ext}" for ext in ("pdf", "png")]
    audit_names = ["panel_A_metrics_pct.csv", "panel_B_S1_scatter.csv",
                   "panel_C_S1_rank_distribution_pct.csv", "panel_D_S1_top5_pct.csv",
                   "audit.json", "report.md"]
    existing = [p for p in paths + [args.audit_dir / n for n in audit_names] if p.exists()]
    if existing:
        parser.error("Refusing to overwrite existing outputs: " + ", ".join(map(str, existing)))
    source_paths = [REPO / "reproduced/figure8" / f"figure08_scenario_{n}_v2.csv"
                    for n in ("metrics", "rankings", "pareto")]
    protected = [*sorted((REPO / "paper/figures").glob("*.pdf")),
                 *sorted((REPO / "paper/figures").glob("*.png")),
                 REPO / "reproduced/figure8/figure08_scenarios_v2.pdf",
                 REPO / "reproduced/figure8/figure08_scenarios_v2.png"]
    source_paths += protected
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {str(p.relative_to(REPO)): digest(p) for p in source_paths}
    metrics, rankings, pareto = [pd.read_csv(p, float_precision="round_trip") for p in source_paths[:3]]
    assert len(metrics) == 90 and len(rankings) == 30 and len(pareto) == 300
    assert not metrics.duplicated(["variant", "analysis_cohort", "criterion"]).any()
    assert not rankings.duplicated(["variant", "analysis_cohort"]).any()
    assert not pareto.duplicated(["variant", "analysis_cohort", "compared_cohort"]).any()
    assert metrics.n_generated_assumed.eq(2000).all()
    assert rankings.n_weights.eq(20000).all()
    for frame in (metrics, rankings, pareto):
        assert set(frame.analysis_cohort) == set(ORDER)
        assert set(frame.variant) == set(SCENARIOS)
    assert np.isfinite(metrics.value_pct).all() and metrics.value_pct.between(0, 100).all()
    panel_a = pd.DataFrame(index=pd.Index(ORDER, name="analysis_cohort"))
    first_place = pd.DataFrame(index=panel_a.index)
    s1_pareto = None
    for scenario, chemical in zip(SCENARIOS, METRICS[2:]):
        selected = metrics.loc[metrics.variant.eq(scenario)]
        assert set(selected.criterion) == {*METRICS[:2], chemical}
        assert selected.groupby("analysis_cohort").n_qc.nunique().eq(1).all()
        for metric in [*METRICS[:2], chemical]:
            r = selected.loc[selected.criterion.eq(metric)].set_index("analysis_cohort").loc[ORDER]
            if metric in panel_a:
                np.testing.assert_allclose(panel_a[metric], r.value_pct, rtol=0, atol=1e-12)
            panel_a[metric] = r.value_pct
        ranked = rankings.loc[rankings.variant.eq(scenario)].set_index("analysis_cohort").loc[ORDER]
        first_place[scenario] = ranked.first_place_pct
        np.testing.assert_allclose(first_place[scenario].sum(), 100, rtol=0, atol=1e-10)
        x = panel_a[[*METRICS[:2], chemical]].to_numpy()
        z = (x-x.min(axis=0))/np.ptp(x, axis=0)
        saved_z = selected.pivot(index="analysis_cohort", columns="criterion", values="normalized_score")
        np.testing.assert_allclose(z, saved_z.loc[ORDER, [*METRICS[:2], chemical]], rtol=0, atol=1e-12)
        np.testing.assert_allclose(z.mean(axis=1), ranked.equal_weight_score, rtol=0, atol=1e-12)
        equal_ranks = np.argsort(np.argsort(-z.mean(axis=1), kind="stable"), kind="stable")+1
        np.testing.assert_array_equal(equal_ranks, ranked.equal_weight_rank)
        dominates = (x[:, None, :] >= x[None, :, :]).all(axis=2) & (x[:, None, :] > x[None, :, :]).any(axis=2)
        pairs = pareto.loc[pareto.variant.eq(scenario)]
        saved_dominance = pairs.pivot(index="analysis_cohort", columns="compared_cohort", values="dominates").loc[ORDER, ORDER]
        np.testing.assert_array_equal(dominates, saved_dominance)
        assert pairs.groupby("analysis_cohort").pareto_efficient.nunique().eq(1).all()
        saved_pareto = pairs.groupby("analysis_cohort").pareto_efficient.first().loc[ORDER]
        np.testing.assert_array_equal(~dominates.any(axis=0), saved_pareto)
        if scenario == "S1":
            s1_pareto = saved_pareto
    panel_a = panel_a[METRICS]
    s1 = rankings.loc[rankings.variant.eq("S1")].set_index("analysis_cohort").loc[ORDER]
    rank_cols = [f"rank_{i}_pct" for i in range(1, 11)]
    # Full S1 distribution is already saved; do not reconstruct or resample it.
    panel_c = s1[rank_cols].copy()
    p = panel_c.to_numpy()
    assert np.isfinite(p).all() and ((p >= 0) & (p <= 100)).all()
    np.testing.assert_allclose(p.sum(axis=1), 100, rtol=0, atol=1e-10)
    np.testing.assert_allclose(p.sum(axis=0), 100, rtol=0, atol=1e-10)
    np.testing.assert_allclose(p*200, np.round(p*200), rtol=0, atol=1e-9)
    for n in (1, 3, 5):
        column = "first_place_pct" if n == 1 else f"top{n}_pct"
        np.testing.assert_allclose(p[:, :n].sum(axis=1), s1[column], rtol=0, atol=1e-10)
    np.testing.assert_allclose(p @ np.arange(1, 11)/100, s1.mean_rank, rtol=0, atol=1e-12)
    np.testing.assert_allclose(panel_c.rank_1_pct, first_place.S1, rtol=0, atol=1e-12)
    # D derives from exactly the five leftmost columns of the S1 matrix in C.
    top5 = panel_c[rank_cols[:5]].sum(axis=1)
    np.testing.assert_allclose(top5, s1.top5_pct, rtol=0, atol=1e-10)
    top5_counts = np.rint(top5.to_numpy()*200).astype(int)
    panel_d = pd.DataFrame({"label": LABELS, "top5_count": top5_counts,
                            "n_weights": 20000, "top5_pct": top5_counts/200,
                            "family_color": [FAMILY_COLORS[c.split('_')[0]] for c in ORDER]}, index=panel_a.index)
    panel_d = panel_d.sort_values("top5_pct", ascending=False, kind="stable")
    assert panel_d.top5_pct.is_monotonic_decreasing
    np.testing.assert_allclose(panel_d.top5_pct.sum(), 500, rtol=0, atol=1e-10)
    panel_b = panel_a[METRICS[:3]].copy()
    panel_b["S1_pareto_efficient"] = s1_pareto
    panel_b["marker_area_pt2"] = 55 + 2*panel_b[METRICS[2]]
    previous_audit = REPO / "reproduced/figure8/hybrid"
    for filename, frame in (("panel_A_metrics_pct.csv", panel_a),
                            ("panel_C_S1_rank_distribution_pct.csv", panel_c)):
        previous_path = previous_audit / filename
        if previous_path.exists():
            previous = pd.read_csv(previous_path, index_col=0, float_precision="round_trip")
            np.testing.assert_allclose(frame, previous.loc[frame.index, frame.columns], rtol=0, atol=1e-12)

    apply_analysis_v2_publication_style()
    plt.rcParams.update({"font.size": 12, "axes.titlesize": 15, "axes.labelsize": 12,
                         "xtick.labelsize": 11, "ytick.labelsize": 11, "legend.fontsize": 10,
                         "text.color": DARK, "axes.labelcolor": DARK, "axes.edgecolor": DARK,
                         "xtick.color": DARK, "ytick.color": DARK, "grid.color": SEQUENTIAL[1]})
    cmap = LinearSegmentedColormap.from_list("art_nouveau_sequential", SEQUENTIAL)
    rank_cmap = cmap
    colors = {c: FAMILY_COLORS[c.split('_')[0]] for c in ORDER}
    fig = plt.figure(figsize=(17.4, 11.8), layout="constrained")
    fig.get_layout_engine().set(w_pad=0.12, h_pad=0.12, wspace=0.10, hspace=0.10)
    grid = fig.add_gridspec(2, 2, width_ratios=[1.28, 1])
    a, b, c, d = [fig.add_subplot(grid[i, j]) for i, j in [(0, 0), (0, 1), (1, 0), (1, 1)]]
    values = panel_a.to_numpy()
    normalized = (values-values.min(axis=0))/np.ptp(values, axis=0)
    im_a = a.imshow(normalized, aspect="auto", cmap=cmap, vmin=0, vmax=1)
    a.set_xticks(range(5), ["QC\nretention", "Unique-formula\nyield", "3d atomic-\ncontent yield",
                           "Lanthanide atomic-\ncontent yield", "3d / lanthanide\nunion yield"])
    for i in range(10):
        for j in range(5):
            v = values[i, j]
            a.text(j, i, f"{v:.4f}%" if 0 < v < .01 else f"{v:.2f}%",
                   ha="center", va="center", fontsize=11,
                   color=contrast_text(cmap(normalized[i, j])))
    cb_a = fig.colorbar(im_a, ax=a, orientation="horizontal", shrink=.82, pad=.035,
                       fraction=.055, aspect=40, ticks=[0, .5, 1])
    cb_a.set_label("Min-max normalized score", fontsize=11)
    a.set_title("A  Structural and chemical metrics", loc="left", fontweight="bold", pad=15)

    offsets = [(7, 4), (7, -12), (-35, 10), (-48, -13), (7, 6), (8, 7),
               (7, -12), (7, 6), (8, -2), (7, 6)]
    for i, (cohort, label, short) in enumerate(COHORTS):
        x, y, _ = panel_b.iloc[i, :3]
        marker = "s" if cohort.endswith("_finetuned") else "D" if cohort.endswith("_refined") else "o"
        efficient = bool(s1_pareto.loc[cohort])
        b.scatter(x, y, s=panel_b.loc[cohort, "marker_area_pt2"], marker=marker,
                  color=colors[cohort], edgecolors=DARK if efficient else "#FFFFFF",
                  linewidths=1.7 if efficient else .8, alpha=1, zorder=3)
        b.annotate(short, (x, y), xytext=offsets[i], textcoords="offset points", fontsize=11, color=DARK)
    b.set(xlim=(0, 101), ylim=(-3, 101), xlabel="QC retention (%)", ylabel="Unique-formula yield (%)")
    b.set_xticks([0, 20, 40, 60, 80, 100])
    b.set_yticks([0, 20, 40, 60, 80, 100])
    b.set_title("B  Structural yield vs diversity (S1)", loc="left", fontweight="bold", pad=15)
    b.grid(alpha=.15, linewidth=.5)
    b.set_axisbelow(True)
    handles = [Line2D([], [], linestyle="", marker="o", color=SEQUENTIAL[2], markeredgecolor=DARK,
                      markeredgewidth=1.7, markersize=8, label="S1 Pareto-efficient")]
    handles += [b.scatter([], [], s=55+2*v, color=SEQUENTIAL[2], edgecolors="white", label=f"{v}%")
                for v in (10, 30, 50)]
    legend_b = b.legend(handles=handles, title="3d atomic-content yield", title_fontsize=10,
                        loc="upper left", frameon=False, labelspacing=.9, borderaxespad=1)

    norm_c = PowerNorm(gamma=.55, vmin=0, vmax=100)
    im_c = c.imshow(p, aspect="auto", norm=norm_c, cmap=rank_cmap)
    c.set_xticks(range(10), range(1, 11))
    c.set_xlabel("Rank")
    c.set_title("C  Rank stability (S1)", loc="left", fontweight="bold", pad=15)
    cb_c = fig.colorbar(im_c, ax=c, orientation="horizontal", shrink=.82, pad=.035,
                       fraction=.055, aspect=40, ticks=[0, 10, 25, 50, 100])
    cb_c.set_label("Weight combinations (%)", fontsize=11)

    bars = d.barh(np.arange(10), panel_d.top5_pct, color=panel_d.family_color,
                  edgecolor="white", linewidth=.7, height=.70, zorder=3)
    d.set_yticks(np.arange(10), panel_d.label)
    d.invert_yaxis()
    d.set_xlim(0, 118)
    d.set_xticks([0, 20, 40, 60, 80, 100])
    d.set_xlabel("Top-5 frequency (%)")
    d.set_title("D  Top-5 frequency (S1)", loc="left", fontweight="bold", pad=15)
    d.grid(axis="x", alpha=.25, linewidth=.5)
    d.set_axisbelow(True)
    for bar, value in zip(bars, panel_d.top5_pct):
        d.text(value+1.2, bar.get_y()+bar.get_height()/2, f"{value:.3f}%",
               va="center", ha="left", fontsize=11, color=DARK)
    for ax in (a, c):
        ax.set_yticks(range(10), LABELS)
        ax.tick_params(axis="both", length=0)
        ax.set_xticks(np.arange(-.5, len(ax.get_xticks()), 1), minor=True)
        ax.set_yticks(np.arange(-.5, 10, 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=1.2)
        ax.tick_params(which="minor", length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
    # No footer, caption, or explanatory text below the four panels.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    annotations = list(b.texts)
    for text in d.texts:
        box = text.get_window_extent(renderer)
        assert box.x1 < d.get_window_extent(renderer).x1, text.get_text()
    for i, annotation in enumerate(annotations):
        box = annotation.get_window_extent(renderer)
        assert not box.overlaps(legend_b.get_window_extent(renderer)), annotation.get_text()
        for other in annotations[i+1:]:
            assert not box.overlaps(other.get_window_extent(renderer)), (annotation.get_text(), other.get_text())
    # Verify the colorbars stay clear of panel tick labels and axis labels.
    for ax, cb in ((a, cb_a), (c, cb_c)):
        bar_box = cb.ax.get_window_extent(renderer)
        for artist in [*ax.get_xticklabels(), ax.xaxis.label]:
            if artist.get_text():
                assert not bar_box.overlaps(artist.get_window_extent(renderer)), artist.get_text()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.audit_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=.08)
    plt.close(fig)
    for name, frame in zip(audit_names[:4], (panel_a, panel_b, panel_c, panel_d)):
        frame.to_csv(args.audit_dir/name)
    assert all(digest(REPO/p) == sha for p, sha in before.items())
    audit = dict(status="PASS", seed_of_saved_calculation=1984, n_weights=20000,
                 rank_distribution_source="saved S1 rank_1_pct through rank_10_pct; no resampling",
                 panel_A="five saved metrics, per-column min-max colors, original percentages annotated",
                 panel_B="QC vs formula yield; area = 55 + 2 * S1 atomic-content yield; S1 Pareto outlines",
                 panel_C="saved S1 rank distribution, percent of 20000 weight combinations",
                 panel_D="S1 Top-5 frequency = sum of C ranks 1-5; descending stable order", source_sha256=before,
                 family_colors=FAMILY_COLORS, sequential_gradient=SEQUENTIAL,
                 checks=["A repeated structural metrics agree across S1-S3", "all equal scores and ranks verified",
                         "Pareto dominance verified for all scenarios", "C row and column sums equal 100%",
                         "C frequencies correspond to integer counts out of 20000",
                         "C first/top3/top5/mean rank agree with saved S1 summaries",
                         "D equals C ranks 1-5 and saved S1 top5_pct",
                         "D integer counts total 100000 (5 ranks times 20000 weights)",
                         "D sorted descending; equal frequencies retain cohort order",
                         "colorbars clear of tick and axis labels", "input and old figure hashes unchanged"],
                 output_sha256={str(p):digest(p) for p in paths})
    (args.audit_dir/"audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    report = """# Figure 8 hybrid v2: audit

Date: 2026-11-09. Validation: PASS.

- A: all five metrics, original values, model order, and min-max normalization are unchanged. Only the palette and text contrast changed. A nonzero value below 0.01% is printed with four decimals.
- B: the S1 scatter retains its coordinates, marker areas (55 + 2 × 3d atomic-content yield) and Pareto outlines. Base/FT/Refined use circle/square/diamond markers; every variant now uses the same specified family color.
- C: the complete saved S1 rank 1-10 distribution is unchanged. Its sequential palette now matches A. Results use 20000 Dirichlet(1,1,1) weights and seed 1984; there was no resampling.
- D: the horizontal Top-5 bar design is restored. Each value is obtained by summing C's saved S1 rank_1_pct through rank_5_pct and verified against the saved S1 top5_pct. All ten sets appear, sorted descending with stable cohort order for ties. Bars use family colors; three-decimal percentage labels follow bar ends, preserving the 0.005 percentage-point resolution of 20000 weights. Old 3d-containing results and first-place frequencies are not used for these bars.

Only display normalization, marker areas and D's sum of saved rank frequencies were calculated for plotting. Normalized equal-weight scores/ranks and Pareto dominance were independently recalculated as validation checks, without replacing saved results. C row/column sums, integer counts out of 20000, mean rank, and first/top3/top5 summaries pass. D counts sum to 100000 (five occupied ranks per weight), so its frequencies correctly sum to 500%, not 100%. All yields use Ngen=2000; atomic-content yields sum per-structure fractions over QC-retained structures, while S3 counts presence of either configured group (OR, not AND).

The four panels retain a 2×2 layout, white background, no explanatory footer, unified 11-12 pt labels and 15 pt headings, and embedded TrueType PDF fonts. Family palette: MatterGen #4F6745; Con-CDVAE #61838F; CrystalFormer #E89339; CrystaLLM #AD463D; Crys-JEPA #304862. A/C sequential gradient: #F4EFE5 -> #B2C1BC -> #829DA6 -> #61838F -> #243350. A annotations choose dark/white text using relative luminance for contrast. Article text and previous publication figures were not changed; their hashes are checked.

Inputs: `reproduced/figure8/figure08_scenario_metrics_v2.csv`, `figure08_scenario_rankings_v2.csv`, and `figure08_scenario_pareto_v2.csv`. Implementation follows `scripts/analysis/build_paper_figure08.py` and imports the existing `plotting_v2` publication style. Exact source/output SHA256 hashes and numeric checks are in `audit.json`; four panel-source CSVs accompany this report.
"""
    report += "\n## S1 Top-5 frequencies\n\n| Generated set | Top-5 count / 20000 | Frequency (%) |\n|---|---:|---:|\n"
    for _, row in panel_d.iterrows():
        report += f"| {row['label']} | {row['top5_count']} | {row['top5_pct']:.3f} |\n"
    (args.audit_dir/"report.md").write_text(report, encoding="utf-8")
    print("PASS: hybrid A/B/C/D checks; source and original-figure hashes unchanged.")
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
