from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .plotting_v2 import (
    ANALYSIS_V2_DARK_TEXT, ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    ANALYSIS_V2_MAGNETIC_COHORT_COLORS, FigureExportPaths,
    apply_analysis_v2_publication_style, save_analysis_v2_figure_bundle,
)
from .validation_figures_v2 import (
    MODEL_ORDER, REJECTION_REASON_LABELS, REJECTION_REASON_ORDER,
    VALIDATION_INPUT, build_validation_tables, read_ragged_validation_records,
)

FIGURE_BASENAME = "manuscript_figure2_structural_overview_v2_preview"
CRYSJEPA_BASE_VALIDATION_INPUT = Path("tables/03_features/crysjepa_base_with_classes.csv")
BASELINE_DISPLAY_ORDER = (*MODEL_ORDER, "Crys-JEPA")
BASE_COHORTS = (
    "mattergen_baseline", "concdvae_baseline",
    "crystalformer_baseline", "crystallm_baseline",
)
FT_COHORTS = (
    "mattergen_finetuned", "concdvae_finetuned",
    "crystalformer_finetuned", "crystallm_finetuned",
)
JEPA_COHORTS = ("crysjepa_base", "crysjepa_refined")
QC_COHORT_ORDER = (*BASE_COHORTS, *FT_COHORTS, *JEPA_COHORTS)
QC_INPUTS = {
    "mattergen_finetuned": Path("tables/03_features/phase5b_mattergen_finetuned_with_classes.csv"),
    "concdvae_finetuned": Path("tables/03_features/phase5b_concdvae_finetuned_with_classes.csv"),
    "crystalformer_finetuned": Path("outputs/crystalformer_finetuned/all_structures.csv"),
    "crystallm_finetuned": Path("outputs/crystallm_finetuned/all_structures.csv"),
    "crysjepa_base": CRYSJEPA_BASE_VALIDATION_INPUT,
    "crysjepa_refined": Path("tables/03_features/crysjepa_refined_with_classes.csv"),
}
QC_COLORS = {
    **ANALYSIS_V2_MAGNETIC_COHORT_COLORS,
    "crystalformer_finetuned": "#A95035",
    "crystallm_finetuned": "#833E38",
}
# Verification targets only; plotted values always come from QC status records.
EXPECTED_RETAINED = dict(zip(QC_COHORT_ORDER, (
    1657, 1864, 1083, 98, 1376, 1299, 1380, 217, 1764, 1543,
)))


@dataclass(frozen=True)
class ManuscriptFigure2Report:
    qc_summary: object
    rejection_summary: object
    missing_inputs: tuple[Path, ...]
    figure_paths: FigureExportPaths | None


def _read_qc_table(path: Path):
    import pandas as pd

    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or ())
        identity = next((key for key in ("sample_uid", "structure_id") if key in columns), None)
        if "status" not in columns or identity is None:
            raise RuntimeError(f"{path}: requires status and sample_uid or structure_id")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise RuntimeError(f"{path}: malformed CSV row width")
    df = pd.DataFrame(rows)
    if len(df) != 2000:
        raise RuntimeError(
            f"{path}: expected 2000 harmonized benchmark structures, found {len(df)}; "
            "supply the benchmark QC table, not raw generation (possibly 2016). "
            "Do not truncate or rescale raw QC counts."
        )
    ids = df[identity].str.strip()
    if ids.eq("").any() or ids.duplicated().any():
        raise RuntimeError(f"{path}: empty or repeated structure identifiers")
    df["status"] = df["status"].str.strip().str.lower()
    if not set(df["status"]).issubset({"validated", "rejected"}):
        raise RuntimeError(f"{path}: unknown QC status")
    if "rejection_reason" in df:
        df["rejection_reason"] = df["rejection_reason"].str.strip()
        if df.loc[df["status"].eq("validated"), "rejection_reason"].ne("").any():
            raise RuntimeError(f"{path}: validated structure has a rejection reason")
    return df


def build_structural_qc_tables(
    validation_input_csv: str | Path = VALIDATION_INPUT,
    *, qc_inputs: dict[str, Path] | None = None,
):
    import pandas as pd

    inputs = {**QC_INPUTS, **(qc_inputs or {})}
    unknown = set(inputs).difference(QC_INPUTS)
    if unknown:
        raise ValueError(f"Unknown QC cohorts: {sorted(unknown)}")
    baseline, rejection = build_validation_tables(
        read_ragged_validation_records(validation_input_csv)
    )
    rows = []
    for model, cohort in zip(MODEL_ORDER, BASE_COHORTS):
        rows.append({
            "cohort": cohort, **baseline.loc[model].to_dict(),
            "source": str(validation_input_csv),
        })
    missing = []
    for cohort in (*FT_COHORTS, *JEPA_COHORTS):
        path = Path(inputs[cohort])
        if not path.is_file():
            missing.append(path)
            continue
        df = _read_qc_table(path)
        retained = int(df["status"].eq("validated").sum())
        rejected = int(df["status"].eq("rejected").sum())
        rows.append({
            "cohort": cohort, "n_total": len(df), "n_validated": retained,
            "n_rejected": rejected, "validated_percent": 100 * retained / len(df),
            "rejected_percent": 100 * rejected / len(df), "source": str(path),
        })
        if cohort == "crysjepa_base":
            if "rejection_reason" not in df:
                raise RuntimeError(f"{path}: missing registered primary rejection reasons")
            reasons = df.loc[df["status"].eq("rejected"), "rejection_reason"]
            if not set(reasons).issubset(REJECTION_REASON_ORDER):
                raise RuntimeError(f"{path}: missing or unknown primary rejection reason")
            rejection.loc["Crys-JEPA"] = [
                100 * int(reasons.eq(reason).sum()) / rejected if rejected else 0.0
                for reason in REJECTION_REASON_ORDER
            ]
    summary = pd.DataFrame(rows).set_index("cohort")
    summary = summary.reindex([key for key in QC_COHORT_ORDER if key in summary.index])
    for column in ("n_total", "n_validated", "n_rejected"):
        summary[column] = summary[column].astype(int)
    summary["expected_retained"] = [EXPECTED_RETAINED[key] for key in summary.index]
    summary["matches_expected"] = summary["n_validated"].eq(summary["expected_retained"])
    return summary, rejection.reindex(BASELINE_DISPLAY_ORDER), tuple(missing)


def _panel_label(ax, label):
    ax.text(-0.075, 1.10, label, transform=ax.transAxes, fontsize=12,
            fontweight="bold", va="top", ha="left")


def _plot_retention(ax, summary, cohorts, labels, title, panel):
    for index, cohort in enumerate(cohorts):
        row = summary.loc[cohort]
        percent = float(row["validated_percent"])
        ax.barh(index, 100, color="#EEEAE2", height=0.58)
        ax.barh(index, percent, color=QC_COLORS[cohort], height=0.58,
                edgecolor=ANALYSIS_V2_DARK_TEXT, linewidth=0.5)
        # High-retention labels fit inside the bar; small bars use outside labels.
        inside = percent >= 55
        ax.text(percent - 2 if inside else percent + 2, index,
                f"{int(row['n_validated']):,} ({percent:.2f}%)",
                ha="right" if inside else "left", va="center", fontsize=9,
                color=ANALYSIS_V2_DARK_TEXT
                if not inside or cohort in (*BASE_COHORTS, "crysjepa_base") else "white")
    ax.set_yticks(range(len(labels)), labels)
    ax.set_ylim(len(labels) - 0.4, -0.6)
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Structural QC retention (%)")
    ax.set_title(title, pad=12)
    ax.grid(axis="x", color="#D5D5D5", linewidth=0.45, alpha=0.5)
    ax.set_axisbelow(True)
    _panel_label(ax, panel)


def _plot_rejection_profile(ax, rejection_summary, qc_summary):
    from matplotlib.colors import LinearSegmentedColormap

    cmap = LinearSegmentedColormap.from_list("qc_rejection", ["#FFFFFF", "#F0E2C5", "#829DA6", "#304862"])
    values = rejection_summary.to_numpy(dtype=float)
    image = ax.imshow(values, aspect="auto", vmin=0, vmax=100, cmap=cmap)
    ax.set_xticks(range(len(REJECTION_REASON_ORDER)),
                  [REJECTION_REASON_LABELS[key] for key in REJECTION_REASON_ORDER])
    ax.set_yticks(range(len(BASELINE_DISPLAY_ORDER)), [
        f"{model} (n={int(qc_summary.loc[cohort, 'n_rejected']):,})"
        for model, cohort in zip(BASELINE_DISPLAY_ORDER, (*BASE_COHORTS, "crysjepa_base"))
    ])
    ax.set_title("Base: registered primary rejection reasons", pad=12)
    for row in range(values.shape[0]):
        for column in range(values.shape[1]):
            value = values[row, column]
            ax.text(column, row, f"{value:.1f}", ha="center", va="center",
                    fontsize=8, color="white" if value >= 60 else ANALYSIS_V2_DARK_TEXT)
    cbar = ax.figure.colorbar(image, ax=ax, pad=0.02, fraction=0.035)
    cbar.set_label("Share of rejected structures (%)")
    _panel_label(ax, "D")


def save_manuscript_figure2(qc_summary, rejection_summary, *,
                            output_dir=ANALYSIS_V2_FIGURE_OUTPUT_DIR):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if tuple(qc_summary.index) != QC_COHORT_ORDER or rejection_summary.isna().any().any():
        raise RuntimeError("Figure 2 requires all ten QC cohorts and five baseline rejection profiles")
    apply_analysis_v2_publication_style()
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 8.2), constrained_layout=True)
    _plot_retention(axes[0, 0], qc_summary, BASE_COHORTS, MODEL_ORDER, "Base", "A")
    _plot_retention(axes[0, 1], qc_summary, FT_COHORTS, MODEL_ORDER, "Fine-tuned (FT)", "B")
    _plot_retention(axes[1, 0], qc_summary, JEPA_COHORTS,
                    ("Crys-JEPA Base", "Crys-JEPA Ref."), "Crys-JEPA", "C")
    _plot_rejection_profile(axes[1, 1], rejection_summary, qc_summary)
    paths = save_analysis_v2_figure_bundle(fig, output_dir, FIGURE_BASENAME)
    plt.close(fig)
    return paths


def run_manuscript_figure2(
    validation_input_csv: str | Path = VALIDATION_INPUT,
    figure_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    *, qc_inputs: dict[str, Path] | None = None, audit_only: bool = False,
    check_expected: bool = False,
) -> ManuscriptFigure2Report:
    summary, rejection, missing = build_structural_qc_tables(
        validation_input_csv, qc_inputs=qc_inputs,
    )
    root = Path(figure_dir)
    root.mkdir(parents=True, exist_ok=True)
    summary.to_csv(root / "figure2_structural_qc_audit.csv")
    rejection.to_csv(root / "figure2_primary_rejection_percent.csv")
    mismatches = summary.loc[~summary["matches_expected"]]
    if check_expected and not mismatches.empty:
        raise RuntimeError("QC retained counts differ from verification targets:\n" + mismatches.to_string())
    if missing and not audit_only:
        raise FileNotFoundError("Missing structural QC inputs:\n" + "\n".join(map(str, missing)))
    paths = None if audit_only else save_manuscript_figure2(summary, rejection, output_dir=root)
    return ManuscriptFigure2Report(summary, rejection, missing, paths)
