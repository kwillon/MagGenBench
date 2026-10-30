"""Export a separately labelled RECALCULATION, never the manuscript Figure 4.

This deliberately retains the existing visual style. A publication restyling
must wait for a decision on the documented numerical discrepancies.
"""
import argparse
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reproduced/fig04_mp_only_smact402")
    args = parser.parse_args()
    output = args.output.resolve()
    result = output / "results/mp_only"
    destination = output / "recalculated_draft"
    destination.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("figure4_plot", ROOT / "filter/scripts/plot_mp_only_publication.py")
    plot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plot)
    plot.style()
    summary, scores, order = plot.read_data(result / "generator_summary.csv", result / "generator_scores.csv", False)
    joined, dft, overall, audit = plot.load_dft(result / "dft_validation/dft_joined_mp_only.csv",
                                               result / "dft_validation/dft_validation_audit.json",
                                               result / "generator_scores.csv")
    stat = plot.statistics(summary, scores, order, replicates=1000, seed=42)
    original_save = plot.save

    def save_labelled(fig, path, dpi):
        fig.suptitle("RECALCULATED MP-only results - NOT the original published Figure 4",
                     fontsize=14, fontweight="bold", y=1.035)
        fig.text(.5, 1.0, "Comparison draft: see figure4_reproduction.md for numerical differences",
                 ha="center", va="top", fontsize=11)
        return original_save(fig, destination / "Figure4_RECALCULATED_NOT_ORIGINAL", dpi)

    plot.save = save_labelled
    plot.combined_figure(stat, order, dft, destination, dpi=300)
    stat.to_csv(destination / "RECALCULATED_figure_statistics.csv", index=False)
    dft.to_csv(destination / "RECALCULATED_dft_confirmation.csv", index=False)
    print(destination / "Figure4_RECALCULATED_NOT_ORIGINAL.pdf")


if __name__ == "__main__":
    main()
