"""Integration check: publication design must retain the pinned original vectors."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import pymupdf as fitz
    import matplotlib
except ImportError as exc:
    raise unittest.SkipTest("Design check requires pymupdf and matplotlib") from exc
ROOT = Path(__file__).resolve().parents[1]


def check_export(tmp_path):
    publication = ROOT / "paper/figures/fig04_magnetic_reference_dft.pdf"
    before = publication.read_bytes()
    subprocess.run([sys.executable, str(ROOT / "scripts/illustrations/restyle_figure4_original_vectors.py"),
                    "--source-from-git", "--output-dir", str(tmp_path)], cwd=ROOT, check=True)
    audit = json.loads((tmp_path / "original_vector_design_audit.json").read_text())
    assert audit["original_geometry_stream_verified_inside_output"]
    assert audit["statistical_artists_verified"] == 88
    assert audit["plotted_scalar_values_preserved"] == 122
    assert audit["max_artist_coordinate_error_pt"] < .02
    assert audit["max_axis_relative_coordinate_error"] < 1e-6
    assert audit["minimum_A_CI_margin_to_right_clip_source_pt"] > .5
    assert not audit["statistics_recomputed"]
    assert not audit["nine_recalculation_differences_imported"]
    exported = tmp_path / "fig04_magnetic_reference_dft_original_values_design.pdf"
    assert hashlib.sha256(exported.read_bytes()).hexdigest() == audit["output_sha256"]
    page = fitz.open(exported)[0]
    assert (page.rect.width, page.rect.height) == (1152, 660)
    assert page.get_images() == []
    assert "line 5-95%" not in page.get_text()
    for text in ("Magnetic-like candidates", "Magnetic-reference contrast",
                 "Magnetic classes", "DFT confirmation: Base groups"):
        assert text in page.get_text()
    assert publication.read_bytes() == before


class OriginalVectorDesignTest(unittest.TestCase):
    def test_export_without_local_reproduction_data(self):
        with tempfile.TemporaryDirectory(prefix="maggenbench-fig04-design-") as directory:
            check_export(Path(directory))
