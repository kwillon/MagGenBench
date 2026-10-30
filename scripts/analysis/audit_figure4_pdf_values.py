"""Read back ORIGINAL vector geometry for verification, never for plot inputs.

Requires PyMuPDF; can run in the separate document-QA environment. Original
data from CSVs remain authoritative. PDF coordinates have limited precision.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pymupdf

ORDER = ["mattergen_base", "mattergen_finetuned", "concdvae_base", "concdvae_finetuned",
         "crysjepa_base", "crysjepa_refined", "crystalformer", "crystalformer_finetuned",
         "crystalllm", "crystalllm_finetuned"]
DFT_ORDER = ["mattergen_base", "concdvae_base", "crystalformer", "crystalllm"]
BRANCH_COLORS = {"AFM": "#D6A64F", "FM": "#5F7F57", "FiM": "#A65A73"}


def compare(output):
    page = pymupdf.open(output / "original/fig04_magnetic_reference_dft.pdf")[0]
    drawings = page.get_drawings()
    frames = [d["rect"] for d in drawings if d["fill"] == (1., 1., 1.)
              and d["rect"].width > 200 and d["rect"].height > 200
              and d["rect"].width < page.rect.width*.8]
    frames.sort(key=lambda r: (round(r.y0), r.x0))
    if len(frames) != 4:
        raise ValueError("Original PDF does not have the expected four axes frames")
    stat = pd.read_csv(output / "audit/figure_statistics.csv").set_index("dataset")
    dft = pd.read_csv(output / "audit/dft_confirmation_verified.csv").set_index("dataset")
    records = []

    def record(panel, dataset, metric, original, restored, tolerance=3e-6):
        records.append({"panel": panel, "dataset": dataset, "metric": metric,
                        "original_pdf_readback": original, "reproduced": restored,
                        "difference": restored-original,
                        "matches_pdf_precision": abs(restored-original) <= tolerance})

    for panel, frame, order, table, value_name in (
        ("A", frames[0], ORDER, stat, "fraction_magnetic_like"),
        ("D", frames[3], DFT_ORDER, dft, "dft_confirmation_fraction"),
    ):
        bars = [d for d in drawings if d["fill"] is not None and d["fill"] != (1., 1., 1.)
                and len(d["items"]) == 1 and d["items"][0][0] == "re"
                and abs(d["rect"].x0-frame.x0) < .01 and frame.contains(d["rect"])]
        bars.sort(key=lambda d: d["rect"].y0)
        errors = [d for d in drawings if d["type"] == "s" and d["color"] is not None
                  and abs(d["color"][0]-.2) < .01 and d["rect"].height < .01
                  and frame.contains(d["rect"]) and d["rect"].width > .001]
        errors.sort(key=lambda d: d["rect"].y0)
        if len(bars) != len(order) or len(errors) != len(order):
            raise ValueError(f"Unexpected original {panel} bar/interval count")
        for ds, bar, interval in zip(order, bars, errors):
            record(panel, ds, value_name, bar["rect"].width/frame.width*1.025, table.loc[ds, value_name])
            fields = ("fmag_ci_low", "fmag_ci_high") if panel == "A" else ("ci95_low", "ci95_high")
            for field, x in zip(fields, (interval["rect"].x0, interval["rect"].x1)):
                record(panel, ds, field, (x-frame.x0)/frame.width*1.025, table.loc[ds, field])

    frame = frames[1]
    ticks = []
    for word in page.get_text("words"):
        if frame.x0 <= word[0] < frame.x1 and frame.y1 < word[1] < frame.y1+15:
            try:
                ticks.append((float(word[4].replace("−", "-")), (word[0]+word[2])/2))
            except ValueError:
                pass
    ticks.sort()
    tick_markers = sorted(d["rect"].x0 for d in drawings
                          if frame.x0 <= d["rect"].x0 <= frame.x1
                          and abs(d["rect"].y0-frame.y1) < .01
                          and d["rect"].width < .001 and 2 < d["rect"].height < 6)
    if len(tick_markers) != len(ticks) or len(ticks) < 2:
        raise ValueError("Cannot match original numeric ticks to their vector markers")
    slope, intercept = np.polyfit([v for v, x in ticks], tick_markers, 1)
    # Glyph bounding boxes are not exact tick anchors. Use the actual vector
    # x=0 reference line for the offset, not the text glyph's bounding box.
    zero_lines = [d for d in drawings if d["type"] == "s" and d["color"] is not None
                  and np.allclose(d["color"], [96/255]*3, atol=1e-4)
                  and d["rect"].width < .001 and d["rect"].height > .9*frame.height
                  and frame.contains(d["rect"])]
    if len(zero_lines) != 1:
        raise ValueError("Cannot calibrate original contrast axis from its x=0 vector line")
    intercept = zero_lines[0]["rect"].x0
    for width, fields in ((2.2, ("contrast_q05", "contrast_q95")),
                          (8., ("contrast_q25", "contrast_q75")),
                          (1.7, ("contrast_q50",))):
        lines = [d for d in drawings if d["type"] == "s" and abs(d["width"]-width) < .01
                 and frame.contains(d["rect"])]
        lines.sort(key=lambda d: (d["rect"].y0+d["rect"].y1)/2)
        if len(lines) != 10:
            raise ValueError(f"Unexpected B distribution artist count: {width}, {len(lines)}")
        for ds, line in zip(ORDER, lines):
            values = (line["rect"].x0,) if len(fields) == 1 else (line["rect"].x0, line["rect"].x1)
            for field, x in zip(fields, values):
                record("B", ds, field, (x-intercept)/slope, stat.loc[ds, field], tolerance=5e-6)

    frame = frames[2]
    for branch, color in BRANCH_COLORS.items():
        rgb = tuple(int(color[i:i+2], 16)/255 for i in (1, 3, 5))
        bars = [d for d in drawings if d["fill"] is not None
                and np.allclose(d["fill"], rgb, atol=1e-5)
                and (d["items"][0][0] == "re" or d["rect"].height == 0)
                and frame.x0-.01 <= d["rect"].x0 <= d["rect"].x1 <= frame.x1+.01
                and frame.y0-.01 <= d["rect"].y0 <= d["rect"].y1 <= frame.y1+.01]
        bars.sort(key=lambda d: d["rect"].x0)
        if len(bars) != 10:
            raise ValueError(f"Unexpected original C segment count for {branch}: {len(bars)}")
        for ds, bar in zip(ORDER, bars):
            record("C", ds, f"branch_{branch}", bar["rect"].height/frame.height,
                   stat.loc[ds, f"branch_{branch}"])
    result = pd.DataFrame(records)
    result.to_csv(output / "audit/original_pdf_vs_reproduced.csv", index=False)
    print(result.groupby("panel").agg(values=("metric", "size"),
                                       matches=("matches_pdf_precision", "sum"),
                                       max_abs_difference=("difference", lambda s: s.abs().max())).to_string())
    if not result.matches_pdf_precision.all():
        print(result.loc[~result.matches_pdf_precision].to_string(index=False))
        raise RuntimeError("Original PDF differs from reproduced statistics; report written before styling")
    print("PASS: original vector readback matches all reproduced plotted statistics within PDF precision")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reproduced/fig04_mp_only"))
    compare(parser.parse_args().output)
