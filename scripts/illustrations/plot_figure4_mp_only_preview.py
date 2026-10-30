"""Style frozen MP-only tables; never extract descriptors or publish a PDF."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import matplotlib as mpl
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "reproduced/fig04_mp_only_smact402")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reproduced/fig04_mp_only")
    args = parser.parse_args()
    source = args.source.resolve()
    destination = args.output_dir.resolve()
    plot = module("mp_only_plot", ROOT / "filter/scripts/plot_mp_only_publication.py")
    # Read the same palette source as Figure 3 without importing the main project's dependencies.
    import ast
    palette_tree = ast.parse((ROOT / "src/mvpipeline/analysis/publication_style.py").read_text(encoding="utf-8"))
    constants = {node.targets[0].id: ast.literal_eval(node.value)
                 for node in palette_tree.body if isinstance(node, ast.Assign)
                 and isinstance(node.targets[0], ast.Name)
                 and node.targets[0].id in {"GENERATOR_COLORS", "ADAPTED_HATCH"}}
    stat_path = source / "recalculated_draft/RECALCULATED_figure_statistics.csv"
    dft_path = source / "recalculated_draft/RECALCULATED_dft_confirmation.csv"
    scores = source / "results/mp_only/generator_scores.csv"
    summary_path = source / "results/mp_only/generator_summary.csv"
    protected = [ROOT / "paper/figures" / name for name in (
        "fig03_magnetic_domain.pdf", "legacy/descriptor_space_pca.pdf",
        "fig04_magnetic_reference_dft.pdf", "fig05_energy_magnetism.pdf")]
    inputs = [stat_path, dft_path, scores, summary_path, *protected]
    before = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    summary, _, order = plot.read_data(summary_path, scores, False)
    stat, dft = pd.read_csv(stat_path), pd.read_csv(dft_path)
    # Frozen derived statistics must agree with the already audited summary/DFT join.
    pd.testing.assert_frame_equal(stat[summary.columns], summary, check_exact=True)
    _, verified_dft, _, _ = plot.load_dft(
        source / "results/mp_only/dft_validation/dft_joined_mp_only.csv",
        source / "results/mp_only/dft_validation/dft_validation_audit.json", scores)
    pd.testing.assert_frame_equal(dft, verified_dft, check_exact=False, atol=1e-14, rtol=0)
    assert list(dft.dataset) == list(plot.DFT_ORDER)
    plot.style()
    fig = plot.publication_preview(stat, order, dft, constants["GENERATOR_COLORS"], constants["ADAPTED_HATCH"])
    # Inspect the drawn artists, not just the source tables: presentation may not
    # move a median/endpoint or substitute a population during reordering.
    a, b, c, d = fig.axes
    for axis, values, low, high in (
        (a, stat.fraction_magnetic_like, stat.fmag_ci_low, stat.fmag_ci_high),
        (d, dft.dft_confirmation_fraction, dft.ci95_low, dft.ci95_high),
    ):
        np.testing.assert_array_equal([p.get_width() for p in axis.patches], values)
        np.testing.assert_allclose([seg[:, 0] for seg in axis.collections[0].get_segments()],
                                   np.column_stack([low, high]), rtol=0, atol=1e-15)
    np.testing.assert_array_equal([p.get_x() for p in b.patches], stat.contrast_q25)
    np.testing.assert_allclose([p.get_x()+p.get_width() for p in b.patches], stat.contrast_q75,
                               rtol=0, atol=1e-15)
    np.testing.assert_array_equal([line.get_xdata()[0] for line in b.lines if line.get_marker() in {"o", "D"}],
                                  stat.contrast_q50)
    for j, collection in enumerate(b.collections):
        np.testing.assert_array_equal([seg[0, 0] for seg in collection.get_segments()],
                                      stat.loc[j, ["contrast_q05", "contrast_q95"]].to_numpy())
    # Matplotlib obtains stacked widths by subtracting accumulated endpoints.
    np.testing.assert_allclose([p.get_width() for p in c.patches],
                               stat[["branch_AFM", "branch_FM", "branch_FiM"]].to_numpy().T.ravel(),
                               rtol=0, atol=1e-15)
    for axis in (a, b):
        assert sum(p.get_hatch() == constants["ADAPTED_HATCH"] for p in axis.patches) == 5
        for j in range(0, 10, 2):
            assert axis.patches[j].get_facecolor() == axis.patches[j+1].get_facecolor()
    assert len(fig.axes) == 4 and len(d.patches) == 4 and len(c.patches) == 30
    destination.mkdir(parents=True, exist_ok=True)
    basename = destination / "fig04_magnetic_reference_dft_preview"
    with mpl.rc_context({"savefig.bbox": None}):
        fig.savefig(basename.with_suffix(".pdf"), bbox_inches=None)
        fig.savefig(basename.with_suffix(".png"), bbox_inches=None, dpi=200)
    assert before == {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    (destination / "figure4_preview_provenance.json").write_text(json.dumps({
        "status": "Recalculated preview, not an exact reproduction",
        "input_sha256": before, "statistics_recomputed": False,
        "descriptor_extraction_run": False, "palette": constants,
        "figure_inches": list(fig.get_size_inches()), "panel_count": len(fig.axes),
        "artist_checks": "All A/B/C/D values and interval endpoints match frozen tables; paired colors and hatches verified",
        "dft_datasets": list(dft.dataset), "plotter_sha256": sha(Path(plot.__file__)),
    }, indent=2), encoding="utf-8")
    print(basename.with_suffix(".pdf"))


if __name__ == "__main__":
    main()
