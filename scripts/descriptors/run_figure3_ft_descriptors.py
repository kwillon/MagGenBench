from __future__ import annotations

import argparse
from pathlib import Path

from mvpipeline.descriptors.figure3_ft import (
    FT_OUTPUT_DIR, FT_QC_INPUTS, STANDARDIZED_INPUT,
    compute_figure3_ft_descriptors, prepare_figure3_ft_inputs,
)


def main():
    parser = argparse.ArgumentParser(description="Compute only the two new FT Magnetic Descriptor v2 sets")
    parser.add_argument("--standardized-input", type=Path, default=STANDARDIZED_INPUT)
    parser.add_argument("--crystalformer-qc", type=Path, default=FT_QC_INPUTS["crystalformer_finetuned"])
    parser.add_argument("--crystallm-qc", type=Path, default=FT_QC_INPUTS["crystallm_finetuned"])
    parser.add_argument("--output-dir", type=Path, default=FT_OUTPUT_DIR)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, default=Path("config/descriptors_v2_magnetic.yaml"))
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    manifests = prepare_figure3_ft_inputs(
        standardized_input=args.standardized_input,
        qc_inputs={"crystalformer_finetuned": args.crystalformer_qc, "crystallm_finetuned": args.crystallm_qc},
        output_dir=args.output_dir, repo_root=args.repo_root, config_path=args.config,
    )
    print("QC/enrichment identities and CIF paths: PASSED")
    for cohort, path in manifests.items():
        print(f"{cohort} manifest: {path}")
    if not args.prepare_only:
        outputs = compute_figure3_ft_descriptors(
            manifests, output_dir=args.output_dir, repo_root=args.repo_root, config_path=args.config,
        )
        for cohort, path in outputs.items():
            print(f"{cohort} descriptors: {path}")
        print("FIGURE3_FT_DESCRIPTOR_V2: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
