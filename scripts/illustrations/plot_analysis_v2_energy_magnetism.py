from __future__ import annotations

from mvpipeline.analysis.energy_magnetism_v2 import (
    run_analysis_v2_energy_magnetism,
)


def main() -> int:
    report = run_analysis_v2_energy_magnetism()

    print("===== Energy–magnetism analysis figures =====")
    print(f"input: {report.input_csv}")
    print(f"total rows: {report.n_total}")
    print(f"paired finite rows: {report.n_paired}")

    print("\n===== Generated-set summary =====")
    print(
        report.summary[
            [
                "analysis_cohort",
                "n",
                "energy_median_eV_per_atom",
                "moment_median",
                "pearson_r",
                "spearman_rho",
            ]
        ].to_string(index=False)
    )

    print("\n===== Figures =====")
    for paths in report.figure_paths:
        print(f"figure_png: {paths.png}")
        print(f"figure_pdf: {paths.pdf}")
        print(f"figure_svg: {paths.svg}")

    print("ANALYSIS_V2_ENERGY_MAGNETISM: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
