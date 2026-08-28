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


FIGURE_BASENAME = "paper_pipeline_v2_preview"

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


@dataclass(frozen=True)
class PaperPipelineFigureReport:
    figure_paths: FigureExportPaths


def _box(
    ax,
    *,
    x: float,
    y: float,
    w: float,
    h: float,
    facecolor: str,
    edgecolor: str = "#AEB7C2",
    linewidth: float = 0.85,
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
    linewidth: float = 1.0,
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
    fontsize: float = 9.0,
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
    fontsize: float = 7.0,
    color: str = "#5C5A55",
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
        zorder=5,
    )


def _cohort_pill(
    ax,
    *,
    x: float,
    y: float,
    w: float,
    label: str,
    cohort: str,
) -> None:
    h = 0.034

    _box(
        ax,
        x=x,
        y=y,
        w=w,
        h=h,
        facecolor=ANALYSIS_V2_MAGNETIC_COHORT_COLORS[cohort],
        edgecolor="white",
        linewidth=0.55,
        radius=0.008,
        zorder=4,
    )

    ax.text(
        x + w / 2,
        y + h / 2,
        label,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=6.8,
        fontweight="bold",
        color="white",
        zorder=5,
    )


def _model_group(
    ax,
    *,
    x: float,
    y: float,
    w: float,
    model_name: str,
    chips: tuple[tuple[str, str], ...],
) -> list[float]:
    _title(
        ax,
        x=x + w / 2,
        y=y + 0.055,
        text=model_name,
        fontsize=8.0,
    )

    pill_y = y - 0.010

    if len(chips) == 1:
        pill_w = w * 0.55
        pill_x = x + (w - pill_w) / 2

        label, cohort = chips[0]

        _cohort_pill(
            ax,
            x=pill_x,
            y=pill_y,
            w=pill_w,
            label=label,
            cohort=cohort,
        )

        return [pill_x + pill_w / 2]

    gap = 0.007
    pill_w = (w * 0.86 - gap) / 2
    total = 2 * pill_w + gap
    pill_x0 = x + (w - total) / 2

    centers = []

    for i, (label, cohort) in enumerate(chips):
        pill_x = pill_x0 + i * (pill_w + gap)

        _cohort_pill(
            ax,
            x=pill_x,
            y=pill_y,
            w=pill_w,
            label=label,
            cohort=cohort,
        )

        centers.append(pill_x + pill_w / 2)

    return centers


def _stage_box(
    ax,
    *,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    facecolor: str,
    note: str | None = None,
    title_size: float = 9.0,
) -> None:
    _box(
        ax,
        x=x,
        y=y,
        w=w,
        h=h,
        facecolor=facecolor,
        edgecolor="#AAB4C0",
        linewidth=0.85,
        radius=0.012,
    )

    if note is None:
        _title(
            ax,
            x=x + w / 2,
            y=y + h / 2,
            text=title,
            fontsize=title_size,
        )
    else:
        _title(
            ax,
            x=x + w / 2,
            y=y + h * 0.60,
            text=title,
            fontsize=title_size,
        )
        _note(
            ax,
            x=x + w / 2,
            y=y + h * 0.26,
            text=note,
            fontsize=7.0,
        )


def save_paper_pipeline_figure(
    *,
    output_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> FigureExportPaths:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_analysis_v2_publication_style()

    fig, ax = plt.subplots(figsize=(14.8, 7.2))
    fig.patch.set_facecolor("white")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ------------------------------------------------------------
    # Top row: generation cohorts
    # ------------------------------------------------------------

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

    group_w = 0.17
    gap = 0.022
    total_w = 5 * group_w + 4 * gap
    start_x = (1 - total_w) / 2
    top_y = 0.885

    centers = []

    for i, (name, chips) in enumerate(model_specs):
        x = start_x + i * (group_w + gap)
        centers.extend(
            _model_group(
                ax,
                x=x,
                y=top_y,
                w=group_w,
                model_name=name,
                chips=chips,
            )
        )

    convergence_y = 0.805

    for cx in centers:
        _line(
            ax,
            x0=cx,
            y0=top_y - 0.012,
            x1=cx,
            y1=convergence_y,
            linewidth=0.9,
        )

    _line(
        ax,
        x0=min(centers),
        y0=convergence_y,
        x1=max(centers),
        y1=convergence_y,
        linewidth=0.95,
    )

    _arrow(
        ax,
        x0=0.5,
        y0=convergence_y,
        x1=0.5,
        y1=0.725,
    )

    # ------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------

    # Structures
    _stage_box(
        ax,
        x=0.390,
        y=0.640,
        w=0.220,
        h=0.080,
        title="Structures",
        facecolor="#F7F7F4",
    )

    _arrow(
        ax,
        x0=0.5,
        y0=0.640,
        x1=0.5,
        y1=0.565,
    )

    # Structural QC
    _stage_box(
        ax,
        x=0.360,
        y=0.485,
        w=0.280,
        h=0.085,
        title="Structural QC",
        facecolor="#F2E4C4",
    )

    _arrow(
        ax,
        x0=0.5,
        y0=0.485,
        x1=0.5,
        y1=0.435,
    )

    # Branch split
    split_y = 0.435
    left_center = 0.32
    right_center = 0.68

    _line(
        ax,
        x0=left_center,
        y0=split_y,
        x1=right_center,
        y1=split_y,
    )

    # Upper branch nodes
    _stage_box(
        ax,
        x=0.175,
        y=0.305,
        w=0.290,
        h=0.090,
        title="Relaxation",
        facecolor="#F6EFE5",
    )
    _arrow(
        ax,
        x0=left_center,
        y0=split_y,
        x1=left_center,
        y1=0.395,
    )

    _stage_box(
        ax,
        x=0.535,
        y=0.305,
        w=0.290,
        h=0.090,
        title="Magnetism",
        facecolor="#EEF3F4",
    )
    _arrow(
        ax,
        x0=right_center,
        y0=split_y,
        x1=right_center,
        y1=0.395,
    )

    # Lower branch nodes
    _stage_box(
        ax,
        x=0.175,
        y=0.190,
        w=0.290,
        h=0.080,
        title="Energy",
        facecolor="#FAF6F0",
    )
    _arrow(
        ax,
        x0=left_center,
        y0=0.305,
        x1=left_center,
        y1=0.270,
    )

    _stage_box(
        ax,
        x=0.535,
        y=0.190,
        w=0.290,
        h=0.080,
        title="Magnetic descriptors",
        facecolor="#F4F7F8",
    )
    _arrow(
        ax,
        x0=right_center,
        y0=0.305,
        x1=right_center,
        y1=0.270,
    )

    # Merge energetic and magnetic branches.
    merge_y = 0.155

    _line(
        ax,
        x0=left_center,
        y0=0.190,
        x1=left_center,
        y1=merge_y,
    )
    _line(
        ax,
        x0=right_center,
        y0=0.190,
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

    # Harmonized Descriptor v2 layer.
    desc_x = 0.395
    desc_y = 0.095
    desc_w = 0.210
    desc_h = 0.045

    _arrow(
        ax,
        x0=0.5,
        y0=merge_y,
        x1=0.5,
        y1=desc_y + desc_h,
    )

    _stage_box(
        ax,
        x=desc_x,
        y=desc_y,
        w=desc_w,
        h=desc_h,
        title="Magnetically informed descriptors",
        facecolor="#E8EFF1",
        title_size=8.4,
    )

    # Final comparative analysis.
    ana_x = 0.340
    ana_y = 0.005
    ana_w = 0.320
    ana_h = 0.065

    _arrow(
        ax,
        x0=0.5,
        y0=desc_y,
        x1=0.5,
        y1=ana_y + ana_h,
    )

    _stage_box(
        ax,
        x=ana_x,
        y=ana_y,
        w=ana_w,
        h=ana_h,
        title="Integrated structural and magnetic analysis",
        facecolor="#E9EDF4",
        title_size=8.8,
    )

    paths = save_analysis_v2_figure_bundle(
        fig,
        output_dir,
        FIGURE_BASENAME,
    )
    plt.close(fig)

    return paths


def run_paper_pipeline_figure(
    *,
    figure_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> PaperPipelineFigureReport:
    if tuple(ANALYSIS_V2_MAGNETIC_COHORT_ORDER) != EXPECTED_COHORTS:
        raise RuntimeError(
            "Analysis v2 cohort order differs from paper pipeline contract"
        )

    paths = save_paper_pipeline_figure(
        output_dir=figure_dir,
    )

    return PaperPipelineFigureReport(
        figure_paths=paths,
    )
