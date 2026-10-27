from __future__ import annotations

from pathlib import Path

import fitz
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OLD_PDF = ROOT / "paper" / "figures" / "fig06_diversity_adaptation.pdf"
PREVIEW_PDF = (
    ROOT
    / "reproduced"
    / "figure6"
    / "fig06_diversity_adaptation_palette_preview.pdf"
)
OUTPUT_PDF = (
    ROOT
    / "paper"
    / "figures"
    / "fig06_diversity_adaptation_updated.pdf"
)
PREVIEW_PNG = (
    ROOT
    / "reproduced"
    / "figure6"
    / "fig06_diversity_adaptation_updated_preview.png"
)
BOUNDARY_Y = 626.0


def _inspect_boundary(page: fitz.Page) -> float:
    """Print text blocks near the expected B/C boundary and return its y coordinate."""
    blocks = page.get_text("blocks")
    nearby = sorted(
        (
            float(block[1]),
            float(block[3]),
            str(block[4]).strip().replace("\n", " "),
        )
        for block in blocks
        if float(block[1]) < BOUNDARY_Y + 90
        and float(block[3]) > BOUNDARY_Y - 90
    )
    print("text blocks near B/C boundary:")
    for top, bottom, text in nearby:
        print(f"  y={top:.2f}..{bottom:.2f}: {text[:120]}")
    return BOUNDARY_Y


def _fit_rect(source: fitz.Rect, target: fitz.Rect) -> fitz.Rect:
    """Return an aspect-preserving, centered placement inside target."""
    scale = min(target.width / source.width, target.height / source.height)
    width = source.width * scale
    height = source.height * scale
    x0 = target.x0 + (target.width - width) / 2
    y0 = target.y0 + (target.height - height) / 2
    return fitz.Rect(x0, y0, x0 + width, y0 + height)


def _render(page: fitz.Page, scale: float = 2.0) -> np.ndarray:
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    return np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
        pixmap.height,
        pixmap.width,
        pixmap.n,
    )


def merge_top_half() -> None:
    if not OLD_PDF.is_file():
        raise FileNotFoundError(OLD_PDF)
    if not PREVIEW_PDF.is_file():
        raise FileNotFoundError(PREVIEW_PDF)

    old = fitz.open(OLD_PDF)
    preview = fitz.open(PREVIEW_PDF)
    result = fitz.open()

    try:
        old_page = old[0]
        preview_page = preview[0]
        old_rect = old_page.rect
        preview_rect = preview_page.rect

        print(f"old page size: {old_rect.width:.3f} x {old_rect.height:.3f} pt")
        print(
            "preview page size: "
            f"{preview_rect.width:.3f} x {preview_rect.height:.3f} pt"
        )

        boundary_y = _inspect_boundary(old_page)
        if not 0 < boundary_y < old_rect.height:
            raise RuntimeError(f"Invalid B/C boundary: {boundary_y}")

        top_area = fitz.Rect(
            0,
            0,
            old_rect.width,
            boundary_y,
        )
        old_bottom = fitz.Rect(
            0,
            boundary_y,
            old_rect.width,
            old_rect.height,
        )
        preview_page_rect = preview_page.rect
        preview_placement = _fit_rect(preview_page_rect, top_area)

        new_page = result.new_page(
            width=old_rect.width,
            height=old_rect.height,
        )

        # Insert the complete A/B preview page, preserving its aspect ratio.
        new_page.show_pdf_page(preview_placement, preview, 0)
        # The original lower half is copied as PDF content, not rasterized.
        new_page.show_pdf_page(old_bottom, old, 0, clip=old_bottom)

        if old.page_count > 1:
            result.insert_pdf(old, from_page=1, to_page=old.page_count - 1)

        OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
        PREVIEW_PNG.parent.mkdir(parents=True, exist_ok=True)
        result.save(OUTPUT_PDF, garbage=4, deflate=True)

        # This raster is only for visual QA; the delivered PDF remains vector-based.
        qa_page = result[0]
        pixmap = qa_page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        pixmap.save(PREVIEW_PNG)

        old_render = _render(old_page)
        new_render = _render(qa_page)
        boundary_px = round(boundary_y * 2.0)
        lower_old = old_render[boundary_px:]
        lower_new = new_render[boundary_px:]
        if lower_old.shape != lower_new.shape:
            raise RuntimeError(
                "Rendered lower regions have different shapes: "
                f"{lower_old.shape} != {lower_new.shape}"
            )
        difference = np.abs(
            lower_old.astype(np.int16) - lower_new.astype(np.int16)
        )
        print(
            "lower-region render diff: "
            f"max={int(difference.max())}, "
            f"mean={float(difference.mean()):.6f}, "
            f"pixels_gt_2={int(np.count_nonzero(np.max(difference, axis=2) > 2))}"
        )

        if not np.allclose(
            [qa_page.rect.width, qa_page.rect.height],
            [old_rect.width, old_rect.height],
        ):
            raise RuntimeError("Output page size differs from original")

        print(f"output pdf: {OUTPUT_PDF}")
        print(f"preview png: {PREVIEW_PNG}")
        print(f"pages: {result.page_count}")
    finally:
        result.close()
        preview.close()
        old.close()


if __name__ == "__main__":
    merge_top_half()
