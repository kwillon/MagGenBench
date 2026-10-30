"""Restyle ORIGINAL PDF vector panels, without substituting recalculated values.

The original PDF remains untouched. Only text/color operators are replaced in
an in-memory source; all original path coordinates and statistics are retained
inside Form XObjects. Panel C is rotated clockwise as a whole.
"""
import ast
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

import matplotlib
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reproduced/fig04_mp_only/final_design"
SOURCE = ROOT / "reproduced/fig04_mp_only/original/fig04_magnetic_reference_dft.pdf"
ORIGINAL_SHA256 = "9ef54af2e79915c2ace5fbde91e7abb10b61187844c4ac78e50d2c7c55881105"
BASELINE = "907d98ffca4f04a9db46363251db8fdd284bbcca"
FONT_DIR = Path(matplotlib.get_data_path()) / "fonts/ttf"
FAMILIES = ["MatterGen", "Con-CDVAE", "Crys-JEPA", "CrystalFormer", "CrystaLLM"]
LABELS = [name + " " + variant for name in FAMILIES for variant in
          (("Base", "Refined") if name == "Crys-JEPA" else ("Base", "FT"))]


def constants(path, names):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
            and n.targets[0].id in names}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUT)
    parser.add_argument("--source-from-git", action="store_true",
                        help="Read the pinned original Git blob even if a local control copy exists")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    original_bytes = (SOURCE.read_bytes() if SOURCE.is_file() and not args.source_from_git else
                      subprocess.check_output(["git", "show", BASELINE +
                          ":paper/figures/fig04_magnetic_reference_dft.pdf"], cwd=ROOT))
    source_hash = hashlib.sha256(original_bytes).hexdigest()
    assert source_hash == ORIGINAL_SHA256, "Expected the unchanged original control PDF"
    src = fitz.open(stream=original_bytes, filetype="pdf")
    original = src[0]
    drawings = original.get_drawings()
    frames = sorted([d["rect"] for d in drawings if d["fill"] == (1., 1., 1.)
                     and 200 < d["rect"].width < original.rect.width*.8
                     and d["rect"].height > 200], key=lambda r: (round(r.y0), r.x0))
    assert len(frames) == 4
    families = constants(ROOT / "src/mvpipeline/analysis/publication_style.py", {"GENERATOR_COLORS"})["GENERATOR_COLORS"]
    old_colors = constants(ROOT / "filter/scripts/plot_mp_only_publication.py", {"GENERATOR_COLORS"})["GENERATOR_COLORS"]
    color_map = {}
    for i, (_, old) in enumerate(old_colors.items()):
        color_map[tuple(round(v, 7) for v in fitz.sRGB_to_pdf(int(old[1:], 16)))] = fitz.sRGB_to_pdf(int(families[FAMILIES[i//2]][1:], 16))
    contents = b"\n".join(src.xref_stream(x) for x in original.get_contents())
    # Text is replaced outside the statistics frames. No path, clipping,
    # coordinate, line-width, dash or graphics-state operator is edited.
    text_free = re.sub(rb"BT\b.*?\bET", b"", contents, flags=re.S)
    rgb_pattern = rb"([-+\d.]+) ([-+\d.]+) ([-+\d.]+) (rg|RG)\b"

    def recolor(match):
        rgb = tuple(round(float(match[i]), 7) for i in (1, 2, 3))
        if rgb not in color_map:
            return match[0]
        return (" ".join(f"{v:.10f}" for v in color_map[rgb]) + " " + match[4].decode()).encode()

    recolored = re.sub(rgb_pattern, recolor, text_free)
    # Prove all non-color/text PDF operators remain byte-for-byte the same.
    assert re.sub(rgb_pattern, b"RGB", recolored) == re.sub(rgb_pattern, b"RGB", text_free)
    xref = src.get_new_xref()
    src.update_object(xref, "<<>>")
    src.update_stream(xref, recolored)
    original.set_contents(xref)

    def bars(frame):
        return sorted([d["rect"] for d in drawings if d["fill"] is not None
                       and d["fill"] != (1., 1., 1.) and len(d["items"]) == 1
                       and d["items"][0][0] == "re" and frame.contains(d["rect"])
                       and abs(d["rect"].x0-frame.x0) < .01], key=lambda r: r.y0)

    a_bars = bars(frames[0])
    d_bars = bars(frames[3])
    assert len(a_bars) == 10 and len(d_bars) == 4
    row_y = [(r.y0+r.y1)/2 for r in a_bars]
    iqrs = sorted([d["rect"] for d in drawings if d["type"] == "s"
                   and abs(d["width"]-8) < .01 and frames[1].contains(d["rect"])], key=lambda r:r.y0)
    medians = sorted([d["rect"] for d in drawings if d["type"] == "s"
                      and abs(d["width"]-1.7) < .01 and frames[1].contains(d["rect"])], key=lambda r:r.y0)
    assert len(iqrs) == len(medians) == 10

    def hatch(page, rect, spacing=6, width=.55):
        # Clip each decorative hatch segment explicitly to the original bar.
        if rect.width <= 0 or rect.height <= 0:
            return
        start = rect.x0-rect.height
        while start < rect.x1:
            xa, xb = max(rect.x0, start), min(rect.x1, start+rect.height)
            if xb > xa:
                page.draw_line((xa, rect.y1-(xa-start)), (xb, rect.y1-(xb-start)),
                               color=(.14,.19,.23), width=width)
            start += spacing

    for j in range(1, 10, 2):
        hatch(original, a_bars[j])
        r = iqrs[j]
        hatch(original, fitz.Rect(r.x0, r.y0-4, r.x1, r.y0+4), spacing=5)
        mid = medians[j]
        x, y = mid.x0, (mid.y0+mid.y1)/2
        original.draw_polyline([(x,y-3),(x+3,y),(x,y+3),(x-3,y),(x,y-3)],
                               color=(.14,.19,.23), fill=(1,1,1), width=.7)

    # Panel C class colors remain unchanged. Hatch only adapted cohort bars.
    c_rects = [d["rect"] for d in drawings if d["fill"] is not None
               and d["fill"] != (1.,1.,1.) and frames[2].contains(d["rect"])
               and d["rect"].width > 1 and d["rect"].height > 0]
    c_centers = sorted(set(round((r.x0+r.x1)/2, 4) for r in c_rects))
    assert len(c_centers) == 10
    for j in range(1, 10, 2):
        for r in c_rects:
            if abs((r.x0+r.x1)/2-c_centers[j]) < .01:
                hatch(original, r, spacing=11, width=.45)

    doc = fitz.open()
    page = doc.new_page(width=1152, height=660)
    page.insert_font(fontname="Design", fontfile=str(FONT_DIR / "DejaVuSans.ttf"))
    page.insert_font(fontname="DesignBold", fontfile=str(FONT_DIR / "DejaVuSans-Bold.ttf"))
    regular = fitz.Font(fontfile=str(FONT_DIR / "DejaVuSans.ttf"))
    bold = fitz.Font(fontfile=str(FONT_DIR / "DejaVuSans-Bold.ttf"))

    def text(x, y, string, size=14, align="left", weight=False):
        font = bold if weight else regular
        width = font.text_length(string, fontsize=size)
        if align == "right": x -= width
        if align == "center": x -= width/2
        page.insert_text((x,y), string, fontsize=size, fontname="DesignBold" if weight else "Design",
                         color=(.12,.17,.21))

    targets = [fitz.Rect(152,83,565,308), fitz.Rect(729,83,1152-12,308),
               fitz.Rect(152,392,565,617), fitz.Rect(729,392,1152-12,617)]
    matrices = []
    for i, (frame, target) in enumerate(zip(frames, targets)):
        page.show_pdf_page(target, src, 0, clip=frame, keep_proportion=False,
                           rotate=-90 if i == 2 else 0)
        matrices.append({"source":list(frame), "target":list(target), "rotation":-90 if i==2 else 0})
        text(target.x0, target.y0-14, ["A  Magnetic-like candidates", "B  Magnetic-reference contrast",
             "C  Magnetic classes", "D  DFT confirmation: Base groups"][i], size=16.5, weight=True)

    # Category anchors come from original vector bar centers, not inferred scores.
    for i in (0, 1):
        for y, label in zip(row_y, LABELS):
            mapped = targets[i].y0 + (y-frames[i].y0)/frames[i].height*targets[i].height
            text(targets[i].x0-7, mapped+4, label, size=14, align="right")
    for x, label in zip(c_centers, LABELS):
        mapped = targets[2].y0 + (x-frames[2].x0)/frames[2].width*targets[2].height
        text(targets[2].x0-7, mapped+4, label, size=14, align="right")
    for r, label in zip(d_bars, [LABELS[i] for i in (0,2,6,8)]):
        mapped = targets[3].y0 + ((r.y0+r.y1)/2-frames[3].y0)/frames[3].height*targets[3].height
        text(targets[3].x0-7, mapped+4, label, size=14, align="right")
    for i in (0,2,3):
        target = targets[i]
        for j in range(6):
            value = j/5
            x = target.x0+value/(1.025 if i!=2 else 1)*target.width
            text(x, target.y1+18, f"{value:.1f}", size=13.5, align="center")
    # Contrast ticks retain original vector tick anchors and numeric labels.
    frame = frames[1]
    for word in fitz.open(stream=original_bytes, filetype="pdf")[0].get_text("words"):
        if frame.x0 <= word[0] < frame.x1 and frame.y1 < word[1] < frame.y1+15:
            try: value = float(word[4].replace("−","-"))
            except ValueError: continue
            ticks = [d["rect"].x0 for d in drawings if abs(d["rect"].y0-frame.y1)<.01
                     and d["rect"].width<.001 and 2<d["rect"].height<6 and frame.x0<=d["rect"].x0<=frame.x1]
            anchor = min(ticks, key=lambda x: abs(x-(word[0]+word[2])/2))
            x = targets[1].x0+(anchor-frame.x0)/frame.width*targets[1].width
            text(x, targets[1].y1+18, f"{value:g}", size=13.5, align="center")
    for i, label in enumerate(["Fraction closer to magnetic than NM reference",
        "Contrast: d(NM) - d(magnetic)", "Fraction among magnetic-like candidates",
        "Fraction confirmed magnetic by DFT (Wilson 95% CI)"]):
        text((targets[i].x0+targets[i].x1)/2, targets[i].y1+38, label, size=14, align="center")
    # Compact shared style key; panel C has an independent class color legend.
    def key(x,y,color,label,hatched=False):
        r=fitz.Rect(x,y-9,x+18,y)
        page.draw_rect(r,color=(.14,.19,.23),fill=color,width=.45)
        if hatched: hatch(page,r,spacing=5)
        text(x+24,y,label,size=12.5)
    key(245,28,(.75,.78,.8),"Base")
    key(330,28,(.75,.78,.8),"Fine-tuned / Refined",True)
    text(540,28,"A: formula-cluster bootstrap 95% CI",size=12.5)
    for x, color, label in [(350,"D6A64F","AFM"),(425,"5F7F57","FM"),(490,"A65A73","FiM")]:
        key(x, targets[2].y0-13, fitz.sRGB_to_pdf(int(color,16)), label)
    target_path=output / "fig04_magnetic_reference_dft_original_values_design.pdf"
    doc.subset_fonts()
    doc.save(target_path,garbage=4,deflate=True)
    if SOURCE.is_file():
        assert SOURCE.read_bytes()==original_bytes
    saved=fitz.open(target_path)
    p=saved[0]
    assert len(p.get_images())==0
    # The original geometry stream must actually survive inside the exported
    # Form XObject, not merely pass the pre-export assertion.
    assert any(recolored in (saved.xref_stream(x) or b"")
               for x in range(1,saved.xref_length()) if saved.xref_is_stream(x))
    spans=[s for block in p.get_text("dict")["blocks"] if "lines" in block
           for line in block["lines"] for s in line["spans"]]
    assert all(p.rect.contains(fitz.Rect(s["bbox"])) for s in spans)
    # Check each original statistical artist after the actual panel transforms:
    # A 10 bars + 10 CIs, B 30 lines, C 30 segments, D 4 bars + 4 CIs.
    output_rects=[d["rect"] for d in p.get_drawings()]
    checks=[]
    a_ci_right_margins=[]
    for i, frame in enumerate(frames):
        if i in (0,3):
            selected=bars(frame)+[d["rect"] for d in drawings if d["type"]=="s"
                and d["color"] is not None and abs(d["color"][0]-.2)<.01
                and d["rect"].height<.01 and frame.contains(d["rect"])
                and d["rect"].width>.001]
        elif i==1:
            selected=[d["rect"] for d in drawings if d["type"]=="s"
                      and any(abs(d["width"]-w)<.01 for w in (2.2,8.,1.7))
                      and frame.contains(d["rect"])]
        else:
            class_rgb=[fitz.sRGB_to_pdf(int(h,16)) for h in ("D6A64F","5F7F57","A65A73")]
            selected=[d["rect"] for d in drawings if d["fill"] is not None
                and any(max(abs(a-b) for a,b in zip(d["fill"],rgb))<1e-5 for rgb in class_rgb)
                and frame.x0-.01<=d["rect"].x0<=d["rect"].x1<=frame.x1+.01
                and frame.y0-.01<=d["rect"].y0<=d["rect"].y1<=frame.y1+.01]
        assert len(selected)==(20,30,30,8)[i]
        if i==0:
            a_ci_right_margins=[frame.x1-r.x1 for r in selected[10:]]
            assert min(a_ci_right_margins)>.5, "CI near 1.0 would touch the panel clip boundary"
        target=targets[i]
        actual_frame=min([d["rect"] for d in p.get_drawings() if d["fill"]==(1.,1.,1.)],
                         key=lambda r:max(abs(a-b) for a,b in zip(target,r)))
        def point(x,y):
            if i==2:
                return (target.x0+(frame.y1-y)/frame.height*target.width,
                        target.y0+(x-frame.x0)/frame.width*target.height)
            return (target.x0+(x-frame.x0)/frame.width*target.width,
                    target.y0+(y-frame.y0)/frame.height*target.height)
        for rect in selected:
            corners=[point(rect.x0,rect.y0),point(rect.x1,rect.y1)]
            expected=(min(x[0] for x in corners),min(x[1] for x in corners),
                      max(x[0] for x in corners),max(x[1] for x in corners))
            matched=min(output_rects,key=lambda r:max(abs(a-b) for a,b in zip(expected,r)))
            error=max(abs(a-b) for a,b in zip(expected,matched))
            # Form matrices are serialized at finite PDF precision. 0.02 pt
            # bounds that display-coordinate rounding; source paths are exact.
            assert error<.02, (i,expected,error)
            normalized_expected=((expected[0]-target.x0)/target.width,
                                 (expected[1]-target.y0)/target.height,
                                 (expected[2]-target.x0)/target.width,
                                 (expected[3]-target.y0)/target.height)
            normalized_actual=((matched.x0-actual_frame.x0)/actual_frame.width,
                               (matched.y0-actual_frame.y0)/actual_frame.height,
                               (matched.x1-actual_frame.x0)/actual_frame.width,
                               (matched.y1-actual_frame.y0)/actual_frame.height)
            relative_error=max(abs(a-b) for a,b in zip(normalized_expected,normalized_actual))
            assert relative_error<1e-6, (i,relative_error)
            checks.append({"panel":"ABCD"[i],"original_rect":list(rect),
                           "expected_output_rect":expected,"max_error_pt":error,
                           "max_axis_relative_error":relative_error})
    p.get_pixmap(matrix=fitz.Matrix(2,2)).save(str(target_path.with_suffix(".png")))
    (output/"original_vector_design_audit.json").write_text(json.dumps({
        "source_sha256":source_hash, "source_path":str(SOURCE.relative_to(ROOT)),
        "output_sha256":hashlib.sha256(target_path.read_bytes()).hexdigest(),
        "original_path_operators_unchanged":True, "statistics_recomputed":False,
        "source_text_removed_and_colors_replaced_only":True,
        "panel_transforms":matrices, "panel_C_rotation":"clockwise, original stack geometry retained",
        "nine_recalculation_differences_imported":False,
        "original_geometry_stream_verified_inside_output":True,
        "text_outside_page":0, "embedded_images":0,
        "statistical_artists_verified":len(checks), "plotted_scalar_values_preserved":122,
        "max_artist_coordinate_error_pt":max(c["max_error_pt"] for c in checks),
        "max_axis_relative_coordinate_error":max(c["max_axis_relative_error"] for c in checks),
        "minimum_A_CI_margin_to_right_clip_source_pt":min(a_ci_right_margins),
        "artist_checks":checks,
        "original_stream_geometry_sha256":hashlib.sha256(re.sub(rgb_pattern,b"RGB",text_free)).hexdigest(),
    },indent=2),encoding="utf-8")
    print(target_path)


if __name__=="__main__":
    main()
