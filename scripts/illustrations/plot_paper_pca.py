from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from mvpipeline.analysis.typography import prepare_figure_typography

from mvpipeline.analysis.projections_v2 import (
    COMPOSITION_SYMMETRY_PCA_FEATURES,
    MAGNETIC_GEOMETRY_PCA_FEATURES,
)

ROOT = Path("reproduced/pca_publication")
ROOT.mkdir(parents=True, exist_ok=True)

OLD = Path("tables/10_analysis_v2_magnetic/analysis_v2_magnetic.csv")
FT_ROOT = Path("tables/figure_sources")

ORDER = [
    "mattergen_baseline", "mattergen_finetuned",
    "concdvae_baseline", "concdvae_finetuned",
    "crystalformer_baseline", "crystalformer_finetuned",
    "crystallm_baseline", "crystallm_finetuned",
    "crysjepa_base", "crysjepa_refined",
]
LABELS = [
    "MatterGen Base", "MatterGen FT",
    "Con-CDVAE Base", "Con-CDVAE FT",
    "CrystalFormer Base", "CrystalFormer FT",
    "CrystaLLM Base", "CrystaLLM FT",
    "Crys-JEPA Base", "Crys-JEPA Refined",
]
PAIRS = [
    ("mattergen_baseline", "mattergen_finetuned", "MatterGen"),
    ("concdvae_baseline", "concdvae_finetuned", "Con-CDVAE"),
    ("crystalformer_baseline", "crystalformer_finetuned", "CrystalFormer"),
    ("crystallm_baseline", "crystallm_finetuned", "CrystaLLM"),
    ("crysjepa_base", "crysjepa_refined", "Crys-JEPA"),
]

FEATURES = list(dict.fromkeys(
    COMPOSITION_SYMMETRY_PCA_FEATURES +
    MAGNETIC_GEOMETRY_PCA_FEATURES
))
KEEP = ["analysis_cohort", "sample_uid"] + FEATURES

frames = [pd.read_csv(OLD, usecols=lambda x: x in KEEP)]

for name in ("crystalformer_finetuned", "crystallm_finetuned"):
    path = FT_ROOT / f"{name}_descriptors.csv"
    frames.append(pd.read_csv(path, usecols=lambda x: x in KEEP))

df = pd.concat(frames, ignore_index=True)
assert len(df) == 12281, len(df)
assert set(df.analysis_cohort) == set(ORDER)
assert not df.duplicated(["analysis_cohort", "sample_uid"]).any()

counts = df.groupby("analysis_cohort").size()
print("=== INPUT COUNTS ===")
print(counts.reindex(ORDER).to_string())

results = {}
report = {"input_rows": len(df), "spaces": {}}

for name, feature_names in (
    ("composition", COMPOSITION_SYMMETRY_PCA_FEATURES),
    ("magnetic_geometry", MAGNETIC_GEOMETRY_PCA_FEATURES),
):
    columns = list(feature_names)
    values = df[columns].apply(pd.to_numeric, errors="coerce")
    valid = np.isfinite(values.to_numpy(dtype=float)).all(axis=1)

    included = df.loc[valid, ["analysis_cohort", "sample_uid"]].copy()
    X = values.loc[valid].to_numpy(dtype=float)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    if not np.isfinite(X_scaled).all():
        raise RuntimeError(f"{name}: invalid scaled values")

    pca = PCA(n_components=2, svd_solver="full")
    xy = pca.fit_transform(X_scaled)

    included["PC1"] = xy[:, 0]
    included["PC2"] = xy[:, 1]

    if set(included.analysis_cohort) != set(ORDER):
        raise RuntimeError(f"{name}: a cohort has no eligible rows")

    loadings = pd.DataFrame(
        pca.components_.T,
        index=columns,
        columns=["PC1", "PC2"],
    )

    included.to_csv(ROOT / f"{name}_scores.csv", index=False)
    loadings.to_csv(ROOT / f"{name}_loadings.csv")

    excluded = int((~valid).sum())
    report["spaces"][name] = {
        "included": int(valid.sum()),
        "excluded": excluded,
        "explained_variance_ratio": [
            float(x) for x in pca.explained_variance_ratio_
        ],
        "cohort_counts": {
            key: int(value)
            for key, value in included.groupby("analysis_cohort").size().items()
        },
    }
    results[name] = (included, loadings, pca)

    print(f"\n{name}: included={valid.sum()}, excluded={excluded}")
    print("Explained variance:", pca.explained_variance_ratio_)

colors = dict(zip(ORDER, plt.get_cmap("tab10").colors))

fig = plt.figure(figsize=(16, 11), layout="constrained")
gs = fig.add_gridspec(3, 10, height_ratios=[1.2, 0.85, 0.85])

for position, (name, title) in enumerate((
    ("composition", "Composition and symmetry"),
    ("magnetic_geometry", "Magnetic-sublattice geometry"),
)):
    ax = fig.add_subplot(gs[0, position*5:(position+1)*5])
    scores, _, pca = results[name]
    for cohort, label in zip(ORDER, LABELS):
        points = scores[scores.analysis_cohort == cohort]
        ax.scatter(
            points.PC1, points.PC2,
            s=2, alpha=0.24,
            color=colors[cohort], label=label,
            rasterized=True,
        )
    ax.set_title(title)
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")
    if position == 0:
        ax.legend(fontsize=7, ncol=2, loc="best", markerscale=3)

scores = results["composition"][0]
centroids = scores.groupby("analysis_cohort")[["PC1", "PC2"]].mean()

for i, (base, adapted, title) in enumerate(PAIRS):
    row = 1 + (i // 3)
    col = (i % 3) * 3
    if i == 4:
        col = 3
    ax = fig.add_subplot(gs[row, col:col+3])
    ax.scatter(
        scores.PC1, scores.PC2, s=0.6,
        alpha=0.025, color="gray", rasterized=True,
    )
    p = centroids.loc[base]
    q = centroids.loc[adapted]
    ax.scatter([p.PC1, q.PC1], [p.PC2, q.PC2],
               c=[colors[base], colors[adapted]], s=55, zorder=3)
    ax.annotate(
        "", xy=(q.PC1, q.PC2), xytext=(p.PC1, p.PC2),
        arrowprops=dict(arrowstyle="->", lw=1.7, color="black"),
    )
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")

fig.suptitle("Descriptor-space PCA and cohort-centroid shifts", fontsize=15)
prepare_figure_typography(fig)
fig.savefig(ROOT / "supp02_descriptor_space.pdf", bbox_inches="tight")
fig.savefig(ROOT / "supp02_descriptor_space.png", dpi=180, bbox_inches="tight")
plt.close(fig)

fig, axes = plt.subplots(2, 2, figsize=(14, 11), layout="constrained")
for row, (name, title) in enumerate((
    ("composition", "Composition and symmetry"),
    ("magnetic_geometry", "Magnetic-sublattice geometry"),
)):
    _, loadings, _ = results[name]
    for col, pc in enumerate(("PC1", "PC2")):
        ax = axes[row, col]
        series = loadings[pc]
        top = series.reindex(series.abs().nlargest(8).index).sort_values()
        ax.barh(top.index, top.values)
        ax.axvline(0, lw=0.8, color="gray")
        ax.set_title(f"{title}: {pc}")
        ax.set_xlabel("PCA component coefficient")
        ax.tick_params(axis="y", labelsize=8)

prepare_figure_typography(fig)
fig.savefig(ROOT / "supp01_pca_loadings.pdf", bbox_inches="tight")
fig.savefig(ROOT / "supp01_pca_loadings.png", dpi=180, bbox_inches="tight")
plt.close(fig)

(ROOT / "pca_audit.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print("\nPCA OUTPUTS:")
for p in sorted(ROOT.glob("*")):
    print(p)
print("PCA GENERATION: PASSED")
