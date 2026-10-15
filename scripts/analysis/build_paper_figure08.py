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

ROOT = Path("paper/tables/figure_sources")
MASTER = Path("tables/10_analysis_v2_magnetic/analysis_v2_magnetic.csv")
OUTPUT = Path("reproduced/figure8")
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

# D: First-place frequency
order = np.argsort(
    -summary.first_place_fraction.to_numpy(),
    kind="stable",
)

prob = 100 * summary.first_place_fraction.to_numpy()

bars = ax_d.barh(
    np.array(labels)[order],
    prob[order],
    color=[COHORT_COLORS[ORDER[i]] for i in order],
    edgecolor="#FFFFFF",
    linewidth=0.7,
    height=0.72,
)

ax_d.invert_yaxis()
ax_d.set_xlabel("First-place frequency (%)")
ax_d.set_title("D  First-place frequency")
ax_d.set_xlim(0, 60)
ax_d.grid(axis="x", alpha=0.15, linewidth=0.5)
ax_d.set_axisbelow(True)

for bar, i in zip(bars, order):
    if prob[i] > 0:
        ax_d.text(
            prob[i] + 1,
            bar.get_y() + bar.get_height() / 2,
            f"{prob[i]:.2f}%",
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
