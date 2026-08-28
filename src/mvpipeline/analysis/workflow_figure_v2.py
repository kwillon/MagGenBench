from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .plotting_v2 import (
    ANALYSIS_V2_DARK_TEXT,
    ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    ANALYSIS_V2_MAGNETIC_COHORT_COLORS,
    ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
    FigureExportPaths,
    apply_analysis_v2_publication_style,
    save_analysis_v2_figure_bundle,
)


FIGURE_BASENAME = "study_workflow_v2_preview"

EXPECTED_COHORTS = (
    "mattergen_baseline",
    "mattergen_finetuned",
    "concdvae_baseline",
    "concdvae_finetuned",
    "crystalformer_baseline",
    "crystallm_baseline",
    "crysjepa_base",
    "crysjepa_refined",
)

PIPELINE_STAGE_GROUPS = (
    (
        "Structural preparation",
        (
            "01_master",
            "02_validation",
            "03_features",
        ),
    ),
    (
        "Physics-informed enrichment",
        (
            "04_magnetic_screening",
            "05_relaxation",
            "06_energy",
            "07_magnetic_descriptors",
        ),
    ),
    (
        "Harmonized descriptor layer",
        (
            "08_standardized_enrichment",
            "09_descriptor_v2_magnetic",
        ),
    ),
    (
        "Comparative analysis",
        (
            "10_analysis_v2_magnetic",
        ),
    ),
)


@dataclass(frozen=True)
class WorkflowFigureReport:
    figure_paths: FigureExportPaths


def _box(
    ax,
    *,
    x: float,
    y: float,
    w: float,
    h: float,
    facecolor: str = "white",
    edgecolor: str = "#AEB7C2",
    linewidth: float = 0.8,
    radius: float = 0.012,
    zorder: int = 2,
):
    from matplotlib.patches import FancyBboxPatch

    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.006,rounding_size={radius}",
        transform=ax.transAxes,
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=linewidth,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def _arrow(
    ax,
    *,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    linewidth: float = 1.15,
) -> None:
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        xycoords=ax.transAxes,
        textcoords=ax.transAxes,
        arrowprops={
            "arrowstyle": "-|>",
            "linewidth": linewidth,
            "color": ANALYSIS_V2_DARK_TEXT,
            "mutation_scale": 12,
            "shrinkA": 2,
            "shrinkB": 2,
        },
        zorder=1,
    )


def _line(
    ax,
    *,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    linewidth: float = 1.05,
) -> None:
    ax.plot(
        [x0, x1],
        [y0, y1],
        transform=ax.transAxes,
        color=ANALYSIS_V2_DARK_TEXT,
        linewidth=linewidth,
        solid_capstyle="round",
        zorder=1,
    )


def _title(
    ax,
    *,
    x: float,
    y: float,
    text: str,
    fontsize: float = 9.2,
) -> None:
    ax.text(
        x,
        y,
        text,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="bold",
        color=ANALYSIS_V2_DARK_TEXT,
        zorder=5,
    )


def _note(
    ax,
    *,
    x: float,
    y: float,
    text: str,
    fontsize: float = 7.3,
    color: str = "#5B554D",
) -> None:
    ax.text(
        x,
        y,
        text,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=color,
        linespacing=1.15,
        zorder=5,
    )


def _cohort_chip(
    ax,
    *,
    x: float,
    y: float,
    w: float,
    h: float,
    label: str,
    cohort: str,
) -> None:
    _box(
        ax,
        x=x,
        y=y,
        w=w,
        h=h,
        facecolor=ANALYSIS_V2_MAGNETIC_COHORT_COLORS[cohort],
        edgecolor="white",
        linewidth=0.55,
        radius=0.007,
        zorder=4,
    )

    ax.text(
        x + w / 2,
        y + h / 2,
        label,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=7.0,
        fontweight="bold",
        color="white",
        zorder=5,
    )


def _model_card(
    ax,
    *,
    x: float,
    y: float,
    w: float,
    h: float,
    model: str,
    chips: tuple[tuple[str, str], ...],
) -> None:
    _box(
        ax,
        x=x,
        y=y,
        w=w,
        h=h,
        facecolor="#FAFAF8",
        edgecolor="#C8CDD3",
        linewidth=0.7,
        radius=0.010,
    )

    _title(
        ax,
        x=x + w / 2,
        y=y + h * 0.68,
        text=model,
        fontsize=8.3,
    )

    chip_h = h * 0.28
    chip_y = y + h * 0.13

    if len(chips) == 1:
        chip_w = w * 0.58
        chip_x = x + (w - chip_w) / 2

        label, cohort = chips[0]

        _cohort_chip(
            ax,
            x=chip_x,
            y=chip_y,
            w=chip_w,
            h=chip_h,
            label=label,
            cohort=cohort,
        )
        return

    gap = 0.007
    chip_w = (w - 0.024 - gap) / 2
    chip_x = x + 0.012

    for i, (label, cohort) in enumerate(chips):
        _cohort_chip(
            ax,
            x=chip_x + i * (chip_w + gap),
            y=chip_y,
            w=chip_w,
            h=chip_h,
            label=label,
            cohort=cohort,
        )


def _pipeline_box(
    ax,
    *,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    note: str,
    facecolor: str,
    title_size: float = 8.5,
) -> None:
    _box(
        ax,
        x=x,
        y=y,
        w=w,
        h=h,
        facecolor=facecolor,
        edgecolor="#AAB4C0",
        linewidth=0.8,
        radius=0.012,
    )

    _title(
        ax,
        x=x + w / 2,
        y=y + h * 0.63,
        text=title,
        fontsize=title_size,
    )

    _note(
        ax,
        x=x + w / 2,
        y=y + h * 0.31,
        text=note,
        fontsize=7.1,
    )


def save_study_workflow_figure(
    *,
    output_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> FigureExportPaths:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_analysis_v2_publication_style()

    fig, ax = plt.subplots(figsize=(14.8, 7.6))
    fig.patch.set_facecolor("white")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ------------------------------------------------------------------
    # Generated structure sets
    # ------------------------------------------------------------------

    _title(
        ax,
        x=0.5,
        y=0.955,
        text="Generated structure sets",
        fontsize=10.5,
    )

    model_specs = (
        (
            "MatterGen",
            (
                ("Base", "mattergen_baseline"),
                ("Fine-tuned", "mattergen_finetuned"),
            ),
        ),
        (
            "Con-CDVAE",
            (
                ("Base", "concdvae_baseline"),
                ("Fine-tuned", "concdvae_finetuned"),
            ),
        ),
        (
            "CrystalFormer",
            (
                ("Base", "crystalformer_baseline"),
            ),
        ),
        (
            "CrystaLLM",
            (
                ("Base", "crystallm_baseline"),
            ),
        ),
        (
            "Crys-JEPA",
            (
                ("Base", "crysjepa_base"),
                ("Refined", "crysjepa_refined"),
            ),
        ),
    )

    card_w = 0.168
    card_h = 0.125
    gap = 0.018

    total_w = 5 * card_w + 4 * gap
    start_x = (1 - total_w) / 2
    card_y = 0.805

    centers = []

    for i, (model, chips) in enumerate(model_specs):
        x = start_x + i * (card_w + gap)
        centers.append(x + card_w / 2)

        _model_card(
            ax,
            x=x,
            y=card_y,
            w=card_w,
            h=card_h,
            model=model,
            chips=chips,
        )

    # All generation cohorts converge into the same evaluation pipeline.
    convergence_y = 0.755

    for center in centers:
        _line(
            ax,
            x0=center,
            y0=card_y,
            x1=center,
            y1=convergence_y,
        )

    _line(
        ax,
        x0=centers[0],
        y0=convergence_y,
        x1=centers[-1],
        y1=convergence_y,
    )

    _arrow(
        ax,
        x0=0.5,
        y0=convergence_y,
        x1=0.5,
        y1=0.690,
    )

    # ------------------------------------------------------------------
    # Structural validation and basic features
    # ------------------------------------------------------------------

    qc_x = 0.355
    qc_y = 0.575
    qc_w = 0.290
    qc_h = 0.105

    _pipeline_box(
        ax,
        x=qc_x,
        y=qc_y,
        w=qc_w,
        h=qc_h,
        title="Structural validation & basic features",
        note="validity · geometry · composition · symmetry",
        facecolor="#F2E4C4",
        title_size=8.8,
    )

    _arrow(
        ax,
        x0=0.5,
        y0=qc_y,
        x1=0.5,
        y1=0.520,
    )

    # ------------------------------------------------------------------
    # Parallel energetic and magnetic branches
    # ------------------------------------------------------------------

    left_x = 0.185
    right_x = 0.555
    branch_w = 0.260
    branch_h = 0.100

    top_y = 0.405
    low_y = 0.270

    left_center = left_x + branch_w / 2
    right_center = right_x + branch_w / 2

    split_y = 0.520

    _line(
        ax,
        x0=left_center,
        y0=split_y,
        x1=right_center,
        y1=split_y,
    )

    _pipeline_box(
        ax,
        x=left_x,
        y=top_y,
        w=branch_w,
        h=branch_h,
        title="Structure relaxation",
        note="relaxed geometry where available",
        facecolor="#F6EFE5",
    )

    _pipeline_box(
        ax,
        x=right_x,
        y=top_y,
        w=branch_w,
        h=branch_h,
        title="Magnetic screening",
        note="composition-based magnetic annotations",
        facecolor="#EEF3F4",
    )

    _arrow(
        ax,
        x0=left_center,
        y0=split_y,
        x1=left_center,
        y1=top_y + branch_h,
    )

    _arrow(
        ax,
        x0=right_center,
        y0=split_y,
        x1=right_center,
        y1=top_y + branch_h,
    )

    _pipeline_box(
        ax,
        x=left_x,
        y=low_y,
        w=branch_w,
        h=branch_h,
        title="CHGNet energy",
        note="predicted total energy per atom",
        facecolor="#FAF6F0",
    )

    _pipeline_box(
        ax,
        x=right_x,
        y=low_y,
        w=branch_w,
        h=branch_h,
        title="Magnetic descriptors",
        note="DXMag · composition · local magnetic geometry",
        facecolor="#F4F7F8",
    )

    _arrow(
        ax,
        x0=left_center,
        y0=top_y,
        x1=left_center,
        y1=low_y + branch_h,
    )

    _arrow(
        ax,
        x0=right_center,
        y0=top_y,
        x1=right_center,
        y1=low_y + branch_h,
    )

    # ------------------------------------------------------------------
    # Merge the energetic and magnetic branches
    # ------------------------------------------------------------------

    merge_y = 0.225

    _line(
        ax,
        x0=left_center,
        y0=low_y,
        x1=left_center,
        y1=merge_y,
    )

    _line(
        ax,
        x0=right_center,
        y0=low_y,
        x1=right_center,
        y1=merge_y,
    )

    _line(
        ax,
        x0=left_center,
        y0=merge_y,
        x1=right_center,
        y1=merge_y,
    )

    # ------------------------------------------------------------------
    # Harmonized descriptor layer
    # ------------------------------------------------------------------

    desc_x = 0.335
    desc_y = 0.105
    desc_w = 0.330
    desc_h = 0.090

    _arrow(
        ax,
        x0=0.5,
        y0=merge_y,
        x1=0.5,
        y1=desc_y + desc_h,
    )

    _pipeline_box(
        ax,
        x=desc_x,
        y=desc_y,
        w=desc_w,
        h=desc_h,
        title="Standardized enrichment\n+ magnetically informed descriptors",
        note="harmonized magnetic descriptor space",
        facecolor="#E8EFF1",
        title_size=8.4,
    )

    # ------------------------------------------------------------------
    # Integrated structural and magnetic analysis
    # ------------------------------------------------------------------

    ana_x = 0.315
    ana_y = 0.015
    ana_w = 0.370
    ana_h = 0.075

    _arrow(
        ax,
        x0=0.5,
        y0=desc_y,
        x1=0.5,
        y1=ana_y + ana_h,
    )

    _pipeline_box(
        ax,
        x=ana_x,
        y=ana_y,
        w=ana_w,
        h=ana_h,
        title="Integrated structural and magnetic analysis",
        note=(
            "structure · magnetism · energy · PCA · "
            "adaptation · diversity"
        ),
        facecolor="#E9EDF4",
        title_size=8.6,
    )

    paths = save_analysis_v2_figure_bundle(
        fig,
        output_dir,
        FIGURE_BASENAME,
    )
    plt.close(fig)

    return paths


def run_study_workflow(
    *,
    figure_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> WorkflowFigureReport:
    if tuple(ANALYSIS_V2_MAGNETIC_COHORT_ORDER) != EXPECTED_COHORTS:
        raise RuntimeError(
            "Analysis v2 cohort order differs from workflow figure contract"
        )

    paths = save_study_workflow_figure(
        output_dir=figure_dir,
    )

    return WorkflowFigureReport(
        figure_paths=paths,
    )
