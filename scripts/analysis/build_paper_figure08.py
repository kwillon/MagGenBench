import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, PowerNorm

from mvpipeline.analysis.plotting_v2 import (
    ANALYSIS_V2_MAGNETIC_COHORT_COLORS,
    apply_analysis_v2_publication_style,
)

parser = argparse.ArgumentParser(description="Build Figure 8 benchmark metrics")
parser.add_argument(
    "--chemistry-only", action="store_true",
    help="Export chemistry metrics without writing existing Figure 8 results",
)
parser.add_argument(
    "--compare-criteria", action="store_true",
    help="Compare three criterion systems without writing existing Figure 8 results",
)
parser.add_argument(
    "--compare-scenarios", action="store_true",
    help="Compare three research scenarios without writing existing Figure 8 results",
)
parser.add_argument(
    "--compare-ablation", action="store_true",
    help="Compare two-objective controls without writing existing Figure 8 results",
)
parser.add_argument(
    "--build-figure8-v2", action="store_true",
    help="Plot the saved S1-S3 results without recalculating rankings",
)
args = parser.parse_args()
if sum((args.chemistry_only, args.compare_criteria, args.compare_scenarios,
        args.compare_ablation, args.build_figure8_v2)) > 1:
    parser.error("Choose only one calculation or figure-building mode")

ROOT = Path("tables/figure_sources")
MASTER = Path("tables/10_analysis_v2_magnetic/analysis_v2_magnetic.csv")
OUTPUT = Path("reproduced/figure8")
SAVED = Path("tables/figure_sources/figure8")
OUTPUT.mkdir(parents=True, exist_ok=True)

COHORTS = [
    ("mattergen_baseline", "MatterGen Base"),
    ("mattergen_finetuned", "MatterGen FT"),
    ("concdvae_baseline", "Con-CDVAE Base"),
    ("concdvae_finetuned", "Con-CDVAE FT"),
    ("crystalformer_baseline", "CrystalFormer Base"),
    ("crystalformer_finetuned", "CrystalFormer FT"),
    ("crystallm_baseline", "CrystaLLM Base"),
    ("crystallm_finetuned", "CrystaLLM FT"),
    ("crysjepa_base", "Crys-JEPA Base"),
    ("crysjepa_refined", "Crys-JEPA Refined"),
]
ORDER = [x[0] for x in COHORTS]
LABELS = dict(COHORTS)

if args.build_figure8_v2:
    inputs = [SAVED / f"figure08_scenario_{name}_v2.csv"
              for name in ("metrics", "rankings", "pareto")]
    missing = [path for path in inputs if not path.is_file()]
    if missing:
        parser.exit(2, "Missing Figure 8 v2 inputs:\n" + "\n".join(map(str, missing))
                    + "\nRun scripts/analysis/build_paper_figure08.py --compare-scenarios first.\n"
                    "If its A/B/C inputs are missing, first run the same script with --compare-criteria.\n"
                    "Both calculation modes use the existing tracked figure-source CSVs.\n")
    scenario_metrics, scenario_ranks, scenario_pareto = [pd.read_csv(path) for path in inputs]
    scenarios = ["S1", "S2", "S3"]
    metric_order = ["qc_retention_pct", "unique_formula_yield_pct",
                    "3d_atomic_content_yield", "lanthanide_atomic_content_yield",
                    "configured_3d_lanthanide_union_yield"]
    assert len(scenario_metrics) == 90 and len(scenario_ranks) == 30 and len(scenario_pareto) == 300
    for frame in (scenario_metrics, scenario_ranks, scenario_pareto):
        assert set(frame.variant) == set(scenarios)
        assert set(frame.analysis_cohort) == set(ORDER)
    assert not scenario_metrics.duplicated(["variant", "analysis_cohort", "criterion"]).any()
    assert not scenario_ranks.duplicated(["variant", "analysis_cohort"]).any()
    assert not scenario_pareto.duplicated(["variant", "analysis_cohort", "compared_cohort"]).any()
    assert scenario_metrics.n_generated_assumed.eq(2000).all()
    assert np.isfinite(scenario_metrics.value_pct).all()
    assert scenario_metrics.value_pct.between(0, 100).all()
    assert scenario_ranks.n_weights.eq(20000).all()
    assert scenario_pareto.pareto_efficient.isin([True, False]).all()
    assert scenario_pareto.dominates.isin([True, False]).all()
    panel_metrics = pd.DataFrame(index=ORDER)
    panel_pareto = pd.DataFrame(index=ORDER)
    panel_ranks = pd.DataFrame(index=ORDER)
    panel_frequency = pd.DataFrame(index=ORDER)
    for scenario, chemical in zip(scenarios, metric_order[2:]):
        metrics = scenario_metrics.loc[scenario_metrics.variant.eq(scenario)]
        assert set(metrics.criterion) == {metric_order[0], metric_order[1], chemical}
        assert metrics.groupby("analysis_cohort").n_qc.nunique().eq(1).all()
        for metric in (metric_order[0], metric_order[1], chemical):
            rows = metrics.loc[metrics.criterion.eq(metric)].set_index("analysis_cohort").loc[ORDER]
            assert rows.n_qc.between(1, 2000).all()
            if metric in panel_metrics:
                assert np.allclose(panel_metrics[metric], rows.value_pct, rtol=0, atol=1e-12)
            panel_metrics[metric] = rows.value_pct
        ranks = scenario_ranks.loc[scenario_ranks.variant.eq(scenario)].set_index("analysis_cohort").loc[ORDER]
        assert np.array_equal(np.sort(ranks.equal_weight_rank), np.arange(1, 11))
        assert np.isfinite(ranks.first_place_pct).all()
        assert ranks.first_place_pct.between(0, 100).all()
        assert np.isclose(ranks.first_place_pct.sum(), 100, rtol=0, atol=1e-10)
        panel_ranks[scenario] = ranks.equal_weight_rank
        panel_frequency[scenario] = ranks.first_place_pct
        pairs = scenario_pareto.loc[scenario_pareto.variant.eq(scenario)]
        assert set(pairs.compared_cohort) == set(ORDER)
        assert pairs.groupby("analysis_cohort").pareto_efficient.nunique().eq(1).all()
        saved_status = pairs.groupby("analysis_cohort").pareto_efficient.first().reindex(ORDER)
        assert np.array_equal(saved_status, ~pairs.groupby("compared_cohort").dominates.any().reindex(ORDER))
        panel_pareto[scenario] = saved_status
    panel_metrics = panel_metrics[metric_order]
    values = panel_metrics.to_numpy(dtype=float)
    span = np.ptp(values, axis=0)
    normalized = np.divide(values - values.min(axis=0), span,
                           out=np.zeros_like(values), where=span > 0)

    apply_analysis_v2_publication_style()
    plt.rcParams.update({"font.size": 10, "ytick.labelsize": 9,
                         "xtick.labelsize": 9, "axes.titlesize": 12})
    metric_cmap = LinearSegmentedColormap.from_list(
        "scenario_metric", ["#F7F8F6", "#C9DCE2", "#8BAEBA", "#4F8296", "#24526C"],
    )
    pareto_cmap = LinearSegmentedColormap.from_list("scenario_pareto", ["#F0F2F1", "#24526C"])
    fig = plt.figure(figsize=(16, 12.8), layout="constrained")
    grid = fig.add_gridspec(3, 2, height_ratios=[1, 1, 0.19], width_ratios=[1.45, 1])
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[1, 0])
    ax_d = fig.add_subplot(grid[1, 1])
    scenario_ticks = ["S1\n3d-focused", "S2\nLanthanide-focused", "S3\nBroad exploration"]
    labels = [LABELS[cohort] for cohort in ORDER]

    image_a = ax_a.imshow(normalized, aspect="auto", vmin=0, vmax=1, cmap=metric_cmap)
    ax_a.set_xticks(range(5), ["QC\nretention", "Unique-formula\nyield", "3d atomic-\ncontent yield",
                              "Lanthanide atomic-\ncontent yield", "Configured 3d /\nlanthanide union yield"])
    ax_a.set_title("A  Structural and chemical metrics", loc="left", fontweight="bold", pad=14)
    for i in range(10):
        for j in range(5):
            cell = f"{values[i, j]:.4f}%" if 0 < values[i, j] < 0.01 else f"{values[i, j]:.2f}%"
            ax_a.text(j, i, cell, ha="center", va="center", fontsize=9,
                      color="white" if normalized[i, j] > 0.7 else "#173247")
    fig.colorbar(image_a, ax=ax_a, orientation="horizontal", shrink=0.82, pad=0.07,
                 ticks=[0, 0.5, 1], label="Color: min-max normalized within each metric; numbers: original (%)")

    ax_b.imshow(panel_pareto.to_numpy(dtype=int), aspect="auto", vmin=0, vmax=1, cmap=pareto_cmap)
    ax_b.set_xticks(range(3), scenario_ticks)
    ax_b.set_title("B  Scenario-specific Pareto efficiency", loc="left", fontweight="bold", pad=14)
    for i in range(10):
        for j in range(3):
            efficient = bool(panel_pareto.iloc[i, j])
            ax_b.text(j, i, "Yes" if efficient else "No", ha="center", va="center", fontsize=10,
                      color="white" if efficient else "#647078")
    ax_b.set_xlabel("Pareto-efficient: Yes / No", labelpad=9)

    image_c = ax_c.imshow(panel_ranks, aspect="auto", vmin=1, vmax=10, cmap=metric_cmap.reversed())
    ax_c.set_xticks(range(3), scenario_ticks)
    ax_c.set_title("C  Scenario-dependent rankings", loc="left", fontweight="bold", pad=14)
    for i in range(10):
        for j in range(3):
            rank = int(panel_ranks.iloc[i, j])
            ax_c.text(j, i, str(rank), ha="center", va="center", fontsize=10,
                      color="white" if rank <= 3 else "#173247")
    fig.colorbar(image_c, ax=ax_c, orientation="horizontal", shrink=0.82, pad=0.07,
                 ticks=[1, 3, 5, 7, 10], label="Equal-weight rank after min-max normalization (1 = best)")

    frequency_norm = PowerNorm(gamma=0.6, vmin=0, vmax=100)
    image_d = ax_d.imshow(panel_frequency, aspect="auto", norm=frequency_norm, cmap=metric_cmap)
    ax_d.set_xticks(range(3), scenario_ticks)
    ax_d.set_title("D  Ranking sensitivity", loc="left", fontweight="bold", pad=14)
    for i in range(10):
        for j in range(3):
            frequency = float(panel_frequency.iloc[i, j])
            ax_d.text(j, i, f"{frequency:.2f}%", ha="center", va="center", fontsize=10,
                      color="white" if frequency_norm(frequency) > 0.7 else "#173247")
    fig.colorbar(image_d, ax=ax_d, orientation="horizontal", shrink=0.82, pad=0.07,
                 ticks=[0, 10, 25, 50, 100], label="First-place frequency (%)")

    for ax in (ax_a, ax_b, ax_c, ax_d):
        ax.set_yticks(range(10), labels)
        ax.tick_params(axis="both", length=0)
        ax.set_xticks(np.arange(-0.5, len(ax.get_xticks()), 1), minor=True)
        ax.set_yticks(np.arange(-0.5, 10, 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=1.2)
        ax.tick_params(which="minor", length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
    footer = fig.add_subplot(grid[2, :])
    footer.axis("off")
    footer.text(0, 0.92,
                "All yields use a nominal budget of 2,000 generations per set; fractions are summed over QC-retained structures.\n"
                "S1 / S2 / S3 share QC retention and unique-formula yield; their chemical criterion is 3d atomic content / lanthanide atomic content / configured-group union.\n"
                "D: leadership frequencies across 20,000 Dirichlet(1,1,1) weight combinations (seed 1984), not probabilities of universal model superiority.\n"
                "Chemical proxies do not establish magnetic properties. S3 covers only the configured 3d and lanthanide groups, not all potentially magnetic elements.",
                transform=footer.transAxes, va="top", fontsize=9, linespacing=1.65, color="#425462")
    for extension in ("pdf", "png", "svg"):
        path = OUTPUT / f"figure08_scenarios_v2.{extension}"
        fig.savefig(path, dpi=300, bbox_inches="tight")
        print(path)
    plt.close(fig)
    print("FIGURE08 SCENARIOS V2: PASSED (saved S1-S3 results; no ranking recalculation)")
    raise SystemExit(0)

# Nominal generation budget; must be confirmed from provenance.
GENERATED_PER_COHORT = 2000

METRICS = [
    "qc_retention_pct",
    "unique_formula_yield_pct",
    "3d_containing_yield_pct",
]

# -----------------------------
# 1. Load and validate sources
# -----------------------------
div = pd.read_csv(ROOT / "fig06_diversity_summary.csv")
eng = pd.read_csv(ROOT / "fig05_energy_magnetism.csv")

assert len(div) == 10
assert len(eng) == 12281
assert set(div.analysis_cohort) == set(ORDER)
assert set(eng.analysis_cohort) == set(ORDER)
assert not div.analysis_cohort.duplicated().any()
assert not eng.duplicated(
    ["analysis_cohort", "sample_uid"]
).any()

counts = eng.groupby("analysis_cohort").size()
reported = div.set_index("analysis_cohort")["n"]

assert counts.reindex(ORDER).equals(
    reported.reindex(ORDER).astype(counts.dtype)
), "Cohort row counts disagree"

# -----------------------------
# 2. Collect composition proxy
# -----------------------------
columns = [
    "analysis_cohort",
    "sample_uid",
    "transition_3d_fraction",
    "configured_lanthanide_fraction",
]

old = pd.read_csv(
    MASTER, usecols=columns, low_memory=False
)

ft_files = {
    "crystalformer_finetuned":
        "crystalformer_finetuned_descriptors.csv",
    "crystallm_finetuned":
        "crystallm_finetuned_descriptors.csv",
}

frames = [old]

for cohort, filename in ft_files.items():
    frame = pd.read_csv(
        ROOT / filename,
        usecols=columns,
        low_memory=False,
    )
    assert set(frame.analysis_cohort) == {cohort}
    frames.append(frame)

mag = pd.concat(frames, ignore_index=True)

assert len(mag) == len(eng)
assert set(mag.analysis_cohort) == set(ORDER)
for frame in (eng, mag):
    assert frame.sample_uid.notna().all()
    assert frame.sample_uid.astype(str).str.strip().ne("").all()
    assert not frame.sample_uid.duplicated().any()
assert not mag.duplicated(
    ["analysis_cohort", "sample_uid"]
).any()

# Ensure the compared records are exactly the same.
left = pd.MultiIndex.from_frame(
    eng[["analysis_cohort", "sample_uid"]]
)
right = pd.MultiIndex.from_frame(
    mag[["analysis_cohort", "sample_uid"]]
)
assert left.is_unique and right.is_unique
assert left.difference(right).empty
assert right.difference(left).empty

fraction = pd.to_numeric(
    mag.transition_3d_fraction,
    errors="coerce",
)
assert np.isfinite(fraction).all()
assert fraction.between(0, 1).all()

mag["contains_3d"] = fraction > 0

count_3d = mag.groupby(
    "analysis_cohort"
)["contains_3d"].sum()

# -----------------------------
# 3. Build metric table
# -----------------------------
summary = div.set_index("analysis_cohort").reindex(ORDER)
summary = summary.copy()

summary["n_generated_assumed"] = GENERATED_PER_COHORT
summary["n_3d_containing"] = count_3d.reindex(ORDER)

assert (summary["n"] <= GENERATED_PER_COHORT).all()
assert (summary["n_unique_formula"] <= summary["n"]).all()
assert (summary["n_3d_containing"] <= summary["n"]).all()

summary["qc_retention_pct"] = (
    100 * summary["n"] / summary["n_generated_assumed"]
)
summary["unique_formula_yield_pct"] = (
    100 * summary["n_unique_formula"] /
    summary["n_generated_assumed"]
)
summary["3d_containing_yield_pct"] = (
    100 * summary["n_3d_containing"] /
    summary["n_generated_assumed"]
)

summary["within_qc_unique_formula_pct"] = (
    100 * summary["n_unique_formula"] / summary["n"]
)
summary["label"] = [LABELS[c] for c in ORDER]

# Export additional composition metrics separately from the ranked objectives.
lanthanide_fraction = pd.to_numeric(
    mag.configured_lanthanide_fraction, errors="coerce",
)
assert np.isfinite(lanthanide_fraction).all()
assert lanthanide_fraction.between(0, 1).all()

chemistry = summary[["label", "n", "n_generated_assumed",
                     "n_unique_formula", *METRICS]].rename(columns={"n": "n_qc"}).copy()
chemistry["n_descriptor_records"] = mag.groupby("analysis_cohort").size().reindex(ORDER)
assert chemistry.index.tolist() == ORDER and len(chemistry) == 10
assert chemistry["n_qc"].gt(0).all()
assert chemistry["n_descriptor_records"].equals(chemistry["n_qc"])

chemistry["n_3d_containing"] = fraction.gt(0).groupby(mag.analysis_cohort).sum().reindex(ORDER)
chemistry["n_lanthanide_containing"] = (
    lanthanide_fraction.gt(0).groupby(mag.analysis_cohort).sum().reindex(ORDER)
)
# Yields use the nominal generation budget; prevalence uses retained QC count.
chemistry["lanthanide_containing_yield"] = (
    100 * chemistry["n_lanthanide_containing"] / chemistry["n_generated_assumed"]
)
chemistry["mean_3d_fraction"] = fraction.groupby(mag.analysis_cohort).mean().reindex(ORDER)
chemistry["mean_lanthanide_fraction"] = (
    lanthanide_fraction.groupby(mag.analysis_cohort).mean().reindex(ORDER)
)
chemistry["within_qc_lanthanide_prevalence"] = (
    100 * chemistry["n_lanthanide_containing"] / chemistry["n_qc"]
)
assert chemistry["n_lanthanide_containing"].between(0, chemistry["n_qc"]).all()
assert np.allclose(
    chemistry["3d_containing_yield_pct"],
    100 * chemistry["n_3d_containing"] / chemistry["n_generated_assumed"],
    rtol=0, atol=1e-12,
)

# Check the original objectives against the existing publication snapshot.
previous = pd.read_csv(ROOT / "fig08_metric_matrix.csv").set_index("analysis_cohort")
assert len(previous) == 10 and previous.index.is_unique
assert set(previous.index) == set(ORDER)
previous = previous.reindex(ORDER)
assert chemistry["n_qc"].equals(previous["n"].rename("n_qc"))
assert chemistry["n_3d_containing"].equals(previous["n_3d_containing"])
assert np.allclose(chemistry[METRICS], previous[METRICS], rtol=0, atol=1e-12)

if not (args.compare_criteria or args.compare_scenarios or args.compare_ablation):
    chemistry.to_csv(OUTPUT / "figure08_chemistry_metrics_v2.csv")
if args.chemistry_only:
    print(chemistry.to_string())
    print("FIGURE08 CHEMISTRY METRICS: PASSED")
    raise SystemExit(0)

if args.compare_criteria or args.compare_scenarios or args.compare_ablation:
    # All comparison objectives use the same nominal generation denominator.
    comparison = chemistry.copy()
    comparison["3d_atomic_content_yield"] = (
        100 * fraction.groupby(mag.analysis_cohort).sum().reindex(ORDER)
        / comparison["n_generated_assumed"]
    )
    comparison["lanthanide_atomic_content_yield"] = (
        100 * lanthanide_fraction.groupby(mag.analysis_cohort).sum().reindex(ORDER)
        / comparison["n_generated_assumed"]
    )
    for metric, mean in (
        ("3d_atomic_content_yield", "mean_3d_fraction"),
        ("lanthanide_atomic_content_yield", "mean_lanthanide_fraction"),
    ):
        assert np.allclose(
            comparison[metric], 100 * comparison[mean] * comparison["n_qc"]
            / comparison["n_generated_assumed"], rtol=0, atol=1e-12,
        )
    assert comparison["n_generated_assumed"].eq(2000).all()
    variants = {
        "A": ("Original", METRICS),
        "B": ("Chemical presence", [*METRICS, "lanthanide_containing_yield"]),
        "C": ("Chemical fractions", [
            *METRICS[:2], "3d_atomic_content_yield", "lanthanide_atomic_content_yield",
        ]),
    }
    if args.compare_scenarios or args.compare_ablation:
        # This union is a composition proxy, not validated magnetism; it excludes
        # other potentially magnetic elements outside the two configured groups.
        contains_3d = fraction.gt(0)
        contains_lanthanide = lanthanide_fraction.gt(0)
        union_count = (contains_3d | contains_lanthanide).groupby(mag.analysis_cohort).sum().reindex(ORDER)
        overlap_count = (contains_3d & contains_lanthanide).groupby(mag.analysis_cohort).sum().reindex(ORDER)
        assert union_count.equals(
            comparison["n_3d_containing"] + comparison["n_lanthanide_containing"] - overlap_count
        )
        assert union_count.between(0, comparison["n_qc"]).all()
        comparison["configured_3d_lanthanide_union_yield"] = (
            100 * union_count / comparison["n_generated_assumed"]
        )
        variants = {
            "S1": ("3d-focused", [*METRICS[:2], "3d_atomic_content_yield"]),
            "S2": ("Lanthanide-focused", [*METRICS[:2], "lanthanide_atomic_content_yield"]),
            "S3": ("Broad chemical exploration", [*METRICS[:2], "configured_3d_lanthanide_union_yield"]),
        }
        baseline_rankings = pd.read_csv(SAVED / "figure08_criteria_rankings_v2.csv")
        assert set(baseline_rankings.variant) == {"A", "B", "C"}
        assert not baseline_rankings.duplicated(["variant", "analysis_cohort"]).any()
        for baseline in ("A", "B", "C"):
            baseline_rows = baseline_rankings.loc[baseline_rankings.variant.eq(baseline)]
            assert baseline_rows.analysis_cohort.tolist() == ORDER
            assert baseline_rows.n_weights.eq(20000).all()
        baseline_metrics = pd.read_csv(SAVED / "figure08_criteria_metrics_v2.csv")
        for baseline in ("A", "B", "C"):
            for metric in baseline_metrics.loc[baseline_metrics.variant.eq(baseline), "criterion"].unique():
                rows = baseline_metrics.loc[
                    baseline_metrics.variant.eq(baseline) & baseline_metrics.criterion.eq(metric)
                ].set_index("analysis_cohort").loc[ORDER]
                assert rows.n_generated_assumed.eq(2000).all()
                assert np.array_equal(rows.n_qc, comparison["n_qc"])
                assert np.allclose(rows.value_pct, comparison[metric], rtol=0, atol=1e-12)

        # Diagnose the shared structural-yield component without changing it.
        assert np.allclose(
            summary["unique_formula_yield_pct"], summary["qc_retention_pct"]
            * summary["within_qc_unique_formula_pct"] / 100, rtol=0, atol=1e-12,
        )
        qc = summary["qc_retention_pct"]
        unique = summary["unique_formula_yield_pct"]
        print("QC / unique-formula yield Pearson:", qc.corr(unique))
        print("QC / unique-formula yield Spearman:", qc.rank().corr(unique.rank()))
        without_crystallm = ~summary.index.str.startswith("crystallm_")
        print("Pearson excluding two CrystaLLM cohorts:", qc[without_crystallm].corr(unique[without_crystallm]))
        print("Within-QC unique formula percent range:",
              summary["within_qc_unique_formula_pct"].min(),
              summary["within_qc_unique_formula_pct"].max())
    if args.compare_ablation:
        # Drop only the separate QC objective; retain exactly the saved S1-S3
        # objective values and normalization populations, with no new QC filter.
        variants = {
            f"{scenario}-2D": (label, metrics[1:])
            for scenario, (label, metrics) in variants.items()
        }
        baseline_rankings = pd.read_csv(SAVED / "figure08_scenario_rankings_v2.csv")
        assert set(baseline_rankings.variant) == {"S1", "S2", "S3"}
        assert not baseline_rankings.duplicated(["variant", "analysis_cohort"]).any()
        saved_metrics = pd.read_csv(SAVED / "figure08_scenario_metrics_v2.csv")
        assert set(saved_metrics.variant) == {"S1", "S2", "S3"}
        assert len(saved_metrics) == 90
        assert not saved_metrics.duplicated(["variant", "analysis_cohort", "criterion"]).any()
        for scenario in ("S1", "S2", "S3"):
            rows = baseline_rankings.loc[baseline_rankings.variant.eq(scenario)]
            assert rows.analysis_cohort.tolist() == ORDER
            assert rows.n_weights.eq(20000).all()
            for metric in saved_metrics.loc[saved_metrics.variant.eq(scenario), "criterion"].unique():
                rows = saved_metrics.loc[
                    saved_metrics.variant.eq(scenario) & saved_metrics.criterion.eq(metric)
                ].set_index("analysis_cohort").loc[ORDER]
                assert rows.n_generated_assumed.eq(2000).all()
                assert np.array_equal(rows.n_qc, comparison["n_qc"])
                assert np.allclose(rows.value_pct, comparison[metric], rtol=0, atol=1e-12)
    metric_tables = []
    ranking_tables = []
    pareto_tables = []
    N_WEIGHTS = 20000
    for variant, (variant_label, metrics) in variants.items():
        X = comparison[metrics].to_numpy(dtype=float)
        assert np.isfinite(X).all()
        assert ((X >= 0) & (X <= 100)).all()
        n = len(X)
        dominance = np.zeros((n, n), dtype=bool)
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                dominance[i, j] = (
                    np.all(X[i] >= X[j]) and np.any(X[i] > X[j])
                )
        # Independently check direction, strictness and transitivity.
        expected_dominance = (
            (X[:, None, :] >= X[None, :, :]).all(axis=2)
            & (X[:, None, :] > X[None, :, :]).any(axis=2)
        )
        assert np.array_equal(dominance, expected_dominance)
        assert not np.diag(dominance).any()
        assert not (dominance & dominance.T).any()
        assert not (((dominance.astype(int) @ dominance.astype(int)) > 0) & ~dominance).any()
        is_pareto = ~dominance.any(axis=0)

        minimum = X.min(axis=0)
        maximum = X.max(axis=0)
        span = maximum - minimum
        # A constant objective contributes zero equally to every cohort.
        Z = np.divide(X - minimum, span, out=np.zeros_like(X), where=span > 0)
        assert np.isfinite(Z).all()
        assert ((Z >= 0) & (Z <= 1)).all()
        rng = np.random.default_rng(1984)
        weights = rng.dirichlet(np.ones(len(metrics)), size=N_WEIGHTS)
        assert (weights >= 0).all()
        assert np.allclose(weights.sum(axis=1), 1, rtol=0, atol=1e-12)
        scores = weights @ Z.T
        ranking = np.argsort(-scores, axis=1, kind="stable")
        rank_position = np.empty_like(ranking)
        for row_idx in range(N_WEIGHTS):
            rank_position[row_idx, ranking[row_idx]] = np.arange(1, n + 1)
        assert np.array_equal(
            np.sort(rank_position, axis=1),
            np.broadcast_to(np.arange(1, n + 1), rank_position.shape),
        )
        equal_scores = Z.mean(axis=1)
        equal_order = np.argsort(-equal_scores, kind="stable")
        equal_ranks = np.empty(n, dtype=int)
        equal_ranks[equal_order] = np.arange(1, n + 1)
        rank_probabilities = np.column_stack([
            (rank_position == rank).mean(axis=0) for rank in range(1, n + 1)
        ])
        assert np.allclose(rank_probabilities.sum(axis=1), 1, rtol=0, atol=1e-12)
        assert np.allclose(rank_probabilities.sum(axis=0), 1, rtol=0, atol=1e-12)
        ranks = pd.DataFrame({
            "variant": variant, "variant_label": variant_label,
            "analysis_cohort": ORDER, "label": [LABELS[c] for c in ORDER],
            "n_weights": N_WEIGHTS, "equal_weight_score": equal_scores,
            "equal_weight_rank": equal_ranks,
            "first_place_pct": 100 * (rank_position == 1).mean(axis=0),
            "top3_pct": 100 * (rank_position <= 3).mean(axis=0),
            "top5_pct": 100 * (rank_position <= 5).mean(axis=0),
            "mean_rank": rank_position.mean(axis=0),
            "rank_p05": np.quantile(rank_position, 0.05, axis=0),
            "rank_p95": np.quantile(rank_position, 0.95, axis=0),
        })
        for rank in range(1, n + 1):
            ranks[f"rank_{rank}_pct"] = 100 * rank_probabilities[:, rank - 1]

        if args.compare_scenarios:
            for baseline in ("A", "B", "C"):
                baseline_rows = baseline_rankings.loc[
                    baseline_rankings.variant.eq(baseline)
                ].set_index("analysis_cohort").loc[ORDER]
                for column in ("equal_weight_rank", "first_place_pct", "top3_pct", "top5_pct", "mean_rank"):
                    ranks[f"{column}_delta_vs_{baseline}"] = (
                        ranks[column].to_numpy() - baseline_rows[column].to_numpy()
                    )

        if args.compare_ablation:
            scenario = variant.removesuffix("-2D")
            baseline_rows = baseline_rankings.loc[
                baseline_rankings.variant.eq(scenario)
            ].set_index("analysis_cohort").loc[ORDER]
            ranks["baseline_scenario"] = scenario
            for column in ("equal_weight_rank", "first_place_pct", "top3_pct", "top5_pct", "mean_rank"):
                ranks[f"{column}_delta_vs_scenario"] = (
                    ranks[column].to_numpy() - baseline_rows[column].to_numpy()
                )

        if variant == "A":
            assert np.array_equal(equal_ranks, previous["equal_weight_rank"])
            for column in ("equal_weight_score", "mean_rank", "rank_p05", "rank_p95"):
                assert np.allclose(ranks[column], previous[column], rtol=0, atol=1e-12)
            assert np.array_equal(is_pareto, previous["pareto_efficient"])
            assert np.array_equal(dominance.sum(axis=0), previous["n_dominators"])
            saved_dominance = pd.read_csv(ROOT / "fig08_dominance_matrix.csv", index_col=0)
            assert np.array_equal(dominance, saved_dominance.loc[ORDER, ORDER])
            saved_distribution = pd.read_csv(ROOT / "fig08_rank_distribution.csv", index_col=0)
            assert np.allclose(
                rank_probabilities, saved_distribution.loc[ORDER].to_numpy(), rtol=0, atol=1e-12,
            )
            saved_ranks = pd.read_csv(ROOT / "fig08_ranking_summary.csv").set_index("analysis_cohort")
            for column in ("first_place_pct", "top3_pct", "top5_pct", "mean_rank"):
                assert np.allclose(ranks[column], saved_ranks.loc[ORDER, column], rtol=0, atol=1e-12)

        for j, metric in enumerate(metrics):
            metric_tables.append(pd.DataFrame({
                "variant": variant, "variant_label": variant_label,
                "analysis_cohort": ORDER, "label": [LABELS[c] for c in ORDER],
                "n_qc": comparison["n_qc"].to_numpy(),
                "n_generated_assumed": GENERATED_PER_COHORT,
                "criterion": metric, "value_pct": X[:, j],
                "normalized_score": Z[:, j], "constant_criterion": span[j] == 0,
            }))
            if args.compare_ablation:
                metric_tables[-1]["qc_retention_pct_reference"] = comparison["qc_retention_pct"].to_numpy()
        ranking_tables.append(ranks)
        for i, cohort in enumerate(ORDER):
            pareto_tables.append(pd.DataFrame({
                "variant": variant, "variant_label": variant_label,
                "analysis_cohort": cohort, "label": LABELS[cohort],
                "pareto_efficient": is_pareto[i],
                "n_dominators": dominance[:, i].sum(),
                "compared_cohort": ORDER, "dominates": dominance[i],
            }))
        print(f"\n{variant} - {variant_label}")
        print(ranks[["label", "equal_weight_rank", "first_place_pct",
                     "top3_pct", "top5_pct", "mean_rank"]].to_string(index=False))
        print("Pareto-efficient:", [LABELS[c] for c, efficient in zip(ORDER, is_pareto) if efficient])

    pd.concat(metric_tables, ignore_index=True).to_csv(
        OUTPUT / ("figure08_ablation_metrics_v2.csv" if args.compare_ablation
                  else "figure08_scenario_metrics_v2.csv" if args.compare_scenarios
                  else "figure08_criteria_metrics_v2.csv"), index=False,
    )
    pd.concat(ranking_tables, ignore_index=True).to_csv(
        OUTPUT / ("figure08_ablation_rankings_v2.csv" if args.compare_ablation
                  else "figure08_scenario_rankings_v2.csv" if args.compare_scenarios
                  else "figure08_criteria_rankings_v2.csv"), index=False,
    )
    pd.concat(pareto_tables, ignore_index=True).to_csv(
        OUTPUT / ("figure08_ablation_pareto_v2.csv" if args.compare_ablation
                  else "figure08_scenario_pareto_v2.csv" if args.compare_scenarios
                  else "figure08_criteria_pareto_v2.csv"), index=False,
    )
    print("FIGURE08 ABLATION COMPARISON: PASSED" if args.compare_ablation
          else "FIGURE08 SCENARIO COMPARISON: PASSED" if args.compare_scenarios
          else "FIGURE08 CRITERIA COMPARISON: PASSED")
    raise SystemExit(0)

# -----------------------------
# 4. Pareto dominance
# -----------------------------
X = summary[METRICS].to_numpy(dtype=float)
n = len(X)

# dominance[i, j] = i is at least as good in all
# metrics and strictly better in at least one.
dominance = np.zeros((n, n), dtype=bool)

for i in range(n):
    for j in range(n):
        if i == j:
            continue
        dominance[i, j] = (
            np.all(X[i] >= X[j]) and
            np.any(X[i] > X[j])
        )

is_pareto = ~dominance.any(axis=0)
summary["pareto_efficient"] = is_pareto
summary["n_dominators"] = dominance.sum(axis=0)

# -----------------------------
# 5. Weight-sensitivity analysis
# -----------------------------
minimum = X.min(axis=0)
maximum = X.max(axis=0)
span = maximum - minimum
assert (span > 0).all()

Z = (X - minimum) / span

rng = np.random.default_rng(1984)
N_WEIGHTS = 20000
weights = rng.dirichlet(
    np.ones(len(METRICS)),
    size=N_WEIGHTS,
)

scores = weights @ Z.T

# Stable alphabetical/cohort-order tie rule.
ranking = np.argsort(-scores, axis=1, kind="stable")
rank_position = np.empty_like(ranking)
for row_idx in range(N_WEIGHTS):
    rank_position[row_idx, ranking[row_idx]] = np.arange(1, n + 1)

summary["first_place_fraction"] = (
    (rank_position == 1).mean(axis=0)
)
summary["mean_rank"] = rank_position.mean(axis=0)
summary["rank_p05"] = np.quantile(
    rank_position, 0.05, axis=0
)
summary["rank_p95"] = np.quantile(
    rank_position, 0.95, axis=0
)

# Equal-weight result for transparent comparison.
equal_scores = Z.mean(axis=1)
equal_order = np.argsort(-equal_scores, kind="stable")
equal_ranks = np.empty(n, dtype=int)
equal_ranks[equal_order] = np.arange(1, n + 1)
summary["equal_weight_score"] = equal_scores
summary["equal_weight_rank"] = equal_ranks

summary.to_csv(
    OUTPUT / "figure08_metric_matrix.csv"
)

pd.DataFrame(
    dominance.astype(int),
    index=ORDER,
    columns=ORDER,
).to_csv(OUTPUT / "figure08_dominance_matrix.csv")

pd.DataFrame({
    "weight_qc": weights[:, 0],
    "weight_unique": weights[:, 1],
    "weight_3d": weights[:, 2],
    "winner": [ORDER[i] for i in ranking[:, 0]],
}).to_csv(
    OUTPUT / "figure08_weight_sensitivity.csv",
    index=False,
)

# -----------------------------
# 6. Plot
# -----------------------------
apply_analysis_v2_publication_style()

COHORT_COLORS = {
    **ANALYSIS_V2_MAGNETIC_COHORT_COLORS,
    "crystalformer_finetuned": "#B75B34",
    "crystallm_finetuned": "#742E36",
}

assert all(cohort in COHORT_COLORS for cohort in ORDER)


METRIC_CMAP = LinearSegmentedColormap.from_list(
    "maggenbench_metric",
    ["#F7F8F6", "#C9DCE2", "#8BAEBA", "#4F8296", "#24526C"],
)

RANK_CMAP = LinearSegmentedColormap.from_list(
    "maggenbench_rank",
    ["#F7F8F6", "#D9E6EB", "#91B7C5", "#447B95", "#173F61"],
)

fig, axes = plt.subplots(
    2, 2, figsize=(15.5, 11.5),
    constrained_layout=True
)
ax_a, ax_b = axes[0]
ax_c, ax_d = axes[1]

labels = summary["label"].tolist()

# A: metric matrix
im = ax_a.imshow(
    Z, aspect="auto", vmin=0, vmax=1, cmap=METRIC_CMAP
)
ax_a.set_xticks(range(3), [
    "QC retention",
    "Unique formula yield",
    "3d-containing yield",
], rotation=20, ha="right")
ax_a.set_yticks(range(n), labels)
for i in range(n):
    for j in range(3):
        ax_a.text(
            j, i, f"{X[i, j]:.2f}%",
            ha="center", va="center",
            fontsize=8,
            color="white" if Z[i, j] > 0.70 else "#173247",
        )
ax_a.set_title("A  Benchmark metrics")
fig.colorbar(im, ax=ax_a, shrink=0.75, label="Normalized score")

SHORT_LABELS = [
    "MG-B", "MG-FT",
    "CD-B", "CD-FT",
    "CF-B", "CF-FT",
    "CL-B", "CL-FT",
    "JE-B", "JE-R",
]

# B: Structural retention versus formula exploration
for i, cohort in enumerate(ORDER):
    if cohort.endswith("_finetuned"):
        marker = "s"
    elif cohort == "crysjepa_refined":
        marker = "D"
    else:
        marker = "o"

    ax_b.scatter(
        X[i, 0],
        X[i, 1],
        s=55 + 2.0 * X[i, 2],
        marker=marker,
        color=COHORT_COLORS[cohort],
        edgecolors="#172B3A" if is_pareto[i] else "#FFFFFF",
        linewidths=1.7 if is_pareto[i] else 0.8,
        alpha=0.95,
        zorder=3,
    )

    ax_b.annotate(
        SHORT_LABELS[i],
        (X[i, 0], X[i, 1]),
        xytext=(6, 6),
        textcoords="offset points",
        fontsize=9,
        color="#253746",
    )

ax_b.set_xlabel("QC retention (%)")
ax_b.set_ylabel("Unique-formula yield (%)")
ax_b.set_title("B  Structural yield vs diversity")
ax_b.grid(alpha=0.15, linewidth=0.5)
ax_b.set_axisbelow(True)

# C: Full distribution of ranks across weight combinations
rank_probabilities = np.column_stack([
    (rank_position == rank).mean(axis=0)
    for rank in range(1, n + 1)
])

rank_table = pd.DataFrame(
    rank_probabilities,
    index=ORDER,
    columns=[f"rank_{i}" for i in range(1, n + 1)],
)
rank_table.to_csv(
    OUTPUT / "figure08_rank_distribution.csv"
)

rank_image = ax_c.imshow(
    100 * rank_probabilities,
    aspect="auto",
    norm=PowerNorm(gamma=0.55, vmin=0, vmax=100),
    cmap=RANK_CMAP,
)
ax_c.set_yticks(range(n), labels)
ax_c.set_xticks(range(n), range(1, n + 1))
ax_c.set_xlabel("Rank")
ax_c.set_ylabel("Generator cohort")
ax_c.set_title("C  Rank stability")
fig.colorbar(
    rank_image, ax=ax_c,
    shrink=0.8,
    label="Weight combinations (%)",
)

# D: Top-5 frequency across sampled objective weights
top3_frequency = (rank_position <= 3).mean(axis=0)
top5_frequency = (rank_position <= 5).mean(axis=0)

summary["top3_frequency"] = top3_frequency
summary["top5_frequency"] = top5_frequency

# Preserve first-place, Top-3 and Top-5 statistics.
pd.DataFrame({
    "analysis_cohort": ORDER,
    "label": labels,
    "first_place_pct":
        100 * summary["first_place_fraction"].to_numpy(),
    "top3_pct": 100 * top3_frequency,
    "top5_pct": 100 * top5_frequency,
    "mean_rank": summary["mean_rank"].to_numpy(),
}).to_csv(
    OUTPUT / "figure08_ranking_summary.csv",
    index=False,
)

top5_order = np.argsort(-top5_frequency, kind="stable")
top5_pct = 100 * top5_frequency

bars = ax_d.barh(
    np.array(labels)[top5_order],
    top5_pct[top5_order],
    color=[COHORT_COLORS[ORDER[i]] for i in top5_order],
    edgecolor="white",
    linewidth=0.7,
    height=0.70,
)

ax_d.invert_yaxis()
ax_d.set_xlim(0, 109)
ax_d.set_xticks([0, 20, 40, 60, 80, 100])
ax_d.set_xlabel("Top-5 frequency (%)")
ax_d.set_title("D  Top-5 frequency")
ax_d.grid(axis="x", alpha=0.15, linewidth=0.5)
ax_d.set_axisbelow(True)

for bar, i in zip(bars, top5_order):
    ax_d.text(
        top5_pct[i] + 1.2,
        bar.get_y() + bar.get_height() / 2,
        f"{top5_pct[i]:.1f}%",
        va="center",
        ha="left",
        fontsize=9,
        color="#253746",
    )

# Number labels in panel B follow the row order in panel A.
# The same order is listed explicitly in the exported metric matrix.

for extension, kwargs in (
    ("pdf", {}),
    ("png", {"dpi": 200}),
    ("svg", {}),
):
    fig.savefig(
        OUTPUT / f"figure08_multiobjective.{extension}",
        bbox_inches="tight",
        **kwargs,
    )
plt.close(fig)

print("\n=== METRIC MATRIX ===")
print(summary[
    ["label", "n", "qc_retention_pct",
     "unique_formula_yield_pct",
     "3d_containing_yield_pct",
     "pareto_efficient", "equal_weight_rank",
     "first_place_fraction"]
].to_string(float_format=lambda v: f"{v:.3f}"))

print("\nPareto-efficient cohorts:")
print(summary.loc[summary.pareto_efficient, "label"].tolist())

print("\nOUTPUT:", OUTPUT)
print("FIGURE08 PRELIMINARY: PASSED")
print("IMPORTANT: verify generated budget = 2000 for each cohort.")
print("IMPORTANT: magnetic-reference and DFT criteria not included.")
