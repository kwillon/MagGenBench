"""Reproduce Figure 4 in an isolated output tree using the existing MP-only model.

Run with the Python environment installed from filter/environment/requirements.txt.
Preparation copies CIFs; original samples and manuscript PDFs are never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from importlib.metadata import distributions, version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "reproduced/fig04_mp_only"
MODEL = ROOT / "filter/src/cifmagfilter/data/model"
FIGURE_BASELINE = "907d98ffca4f04a9db46363251db8fdd284bbcca"
COHORTS = {
    "mattergen_base": "mattergen_cifs", "mattergen_finetuned": "mattergen_finetuned_cifs",
    "concdvae_base": "concdvae_cifs", "concdvae_finetuned": "concdvae_finetuned_cifs",
    "crysjepa_base": "crysjepa_base_cifs", "crysjepa_refined": "crysjepa_refined_cifs",
    "crystalformer": "crystalformer_cifs", "crystalformer_finetuned": "crystalformer_finetuned_cifs",
    "crystalllm": "crystalllm_cifs", "crystalllm_finetuned": "crystallm_finetuned_cifs",
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_script(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(output):
    original = output / "original/fig04_magnetic_reference_dft.pdf"
    original.parent.mkdir(parents=True, exist_ok=True)
    if not original.exists():
        original.write_bytes(subprocess.check_output(
            ["git", "show", FIGURE_BASELINE + ":paper/figures/fig04_magnetic_reference_dft.pdf"], cwd=ROOT))
    for script in ("run_mp_pipeline.py", "recalculate_dft_mp_only.py", "plot_mp_only_publication.py"):
        preserved = original.parent / script
        if not preserved.exists():
            preserved.write_bytes(subprocess.check_output(
                ["git", "show", FIGURE_BASELINE + ":filter/scripts/" + script], cwd=ROOT))
    preparation = load_script("prepare_benchmark", ROOT / "filter/scripts/prepare_benchmark.py")
    all_rows = []
    for dataset, folder in COHORTS.items():
        rows = []
        count = preparation.prepare_dataset(
            ROOT / "samples" / folder, output / "data/generators" / dataset / "cifs",
            dataset, dataset.split("_")[0], dataset.split("_")[-1], "query", None,
            rows, False,
        )
        if count != 2000:
            raise RuntimeError(f"{dataset}: expected 2000 input CIFs, found {count}")
        # Existing scorer expects cif_id in each cohort manifest.
        for row in rows:
            row["cif_id"] = row["structure_id"]
        preparation.write_csv(output / "data/generators" / dataset / "manifest.csv", rows)
        all_rows.extend(rows)
    preparation.write_csv(output / "input_manifest.csv", all_rows)
    provenance = {
        "baseline_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "figure_baseline_commit": FIGURE_BASELINE,
        "original_pdf_sha256": digest(original),
        "protected_figures": {name: digest(ROOT / "paper/figures" / name) for name in
                              ("fig03_magnetic_domain.pdf", "fig05_energy_magnetism.pdf")},
        "model_sha256": {name: digest(MODEL / name) for name in ("reference_filter.json", "reference_filter.npz")},
        "input_count": len(all_rows),
    }
    (output / "input_provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")


def environment(output):
    packages = ("numpy", "pandas", "scikit-learn", "scipy", "pymatgen", "pymatgen-core", "SMACT",
                "spglib", "matplotlib", "Pillow", "umap-learn", "networkx", "pytest")
    record = {"python": sys.version, "platform": platform.platform(),
              "packages": {p: version(p) for p in packages},
              "all_packages": dict(sorted((d.metadata["Name"], d.version) for d in distributions()))}
    (output / "environment.json").write_text(json.dumps(record, indent=2), encoding="utf-8")


def run(output, script, *arguments, log_name):
    command = [sys.executable, str(ROOT / script), *map(str, arguments)]
    print("Running:", command, flush=True)
    with (output / log_name).open("w", encoding="utf-8") as log:
        subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)


def full_extraction(output, jobs):
    """Independent cohort jobs, with canonical CLI extraction and checkpoints.

    No descriptor settings are changed. Merging follows the same sorted cohort
    and sorted filename order as the original sequential run_mp_pipeline.py.
    """
    import pandas as pd

    def extract_cohort(dataset):
        cohort = output / "cohorts" / dataset
        cohort.mkdir(parents=True, exist_ok=True)
        config = {"output_dir": str(cohort), "extraction": {"reject_disordered": True},
                  "datasets": [{"name": dataset, "role": "query",
                                "path": str(output / "data/generators" / dataset / "cifs")}]}
        config_path = cohort / "config.json"
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        signature = {"environment": digest(output / "environment.json"),
                     "manifest": digest(output / "data/generators" / dataset / "manifest.csv"),
                     "core": digest(ROOT / "filter/src/cifmagfilter/core.py"),
                     "cli": digest(ROOT / "filter/src/cifmagfilter/cli.py")}
        checkpoint = cohort / "completed.json"
        feature_path = cohort / "features/structure_features.csv"
        if checkpoint.is_file():
            if json.loads(checkpoint.read_text()) != signature:
                raise RuntimeError(f"{dataset}: checkpoint provenance changed; use a separate output directory")
            print(f"Reusing verified extraction: {dataset}", flush=True)
        else:
            print(f"Extracting: {dataset}", flush=True)
            with (cohort / "extraction.log").open("w", encoding="utf-8") as log:
                subprocess.run([sys.executable, "-X", "utf8", "-m", "cifmagfilter.cli", "extract",
                                "--config", str(config_path)], cwd=ROOT,
                               stdout=log, stderr=subprocess.STDOUT, check=True)
        frame = pd.read_csv(feature_path, low_memory=False)
        manifest = pd.read_csv(output / "data/generators" / dataset / "manifest.csv")
        if len(frame) != 2000 or frame.structure_id.duplicated().any():
            raise RuntimeError(f"{dataset}: incomplete or duplicate feature records")
        if set(frame.structure_id) != set(manifest.structure_id) or set(frame.dataset) != {dataset}:
            raise RuntimeError(f"{dataset}: extracted identity set does not match source manifest")
        checkpoint.write_text(json.dumps(signature, indent=2), encoding="utf-8")
        print(f"Extracted: {dataset}, rows={len(frame)}, parsed={int(frame.parse_success.eq(1).sum())}", flush=True)
        return dataset, frame

    frames = {}
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        futures = [executor.submit(extract_cohort, ds) for ds in sorted(COHORTS)]
        for future in as_completed(futures):
            ds, frame = future.result()
            frames[ds] = frame
    merged = pd.concat([frames[ds] for ds in sorted(COHORTS)], ignore_index=True)
    feature_dir = output / "results/mp_only/features"
    feature_dir.mkdir(parents=True, exist_ok=True)
    merged.to_csv(feature_dir / "structure_features.csv", index=False)
    merged.loc[~merged.parse_success.eq(1)].to_csv(feature_dir / "parse_failures.csv", index=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "smoke", "full", "dft", "plot", "all"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--smoke-limit", type=int, default=2)
    parser.add_argument("--jobs", type=int, default=4, choices=range(1, 5))
    parser.add_argument("--qa-python", type=Path, default=ROOT / ".venv/Scripts/python.exe",
                        help="Python with PyMuPDF for read-only PDF verification")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if args.stage == "all":
        for stage in ("prepare", "smoke", "full"):
            subprocess.run([sys.executable, "-X", "utf8", __file__, stage, "--output", str(output),
                            "--jobs", str(args.jobs)], cwd=ROOT, check=True)
        subprocess.run([sys.executable, str(ROOT / "scripts/analysis/audit_figure4_mp_only.py"),
                        "--output", str(output)], cwd=ROOT, check=True)
        subprocess.run([sys.executable, __file__, "dft", "--output", str(output)], cwd=ROOT, check=True)
        subprocess.run([sys.executable, str(ROOT / "scripts/analysis/audit_figure4_mp_only.py"),
                        "--output", str(output), "--dft"], cwd=ROOT, check=True)
        subprocess.run([str(args.qa_python.resolve()), str(ROOT / "scripts/analysis/audit_figure4_pdf_values.py"),
                        "--output", str(output)], cwd=ROOT, check=True)
        subprocess.run([sys.executable, __file__, "plot", "--output", str(output)], cwd=ROOT, check=True)
        return
    if args.stage == "prepare":
        prepare(output)
        return
    environment(output)
    if args.stage in ("smoke", "full"):
        if args.stage == "full":
            full_extraction(output, args.jobs)
        extra = ("--limit", args.smoke_limit) if args.stage == "smoke" else ("--skip-extract",)
        run(output, "filter/scripts/run_mp_pipeline.py", "--project", output,
            "--model-dir", MODEL, *extra, log_name=f"{args.stage}.log")
    elif args.stage == "dft":
        run(output, "filter/scripts/recalculate_dft_mp_only.py",
            "--scores", output / "results/mp_only/generator_scores.csv",
            "--manifests-dir", output / "data/generators",
            "--output-dir", output / "results/mp_only/dft_validation", log_name="dft.log")
    else:
        import pandas as pd
        audit = json.loads((output / "audit/audit.json").read_text())
        readback = pd.read_csv(output / "audit/original_pdf_vs_reproduced.csv")
        if not audit["summary_matches"] or not readback.matches_pdf_precision.all():
            raise RuntimeError("Scientific audit must pass before styling/export")
        result = output / "results/mp_only"
        run(output, "filter/scripts/plot_mp_only_publication.py",
            "--summary", result / "generator_summary.csv", "--scores", result / "generator_scores.csv",
            "--dft-joined", result / "dft_validation/dft_joined_mp_only.csv",
            "--dft-audit", result / "dft_validation/dft_validation_audit.json",
            "--output-dir", output / "figures", log_name="plot.log")


if __name__ == "__main__":
    main()
