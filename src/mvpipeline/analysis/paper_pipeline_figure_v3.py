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


FIGURE_BASENAME = "paper_pipeline_v3_preview"

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

MODEL_GROUPS = (
    ("MatterGen", (("Base", "mattergen_baseline"), ("Fine-tuned", "mattergen_finetuned"))),
    ("Con-CDVAE", (("Base", "concdvae_baseline"), ("Fine-tuned", "concdvae_finetuned"))),
    ("CrystalFormer", (("Base", "crystalformer_baseline"), ("Fine-tuned*", "crystalformer_finetuned"))),
    ("CrystaLLM", (("Base", "crystallm_baseline"), ("Fine-tuned*", "crystallm_finetuned"))),
    ("Crys-JEPA", (("Base", "crysjepa_base"), ("Refined", "crysjepa_refined"))),
)

MODEL_VARIANT_COLORS = {
    **ANALYSIS_V2_MAGNETIC_COHORT_COLORS,
    "crystalformer_finetuned": "#F5D3C7",
    "crystallm_finetuned": "#E8C9C6",
}

PROVISIONAL_VARIANTS = {
    "crystalformer_finetuned": "#A95035",
    "crystallm_finetuned": "#833E38",
}

REFERENCE_BRANCHES = ("MAGNDATA", "AFM", "FM", "FiM", "NM")

PARALLEL_BRANCHES = {
    "Property prediction": ("CHGNet energy", "DXMag magnetic moment"),
    "Magnetic descriptors": ("Composition", "Local magnetic geometry", "Symmetry"),
}

WORKFLOW_CONTENT_LABELS = (
    "Generated structures / native outputs",
    "CIF harmonization",
    "Structural quality control",
    "Retained structures for downstream analysis",
    "CHGNet energy",
    "Predicted energy per atom",
    "DXMag magnetic moment",
    "Composition-based predicted moment",
    "Magnetic composition",
    "3d, selected 4d/5d, lanthanides",
    "Local magnetic geometry",
    "Coordination and neighbor distances",
    "Symmetry",
    "Magnetic-site and crystallographic symmetry",
    "Descriptor construction",
    "kNN distances",
    "Cmag-NM scoring",
    "Magnetic-reference contrast",
    "Selected candidates",
    "DFT calculations",
    "DFT validation",
    "Structural retention and rejection profiles",
    "Magnetic-domain composition and local environments",
    "Reference-space enrichment",
    "Descriptor-space PCA",
    "Energy-magnetism landscape",
    "Chemical composition and diversity",
)


@dataclass(frozen=True)
class PaperPipelineFigureV3Report:
    figure_paths: FigureExportPaths


def _box(ax, *, x, y, w, h, facecolor, edgecolor="#B9C4CE", linewidth=0.75,
         radius=0.008, zorder=2, linestyle="solid"):
    from matplotlib.patches import FancyBboxPatch

    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.0035,rounding_size={radius}",
        transform=ax.transAxes, facecolor=facecolor, edgecolor=edgecolor,
        linewidth=linewidth, linestyle=linestyle, zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def _panel(ax, *, x, y, w, h, title, facecolor, edgecolor="#D0D8DE",
           title_color=ANALYSIS_V2_DARK_TEXT, title_size=9.0):
    _box(ax, x=x, y=y, w=w, h=h, facecolor=facecolor, edgecolor=edgecolor,
         linewidth=0.92, radius=0.010, zorder=0)
    ax.text(
        x + 0.014, y + h - 0.025, title, transform=ax.transAxes,
        ha="left", va="center", fontsize=title_size, fontweight="bold",
        color=title_color, zorder=6,
    )


def _arrow(ax, *, x0, y0, x1, y1, color="#66727D", linewidth=0.9,
           zorder=1):
    ax.annotate(
        "", xy=(x1, y1), xytext=(x0, y0), xycoords=ax.transAxes,
        textcoords=ax.transAxes,
        arrowprops={"arrowstyle": "-|>", "linewidth": linewidth, "color": color,
                    "mutation_scale": 10, "shrinkA": 2, "shrinkB": 2},
        zorder=zorder,
    )


def _line(ax, *, x0, y0, x1, y1, color="#7A858F", linewidth=0.8, zorder=1):
    ax.plot(
        [x0, x1], [y0, y1], transform=ax.transAxes, color=color,
        linewidth=linewidth, solid_capstyle="round", zorder=zorder,
    )


def _orthogonal_down_arrow(ax, *, x0, y0, x1, y1, elbow_y,
                           color="#66727D", linewidth=0.9):
    _line(ax, x0=x0, y0=y0, x1=x0, y1=elbow_y,
          color=color, linewidth=linewidth)
    _line(ax, x0=x0, y0=elbow_y, x1=x1, y1=elbow_y,
          color=color, linewidth=linewidth)
    _arrow(ax, x0=x1, y0=elbow_y, x1=x1, y1=y1,
           color=color, linewidth=linewidth)


def _icon(ax, kind, *, x, y, size=0.018, color="#52697B", zorder=6):
    from matplotlib.patches import Circle, Ellipse, Polygon, Rectangle, Wedge

    tx = ax.transAxes
    lw = 1.05

    if kind == "database":
        ax.add_patch(Rectangle((x - size, y - size * 0.6), 2 * size, size * 1.2,
                               transform=tx, fill=False, edgecolor=color,
                               linewidth=lw, zorder=zorder))
        for offset in (-0.6, 0.6):
            ax.add_patch(Ellipse((x, y + offset * size), 2 * size, size * 0.55,
                                 transform=tx, fill=False, edgecolor=color,
                                 linewidth=lw, zorder=zorder))
    elif kind == "document":
        ax.add_patch(Rectangle((x - size * 0.72, y - size), size * 1.35, size * 1.8,
                               transform=tx, fill=False, edgecolor=color,
                               linewidth=lw, zorder=zorder))
        ax.add_patch(Polygon(((x + size * 0.18, y + size * 0.8),
                              (x + size * 0.63, y + size * 0.35),
                              (x + size * 0.18, y + size * 0.35)),
                             transform=tx, fill=False, edgecolor=color,
                             linewidth=lw, zorder=zorder))
        _line(ax, x0=x - size * 0.45, y0=y, x1=x + size * 0.30, y1=y,
              color=color, linewidth=lw, zorder=zorder)
    elif kind == "gear":
        ax.add_patch(Circle((x, y), size * 0.48, transform=tx, fill=False,
                            edgecolor=color, linewidth=lw, zorder=zorder))
        ax.add_patch(Circle((x, y), size * 0.16, transform=tx, fill=False,
                            edgecolor=color, linewidth=lw, zorder=zorder))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (.7, .7), (-.7, .7)):
            _line(ax, x0=x + dx * size * 0.48, y0=y + dy * size * 0.48,
                  x1=x + dx * size * 0.75, y1=y + dy * size * 0.75,
                  color=color, linewidth=lw, zorder=zorder)
    elif kind == "qc":
        ax.add_patch(Circle((x - size * 0.12, y + size * 0.10), size * 0.52,
                            transform=tx, fill=False, edgecolor=color,
                            linewidth=lw, zorder=zorder))
        _line(ax, x0=x + size * 0.28, y0=y - size * 0.28,
              x1=x + size * 0.78, y1=y - size * 0.78,
              color=color, linewidth=lw, zorder=zorder)
        ax.plot([x - size * 0.38, x - size * 0.12, x + size * 0.30],
                [y + size * 0.08, y - size * 0.18, y + size * 0.30],
                transform=tx, color=color, linewidth=lw, zorder=zorder)
    elif kind == "cube":
        front = ((-0.62, -0.55), (0.35, -0.55), (0.35, 0.42), (-0.62, 0.42))
        back = tuple((px + 0.30, py + 0.30) for px, py in front)
        for shape in (front, back):
            ax.add_patch(Polygon(
                tuple((x + px * size, y + py * size) for px, py in shape),
                transform=tx, fill=False, closed=True, edgecolor=color,
                linewidth=lw, zorder=zorder,
            ))
        for first, second in zip(front, back):
            _line(ax, x0=x + first[0] * size, y0=y + first[1] * size,
                  x1=x + second[0] * size, y1=y + second[1] * size,
                  color=color, linewidth=lw, zorder=zorder)
    elif kind == "atoms":
        points = ((0.0, 0.0), (-0.70, 0.25), (0.58, 0.52),
                  (0.62, -0.48), (-0.48, -0.58))
        for index in range(1, len(points)):
            _line(ax, x0=x, y0=y,
                  x1=x + points[index][0] * size,
                  y1=y + points[index][1] * size,
                  color=color, linewidth=lw, zorder=zorder)
        for index, (px, py) in enumerate(points):
            ax.add_patch(Circle(
                (x + px * size, y + py * size),
                size * (0.20 if index == 0 else 0.14), transform=tx,
                facecolor=color if index == 0 else "white",
                edgecolor=color, linewidth=lw, zorder=zorder + 1,
            ))
    elif kind == "features":
        heights = (0.52, 0.92, 0.68)
        for index, height in enumerate(heights):
            bar_x = x + (index - 1) * size * 0.52
            ax.add_patch(Rectangle(
                (bar_x - size * 0.13, y - size * 0.62),
                size * 0.26, size * height, transform=tx,
                fill=False, edgecolor=color, linewidth=lw, zorder=zorder,
            ))
            ax.add_patch(Circle(
                (bar_x, y + size * 0.55), size * 0.10, transform=tx,
                facecolor=color, edgecolor="none", zorder=zorder + 1,
            ))
            if index:
                _line(ax, x0=bar_x - size * 0.52, y0=y + size * 0.55,
                      x1=bar_x, y1=y + size * 0.55,
                      color=color, linewidth=lw, zorder=zorder)
    elif kind == "knn":
        points = ((-0.72, -0.38), (-0.34, 0.34), (0.02, -0.02),
                  (0.48, 0.48), (0.73, -0.30))
        focus = points[2]
        for neighbor in (points[1], points[3]):
            _line(ax, x0=x + focus[0] * size, y0=y + focus[1] * size,
                  x1=x + neighbor[0] * size, y1=y + neighbor[1] * size,
                  color=color, linewidth=lw, zorder=zorder)
        for index, (px, py) in enumerate(points):
            ax.add_patch(Circle(
                (x + px * size, y + py * size), size * 0.12,
                transform=tx, facecolor=color, edgecolor="none",
                zorder=zorder + 1,
            ))
            if index == 2:
                ax.add_patch(Circle(
                    (x + px * size, y + py * size), size * 0.28,
                    transform=tx, fill=False, edgecolor=color,
                    linewidth=lw, zorder=zorder,
                ))
    elif kind == "candidate":
        points = ((0.0, 0.62), (-0.58, -0.38), (0.58, -0.38), (0.0, 0.0))
        for first, second in ((0, 1), (1, 2), (2, 0), (3, 0), (3, 1), (3, 2)):
            _line(ax, x0=x + points[first][0] * size,
                  y0=y + points[first][1] * size,
                  x1=x + points[second][0] * size,
                  y1=y + points[second][1] * size,
                  color=color, linewidth=lw, zorder=zorder)
        for px, py in points:
            ax.add_patch(Circle((x + px * size, y + py * size), size * 0.12,
                                transform=tx, facecolor=color, edgecolor="none",
                                zorder=zorder + 1))
        ax.add_patch(Circle((x, y), size * 0.82, transform=tx, fill=False,
                            edgecolor=color, linewidth=lw, zorder=zorder))
    elif kind == "clipboard":
        ax.add_patch(Rectangle(
            (x - size * 0.62, y - size * 0.72), size * 1.24, size * 1.35,
            transform=tx, fill=False, edgecolor=color, linewidth=lw,
            zorder=zorder,
        ))
        ax.add_patch(Rectangle(
            (x - size * 0.25, y + size * 0.48), size * 0.50, size * 0.25,
            transform=tx, facecolor="white", edgecolor=color, linewidth=lw,
            zorder=zorder + 1,
        ))
        ax.plot([x - size * 0.34, x - size * 0.08, x + size * 0.40],
                [y - size * 0.05, y - size * 0.32, y + size * 0.25],
                transform=tx, color=color, linewidth=lw, zorder=zorder + 1)
    elif kind == "crystal":
        points = ((-0.58, -0.50), (0.0, -0.50), (0.58, -0.50),
                  (-0.58, 0.05), (0.0, 0.05), (0.58, 0.05),
                  (-0.58, 0.60), (0.0, 0.60), (0.58, 0.60))
        for row in range(3):
            for column in range(2):
                first = points[row * 3 + column]
                second = points[row * 3 + column + 1]
                _line(ax, x0=x + first[0] * size, y0=y + first[1] * size,
                      x1=x + second[0] * size, y1=y + second[1] * size,
                      color=color, linewidth=lw, zorder=zorder)
        for column in range(3):
            for row in range(2):
                first = points[row * 3 + column]
                second = points[(row + 1) * 3 + column]
                _line(ax, x0=x + first[0] * size, y0=y + first[1] * size,
                      x1=x + second[0] * size, y1=y + second[1] * size,
                      color=color, linewidth=lw, zorder=zorder)
        for px, py in points:
            ax.add_patch(Circle((x + px * size, y + py * size), size * 0.10,
                                transform=tx, facecolor=color, edgecolor="none",
                                zorder=zorder + 1))
    elif kind in {"lattice", "graph", "geometry", "magnetic"}:
        points = ((-0.65, -0.45), (0.65, -0.45), (0.0, 0.62))
        if kind in {"lattice", "geometry"}:
            points += ((0.0, 0.0),)
        for first, second in ((0, 1), (1, 2), (2, 0)):
            _line(ax, x0=x + points[first][0] * size, y0=y + points[first][1] * size,
                  x1=x + points[second][0] * size, y1=y + points[second][1] * size,
                  color=color, linewidth=lw, zorder=zorder)
        if len(points) == 4:
            for index in range(3):
                _line(ax, x0=x, y0=y, x1=x + points[index][0] * size,
                      y1=y + points[index][1] * size, color=color,
                      linewidth=lw, zorder=zorder)
        for px, py in points:
            ax.add_patch(Circle((x + px * size, y + py * size), size * 0.14,
                                transform=tx, facecolor=color, edgecolor="none",
                                zorder=zorder + 1))
    elif kind in {"energy", "landscape"}:
        xs = (-0.85, -0.45, -0.05, 0.35, 0.80)
        ys = (0.45, -0.25, -0.55, -0.20, 0.55)
        ax.plot([x + px * size for px in xs], [y + py * size for py in ys],
                transform=tx, color=color, linewidth=lw, zorder=zorder)
    elif kind == "spin":
        _arrow(ax, x0=x - size * 0.45, y0=y - size * 0.55,
               x1=x - size * 0.45, y1=y + size * 0.60,
               color=color, linewidth=lw, zorder=zorder)
        _arrow(ax, x0=x + size * 0.45, y0=y + size * 0.55,
               x1=x + size * 0.45, y1=y - size * 0.60,
               color=color, linewidth=lw, zorder=zorder)
    elif kind == "symmetry":
        ax.add_patch(Rectangle((x - size * 0.65, y - size * 0.65), size * 1.3,
                               size * 1.3, transform=tx, fill=False,
                               edgecolor=color, linewidth=lw, zorder=zorder))
        _line(ax, x0=x - size * 0.65, y0=y - size * 0.65,
              x1=x + size * 0.65, y1=y + size * 0.65,
              color=color, linewidth=lw, zorder=zorder)
        _line(ax, x0=x - size * 0.65, y0=y + size * 0.65,
              x1=x + size * 0.65, y1=y - size * 0.65,
              color=color, linewidth=lw, zorder=zorder)
    elif kind in {"scatter", "pca"}:
        points = ((-.7, -.5), (-.35, .2), (-.05, -.15), (.35, .55), (.72, .1))
        for px, py in points:
            ax.add_patch(Circle((x + px * size, y + py * size), size * 0.12,
                                transform=tx, facecolor=color, edgecolor="none",
                                zorder=zorder))
    elif kind in {"contrast", "bars"}:
        for index, height in enumerate((0.55, 1.0, 0.72)):
            ax.add_patch(Rectangle((x + (index - 1) * size * 0.55 - size * 0.18,
                                    y - size * 0.65), size * 0.36, size * height,
                                   transform=tx, facecolor=color, edgecolor="none",
                                   zorder=zorder))
    elif kind == "monitor":
        ax.add_patch(Rectangle((x - size * 0.85, y - size * 0.45), size * 1.7,
                               size * 1.05, transform=tx, fill=False,
                               edgecolor=color, linewidth=lw, zorder=zorder))
        _line(ax, x0=x, y0=y - size * 0.45, x1=x, y1=y - size * 0.82,
              color=color, linewidth=lw, zorder=zorder)
        _line(ax, x0=x - size * 0.45, y0=y - size * 0.82,
              x1=x + size * 0.45, y1=y - size * 0.82,
              color=color, linewidth=lw, zorder=zorder)
        _line(ax, x0=x - size * 0.52, y0=y + size * 0.20,
              x1=x - size * 0.10, y1=y + size * 0.20,
              color=color, linewidth=lw, zorder=zorder)
        _line(ax, x0=x - size * 0.52, y0=y - size * 0.08,
              x1=x + size * 0.38, y1=y - size * 0.08,
              color=color, linewidth=lw, zorder=zorder)
    elif kind == "target":
        for scale in (0.75, 0.42):
            ax.add_patch(Circle((x, y), size * scale, transform=tx, fill=False,
                                edgecolor=color, linewidth=lw, zorder=zorder))
        ax.add_patch(Circle((x, y), size * 0.12, transform=tx,
                            facecolor=color, edgecolor="none", zorder=zorder))
    elif kind == "pie":
        ax.add_patch(Wedge((x, y), size * 0.72, 20, 220, transform=tx,
                           facecolor=color, alpha=0.28, edgecolor=color,
                           linewidth=lw, zorder=zorder))
        ax.add_patch(Wedge((x, y), size * 0.72, 225, 375, transform=tx,
                           fill=False, edgecolor=color, linewidth=lw,
                           zorder=zorder))


def _card(ax, *, x, y, w, h, title, note=None, icon=None, accent="#607A8B",
          facecolor="#FFFFFF", title_size=6.5, note_size=5.3,
          icon_position="left", icon_size=None):
    _box(ax, x=x, y=y, w=w, h=h, facecolor=facecolor, edgecolor="#C5CED5",
         linewidth=0.7, radius=0.006)
    if icon and icon_position == "left":
        size = icon_size if icon_size is not None else min(0.013, h * 0.18)
        _icon(ax, icon, x=x + 0.025, y=y + h / 2, size=size,
              color=accent)
        text_x, ha = x + 0.046, "left"
    else:
        text_x, ha = x + w / 2, "center"
        if icon:
            size = icon_size if icon_size is not None else min(0.011, h * 0.12)
            _icon(ax, icon, x=x + w / 2, y=y + h * 0.78,
                  size=size, color=accent)
    if note:
        title_y = y + h * (0.52 if icon_position == "top" else 0.63)
        note_y = y + h * (0.18 if icon_position == "top" else 0.30)
        ax.text(text_x, title_y, title, transform=ax.transAxes,
                ha=ha, va="center", fontsize=title_size, fontweight="bold",
                color=ANALYSIS_V2_DARK_TEXT, linespacing=1.05, zorder=6)
        ax.text(text_x, note_y, note, transform=ax.transAxes,
                ha=ha, va="center", fontsize=note_size, color="#626B73",
                linespacing=1.08, zorder=6)
    else:
        title_y = y + h * (0.34 if icon_position == "top" else 0.43)
        ax.text(text_x, title_y, title, transform=ax.transAxes,
                ha=ha, va="center", fontsize=title_size, fontweight="bold",
                color=ANALYSIS_V2_DARK_TEXT, linespacing=1.08, zorder=6)


def _chip(ax, *, x, y, w, h, label, facecolor, provisional_color=None):
    is_provisional = provisional_color is not None
    _box(ax, x=x, y=y, w=w, h=h, facecolor=facecolor,
         edgecolor=provisional_color if is_provisional else "white",
         linewidth=0.95 if is_provisional else 0.45,
         linestyle=(0, (3, 2)) if is_provisional else "solid",
         radius=0.004, zorder=4)
    ax.text(x + w / 2, y + h / 2, label, transform=ax.transAxes,
            ha="center", va="center", fontsize=5.3, fontweight="bold",
            color=provisional_color if is_provisional else "white", zorder=6)


def _draw_sources(ax):
    _panel(ax, x=0.030, y=0.825, w=0.665, h=0.145, title="Generated sets",
           facecolor="#F3F7FA")
    ax.text(0.680, 0.945, "* ongoing; not yet in downstream analyses",
            transform=ax.transAxes, ha="right", va="center", fontsize=5.3,
            color="#7A6260", fontstyle="italic", zorder=6)
    accents = ("#7890A1", "#8CA078", "#C99A65", "#A66D68", "#718A99")
    gap = 0.009
    card_w = (0.637 - 4 * gap) / 5
    for index, ((model, cohorts), accent) in enumerate(zip(MODEL_GROUPS, accents)):
        x = 0.044 + index * (card_w + gap)
        _box(ax, x=x, y=0.839, w=card_w, h=0.088, facecolor="#FFFFFF",
             edgecolor="#BFCBD3", linewidth=0.78, radius=0.006)
        _box(ax, x=x, y=0.839, w=0.006, h=0.088, facecolor=accent,
             edgecolor=accent, linewidth=0, radius=0.003, zorder=3)
        ax.text(x + 0.017, 0.898, model, transform=ax.transAxes, ha="left",
                va="center", fontsize=6.1, fontweight="bold",
                color=ANALYSIS_V2_DARK_TEXT, zorder=6)
        chip_gap = 0.006
        chip_w = (card_w - 0.020 - chip_gap * (len(cohorts) - 1)) / len(cohorts)
        for chip_index, (label, cohort) in enumerate(cohorts):
            _chip(ax, x=x + 0.012 + chip_index * (chip_w + chip_gap), y=0.848,
                  w=chip_w, h=0.021, label=label,
                  facecolor=MODEL_VARIANT_COLORS[cohort],
                  provisional_color=PROVISIONAL_VARIANTS.get(cohort))

    _panel(ax, x=0.715, y=0.825, w=0.255, h=0.145, title="Reference data",
           facecolor="#F5F1F8", edgecolor="#D8CDDF")
    _card(ax, x=0.729, y=0.881, w=0.095, h=0.041, title="MAGNDATA",
          icon="database", accent="#79698D", title_size=6.1)
    _card(ax, x=0.832, y=0.881, w=0.124, h=0.041,
          title="Materials Project\nreference structures", icon="database",
          accent="#79698D", title_size=5.7)
    ax.text(0.729, 0.865, "Reference branches", transform=ax.transAxes,
            ha="left", va="center", fontsize=5.6, fontweight="bold",
            color="#6F6677", zorder=6)
    gap = 0.006
    chip_w = (0.227 - 4 * gap) / 5
    for index, label in enumerate(REFERENCE_BRANCHES):
        _chip(ax, x=0.729 + index * (chip_w + gap), y=0.834, w=chip_w,
              h=0.020, label=label,
              facecolor="#76658A" if label == "MAGNDATA" else "#9489A0")
    generated_center = 0.030 + 0.665 / 2
    ax.plot([generated_center], [0.825], marker="o", markersize=2.8,
            transform=ax.transAxes, color="#52697B", zorder=7)
    return generated_center, 0.735


def _draw_spine(ax, generated_center):
    center = 0.405
    _box(ax, x=0.190, y=0.495, w=0.430, h=0.300, facecolor="#F5F8FA",
         edgecolor="#E1E7EB", linewidth=0.6, radius=0.014, zorder=0)
    ax.text(center, 0.779, "Generated-data workflow", transform=ax.transAxes,
            ha="center", va="center", fontsize=9.2, fontweight="bold",
            color=ANALYSIS_V2_DARK_TEXT, zorder=6)
    _orthogonal_down_arrow(
        ax, x0=generated_center, y0=0.825, x1=center, y1=0.795,
        elbow_y=0.808, color="#52697B", linewidth=1.05,
    )
    stages = (
        (0.708, "Generated structures / native outputs", "generator-specific representations",
         "document", "#E8F0F5", "#587488"),
        (0.640, "CIF harmonization", "common structure representation",
         "gear", "#E8F0F5", "#587488"),
        (0.572, "Structural quality control", "validity, geometry, composition",
         "qc", "#FAEDC9", "#A27B32"),
        (0.502, "Retained structures for downstream analysis", None,
         "crystal", "#E3EEDC", "#5F7C52"),
    )
    node_x, node_w, node_h = 0.220, 0.370, 0.052
    for index, (y, title, note, icon, color, accent) in enumerate(stages):
        _card(ax, x=node_x, y=y, w=node_w, h=node_h, title=title, note=note,
              icon=icon, accent=accent, facecolor=color, title_size=6.8,
              note_size=5.2)
        if index:
            _arrow(ax, x0=center, y0=stages[index - 1][0],
                   x1=center, y1=y + node_h, linewidth=0.9)
    return center, stages[-1][0]


def _branch_panel(ax, *, x, y, w, h, title, facecolor, accent):
    _panel(ax, x=x, y=y, w=w, h=h, title=title, facecolor=facecolor,
           edgecolor=accent, title_color=accent, title_size=7.5)


def _draw_branches(ax, retained_center, retained_y, reference_center):
    y, h = 0.282, 0.180
    property_box = (0.025, y, 0.215, h)
    descriptor_box = (0.255, y, 0.300, h)
    screening_box = (0.570, y, 0.200, h)
    dft_box = (0.790, y, 0.180, h)

    _branch_panel(ax, x=property_box[0], y=y, w=property_box[2], h=h,
                  title="Property prediction", facecolor="#EDF5FA", accent="#587C93")
    card_y, card_h = 0.312, 0.098
    _card(ax, x=0.037, y=card_y, w=0.091, h=card_h, title="CHGNet\nenergy",
          note="predicted energy\nper atom", icon="energy", accent="#587C93",
          title_size=6.2, note_size=5.0, icon_position="top")
    _card(ax, x=0.137, y=card_y, w=0.091, h=card_h,
          title="DXMag magnetic\nmoment", note="composition-based\npredicted moment",
          icon="spin", accent="#587C93", title_size=5.9, note_size=4.8,
          icon_position="top")

    _branch_panel(ax, x=descriptor_box[0], y=y, w=descriptor_box[2], h=h,
                  title="Magnetic descriptors", facecolor="#EEF6EE", accent="#668262")
    descriptor_cards = (
        ("Composition", "3d, selected 4d/5d,\nlanthanides", "atoms"),
        ("Local magnetic\ngeometry", "coordination and\nneighbor distances", "geometry"),
        ("Symmetry", "magnetic-site and\ncrystallographic symmetry", "symmetry"),
    )
    for index, (title, note, icon) in enumerate(descriptor_cards):
        _card(ax, x=0.267 + index * 0.096, y=card_y, w=0.087, h=card_h,
              title=title, note=note, icon=icon, accent="#668262",
              title_size=5.8, note_size=4.6, icon_position="top")

    _branch_panel(ax, x=screening_box[0], y=y, w=screening_box[2], h=h,
                  title="Reference-space screening", facecolor="#FAEFF0",
                  accent="#9A666B")
    screen_cards = (
        ("Descriptor\nconstruction", "features"),
        ("kNN\ndistances", "knn"),
        ("$C_{\\mathrm{mag-NM}}$\nscoring", "contrast"),
    )
    screen_xs = (0.581, 0.644, 0.707)
    for index, ((title, icon), card_x) in enumerate(zip(screen_cards, screen_xs)):
        note = "magnetic-reference\ncontrast" if index == 2 else None
        _card(ax, x=card_x, y=card_y, w=0.052, h=card_h, title=title, note=note,
              icon=icon, accent="#9A666B", title_size=5.0, note_size=4.1,
              icon_position="top")
        if index:
            _arrow(ax, x0=screen_xs[index - 1] + 0.052, y0=card_y + card_h / 2,
                   x1=card_x, y1=card_y + card_h / 2, color="#9A666B",
                   linewidth=0.75)

    _branch_panel(ax, x=dft_box[0], y=y, w=dft_box[2], h=h,
                  title="Candidate-level DFT validation", facecolor="#F1F4F6",
                  accent="#677783")
    dft_stages = (
        (0.392, "Selected candidates"),
        (0.343, "DFT calculations"),
        (0.294, "DFT validation"),
    )
    dft_icons = ("candidate", "monitor", "clipboard")
    for index, (card_y_dft, title) in enumerate(dft_stages):
        _card(ax, x=0.812, y=card_y_dft, w=0.136, h=0.035, title=title,
              icon=dft_icons[index], accent="#677783",
              title_size=5.7)
        if index:
            _arrow(ax, x0=0.880, y0=dft_stages[index - 1][0],
                   x1=0.880, y1=card_y_dft + 0.035, color="#677783",
                   linewidth=0.75)

    branch_centers = (0.1325, 0.405, 0.670)
    branch_entry_xs = (0.1325, 0.430, 0.670)
    bus_y = 0.477
    _arrow(ax, x0=retained_center, y0=retained_y, x1=retained_center, y1=bus_y)
    _line(ax, x0=branch_entry_xs[0], y0=bus_y,
          x1=branch_entry_xs[-1], y1=bus_y)
    for entry_x in branch_entry_xs:
        _arrow(ax, x0=entry_x, y0=bus_y, x1=entry_x, y1=y + h)

    _arrow(ax, x0=reference_center, y0=0.825, x1=reference_center, y1=y + h,
           color="#79698D", linewidth=1.0)

    score_right = 0.759
    score_y = card_y + card_h / 2
    selected_y = dft_stages[0][0] + 0.035 / 2
    route_x = 0.780
    _line(ax, x0=score_right, y0=score_y, x1=route_x, y1=score_y,
          color="#677783")
    _line(ax, x0=route_x, y0=score_y, x1=route_x, y1=selected_y,
          color="#677783")
    _arrow(ax, x0=route_x, y0=selected_y, x1=0.812, y1=selected_y,
           color="#677783")
    return branch_centers


def _draw_integrated_outputs(ax, branch_centers):
    _panel(ax, x=0.030, y=0.035, w=0.940, h=0.190,
           title="Integrated population-level analyses", facecolor="#F1F5F7",
           edgecolor="#CBD7DE", title_size=9.0)
    bus_y = 0.248
    for center in branch_centers:
        _line(ax, x0=center, y0=0.282, x1=center, y1=bus_y)
    _line(ax, x0=branch_centers[0], y0=bus_y,
          x1=branch_centers[-1], y1=bus_y)
    merge_x = 0.475
    _arrow(ax, x0=merge_x, y0=bus_y, x1=merge_x, y1=0.225)

    outputs = (
        ("Structural retention\nand rejection profiles", "bars", "#A27B32", "#F8EDD0"),
        ("Magnetic-domain composition\nand local environments", "magnetic", "#668262", "#EEF6EE"),
        ("Reference-space\nenrichment", "target", "#9A666B", "#FAEFF0"),
        ("Descriptor-space PCA", "pca", "#668262", "#EEF6EE"),
        ("Energy-magnetism\nlandscape", "landscape", "#587C93", "#EDF5FA"),
        ("Chemical composition\nand diversity", "pie", "#718A99", "#F3F7FA"),
    )
    gap = 0.011
    card_w = (0.910 - 5 * gap) / 6
    for index, (title, icon, accent, color) in enumerate(outputs):
        x = 0.045 + index * (card_w + gap)
        _card(ax, x=x, y=0.064, w=card_w, h=0.102, title=title, icon=icon,
              accent=accent, facecolor=color, title_size=6.0,
              icon_position="top", icon_size=0.015)


def save_paper_pipeline_figure_v3(
    *, output_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> FigureExportPaths:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_analysis_v2_publication_style()
    fig, ax = plt.subplots(figsize=(16.0, 9.6))
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    generated_center, reference_center = _draw_sources(ax)
    retained_center, retained_y = _draw_spine(ax, generated_center)
    branch_centers = _draw_branches(
        ax, retained_center, retained_y, reference_center,
    )
    _draw_integrated_outputs(ax, branch_centers)

    paths = save_analysis_v2_figure_bundle(fig, output_dir, FIGURE_BASENAME)
    plt.close(fig)
    return paths


def run_paper_pipeline_figure_v3(
    *, figure_dir: str | Path = ANALYSIS_V2_FIGURE_OUTPUT_DIR,
) -> PaperPipelineFigureV3Report:
    if tuple(ANALYSIS_V2_MAGNETIC_COHORT_ORDER) != EXPECTED_COHORTS:
        raise RuntimeError(
            "Analysis v2 cohort order differs from paper pipeline v3 contract"
        )
    return PaperPipelineFigureV3Report(
        figure_paths=save_paper_pipeline_figure_v3(output_dir=figure_dir)
    )
