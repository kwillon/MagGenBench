"""Regenerate the selected Figures 3 and 5 without rerunning descriptors/inference."""
import argparse
from pathlib import Path
from shutil import copyfile

from mvpipeline.analysis.manuscript_figure3_v2 import run_manuscript_figure3
from mvpipeline.analysis.manuscript_figure5_v2 import run_manuscript_figure5


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true", help="Copy verified exports to paper/figures")
    args = parser.parse_args()
    qc = {key: Path(f"tables/03_features/phase5b_{key}_with_classes.csv")
          for key in ("crystalformer_finetuned", "crystallm_finetuned")}
    report3 = run_manuscript_figure3(qc_inputs=qc, require_complete_descriptors=True)
    report5 = run_manuscript_figure5()
    print(report3.audit.to_string())
    print(f"Figure 5: {report5.n_paired} finite pairs / {report5.n_total} rows")
    for report, name in ((report3, "fig03_magnetic_domain"), (report5, "fig05_energy_magnetism")):
        print(report.figure_paths)
        if args.publish:
            copyfile(report.figure_paths.pdf, Path("paper/figures") / f"{name}.pdf")


if __name__ == "__main__":
    main()
