from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from .plotting_v2 import (
    ANALYSIS_V2_DARK_TEXT,
    ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    ANALYSIS_V2_AUDIT_OUTPUT_DIR,
    ANALYSIS_V2_MAGNETIC_COHORT_COLORS,
    ANALYSIS_V2_OVERVIEW_CREAM,
    FigureExportPaths,
    apply_analysis_v2_publication_style,
    save_analysis_v2_figure_bundle,
)


VALIDATION_INPUT = Path(
    "tables/02_validation/master_structures_with_validation_status.csv"
)

EXPECTED_TOTAL_ROWS = 8000
EXPECTED_ROWS_PER_MODEL = 2000
EXPECTED_STATUS_SOURCE = "all_structures_row_order"

MODEL_ORDER = (
    "MatterGen",
    "Con-CDVAE",
    "CrystalFormer",
    "CrystaLLM",
)

MODEL_COLORS = {
    "MatterGen": ANALYSIS_V2_MAGNETIC_COHORT_COLORS["mattergen_baseline"],
    "Con-CDVAE": ANALYSIS_V2_MAGNETIC_COHORT_COLORS["concdvae_baseline"],
    "CrystalFormer": ANALYSIS_V2_MAGNETIC_COHORT_COLORS[
        "crystalformer_baseline"
    ],
    "CrystaLLM": ANALYSIS_V2_MAGNETIC_COHORT_COLORS["crystallm_baseline"],
}

REJECTION_REASON_ORDER = (
    "duplicate",
    "charge_imbalance",
    "cif_parse_error",
    "physically_impossible_distance",
    "unrealistic_density",
)

REJECTION_REASON_LABELS = {
    "duplicate": "Duplicate",
    "charge_imbalance": "Charge\nimbalance",
    "cif_parse_error": "CIF parse\nerror",
    "physically_impossible_distance": "Impossible\ndistance",
    "unrealistic_density": "Unrealistic\ndensity",
}

FIGURE_BASENAME = "13_structural_validation_rejection_v2"
MODEL_SUMMARY_CSV = "structural_validation_summary_v2.csv"
REJECTION_SUMMARY_CSV = "structural_rejection_profile_v2.csv"


@dataclass(frozen=True)
class ValidationRecord:
    model_name: str
    model_short: str
    status: str
    status_source: str
    rejection_reason: str
    row_width: int


@dataclass(frozen=True)
class ValidationFigureReport:
    input_csv: Path
    n_rows: int
    model_summary: object
    rejection_summary: object
    model_summary_csv: Path
    rejection_summary_csv: Path
    figure_paths: FigureExportPaths


def read_ragged_validation_records(
    input_csv: str | Path = VALIDATION_INPUT,
) -> list[ValidationRecord]:
    path = Path(input_csv)
    if not path.is_file():
        raise FileNotFoundError(path)

    records: list[ValidationRecord] = []

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)

        if len(header) < 6:
            raise RuntimeError("Validation CSV header is unexpectedly short")

        if header[1:3] != ["model_name", "model_short"]:
            raise RuntimeError(
                "Validation CSV does not have expected model columns"
            )

        if header[-3:] != [
            "status",
            "status_source",
            "rejection_reason",
        ]:
            raise RuntimeError(
                "Validation CSV does not have expected trailing status columns"
            )

        for row_number, row in enumerate(reader, start=2):
            if len(row) < 6:
                raise RuntimeError(
                    f"Validation CSV row {row_number} is too short: "
                    f"{len(row)} fields"
                )

            records.append(
                ValidationRecord(
                    model_name=row[1].strip(),
                    model_short=row[2].strip(),
                    status=row[-3].strip(),
                    status_source=row[-2].strip(),
                    rejection_reason=row[-1].strip(),
                    row_width=len(row),
                )
            )

    return records


def build_validation_tables(
    records: list[ValidationRecord],
    *,
    expected_total_rows: int | None = EXPECTED_TOTAL_ROWS,
    expected_rows_per_model: int | None = EXPECTED_ROWS_PER_MODEL,
):
    import numpy as np
    import pandas as pd

    if expected_total_rows is not None and len(records) != expected_total_rows:
        raise RuntimeError(
            f"Expected {expected_total_rows} validation rows, "
            f"found {len(records)}"
        )

    unknown_models = sorted(
        {record.model_name for record in records}.difference(MODEL_ORDER)
    )
    if unknown_models:
        raise RuntimeError(
            f"Unexpected models in validation artifact: {unknown_models}"
        )

    status_values = {record.status for record in records}
    if status_values != {"validated", "rejected"}:
        raise RuntimeError(
            f"Unexpected validation status values: {sorted(status_values)}"
        )

    source_values = {record.status_source for record in records}
    if source_values != {EXPECTED_STATUS_SOURCE}:
        raise RuntimeError(
            f"Unexpected validation status sources: {sorted(source_values)}"
        )

    model_counts = Counter(record.model_name for record in records)

    if expected_rows_per_model is not None:
        bad_counts = {
            model: model_counts.get(model, 0)
            for model in MODEL_ORDER
            if model_counts.get(model, 0) != expected_rows_per_model
        }
        if bad_counts:
            raise RuntimeError(
                f"Unexpected per-model validation counts: {bad_counts}"
            )

    status_by_model = defaultdict(Counter)
    reason_by_model = defaultdict(Counter)

    for record in records:
        status_by_model[record.model_name][record.status] += 1

        if record.status == "validated":
            if record.rejection_reason:
                raise RuntimeError(
                    "Validated structure has non-empty rejection reason"
                )
        else:
            if not record.rejection_reason:
                raise RuntimeError(
                    "Rejected structure has empty rejection reason"
                )
            if record.rejection_reason not in REJECTION_REASON_ORDER:
                raise RuntimeError(
                    "Unexpected rejection reason: "
                    f"{record.rejection_reason!r}"
                )
            reason_by_model[record.model_name][record.rejection_reason] += 1

    model_rows = []

    for model in MODEL_ORDER:
        total = model_counts[model]
        validated = status_by_model[model]["validated"]
        rejected = status_by_model[model]["rejected"]

        if validated + rejected != total:
            raise RuntimeError(
                f"{model}: status counts do not sum to total"
            )

        model_rows.append(
            {
                "model": model,
                "n_total": total,
                "n_validated": validated,
                "n_rejected": rejected,
                "validated_percent": 100.0 * validated / total,
                "rejected_percent": 100.0 * rejected / total,
            }
        )

    model_summary = pd.DataFrame(model_rows).set_index("model")

    rejection_rows = []

    for model in MODEL_ORDER:
        rejected = int(model_summary.loc[model, "n_rejected"])
        row = {}

        for reason in REJECTION_REASON_ORDER:
            count = reason_by_model[model][reason]
            row[reason] = 100.0 * count / rejected if rejected else 0.0

        rejection_rows.append(row)

    rejection_summary = pd.DataFrame(
        rejection_rows,
        index=MODEL_ORDER,
        columns=REJECTION_REASON_ORDER,
    )

    if not np.allclose(
        rejection_summary.sum(axis=1).to_numpy(dtype=float),
        100.0,
        atol=1e-8,
    ):
        raise RuntimeError(
            "Per-model rejection profiles do not sum to 100%"
        )

    return model_summary, rejection_summary


def _new_figure():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_analysis_v2_publication_style()
    fig = plt.figure(figsize=(12.0, 4.8), constrained_layout=True)
    fig.patch.set_facecolor("white")
    return fig


def _rejection_cmap():
    from matplotlib.colors import LinearSegmentedColormap

    return LinearSegmentedColormap.from_list(
        "analysis_v2_rejection",
        [
            "#FFFFFF",
            ANALYSIS_V2_OVERVIEW_CREAM,
            "#829DA6",
            "#304862",
        ],
    )


def _panel_label(ax, label: str) -> None:
    ax.text(
        -0.08,
        1.06,
        label,
        transform=ax.transAxes,
        fontsize=12,
        fontweight="bold",
        va="top",
        ha="left",
        color=ANALYSIS_V2_DARK_TEXT,
    )


def _plot_validation_outcome(ax, model_summary) -> None:
    y = list(range(len(MODEL_ORDER)))

    ax.barh(
        y,
        [100.0] * len(MODEL_ORDER),
        color="#EEEAE2",
        edgecolor="none",
        height=0.62,
        zorder=1,
    )

    for index, model in enumerate(MODEL_ORDER):
        value = float(model_summary.loc[model, "validated_percent"])
        n_validated = int(model_summary.loc[model, "n_validated"])
        n_total = int(model_summary.loc[model, "n_total"])

        ax.barh(
            index,
            value,
            color=MODEL_COLORS[model],
            edgecolor=ANALYSIS_V2_DARK_TEXT,
            linewidth=0.55,
            height=0.62,
            zorder=2,
        )

        ax.text(
            min(value + 1.5, 97.0),
            index,
            f"{n_validated}/{n_total} ({value:.1f}%)",
            va="center",
            ha="left" if value < 85 else "right",
            fontsize=8,
            color=ANALYSIS_V2_DARK_TEXT,
            zorder=3,
        )

    ax.set_yticks(y)
    ax.set_yticklabels(MODEL_ORDER)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Validated structures (%)")
    ax.set_title("Structural validation outcome", pad=8)
    ax.grid(axis="x", color="#D5D5D5", linewidth=0.45, alpha=0.5)
    ax.set_axisbelow(True)
    _panel_label(ax, "A")


def _plot_rejection_profile(ax, rejection_summary) -> None:
    values = rejection_summary.to_numpy(dtype=float)
    vmax = float(values.max())

    image = ax.imshow(
        values,
        aspect="auto",
        vmin=0.0,
        vmax=vmax,
        cmap=_rejection_cmap(),
    )

    ax.set_xticks(range(len(REJECTION_REASON_ORDER)))
    ax.set_xticklabels(
        [REJECTION_REASON_LABELS[key] for key in REJECTION_REASON_ORDER],
        rotation=0,
    )
    ax.set_yticks(range(len(MODEL_ORDER)))
    ax.set_yticklabels(MODEL_ORDER)
    ax.set_title("Rejection profile among rejected structures", pad=8)

    threshold = 0.52 * vmax

    for row_index in range(values.shape[0]):
        for column_index in range(values.shape[1]):
            value = float(values[row_index, column_index])

            if abs(value) < 0.05:
                continue

            text_color = (
                "white"
                if value >= threshold
                else ANALYSIS_V2_DARK_TEXT
            )

            ax.text(
                column_index,
                row_index,
                f"{value:.1f}",
                ha="center",
                va="center",
                fontsize=7.5,
                color=text_color,
            )

    cbar = ax.figure.colorbar(image, ax=ax, pad=0.02)
    cbar.set_label("Share of rejected structures (%)")
    _panel_label(ax, "B")


def save_validation_figure(
    model_summary,
    rejection_summary,
    *,
    output_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> FigureExportPaths:
    import matplotlib.pyplot as plt

    fig = _new_figure()
    axes = fig.subplots(
        1,
        2,
        gridspec_kw={"width_ratios": [0.85, 1.35]},
    )

    _plot_validation_outcome(axes[0], model_summary)
    _plot_rejection_profile(axes[1], rejection_summary)

    paths = save_analysis_v2_figure_bundle(
        fig,
        output_dir,
        FIGURE_BASENAME,
    )
    plt.close(fig)
    return paths


def run_structural_validation_figure(
    input_csv: str | Path = VALIDATION_INPUT,
    figure_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    audit_dir: str | Path = ANALYSIS_V2_AUDIT_OUTPUT_DIR,
) -> ValidationFigureReport:
    records = read_ragged_validation_records(input_csv)
    model_summary, rejection_summary = build_validation_tables(records)

    audit_root = Path(audit_dir)
    audit_root.mkdir(parents=True, exist_ok=True)

    model_summary_csv = audit_root / MODEL_SUMMARY_CSV
    rejection_summary_csv = audit_root / REJECTION_SUMMARY_CSV

    model_summary.to_csv(model_summary_csv)
    rejection_summary.to_csv(rejection_summary_csv)

    figure_paths = save_validation_figure(
        model_summary,
        rejection_summary,
        output_dir=figure_dir,
    )

    return ValidationFigureReport(
        input_csv=Path(input_csv),
        n_rows=len(records),
        model_summary=model_summary,
        rejection_summary=rejection_summary,
        model_summary_csv=model_summary_csv,
        rejection_summary_csv=rejection_summary_csv,
        figure_paths=figure_paths,
    )
