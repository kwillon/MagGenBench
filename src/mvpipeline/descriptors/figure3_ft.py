from __future__ import annotations

import hashlib
import json
import platform
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from ..io.stage_tables import write_stage_csv_atomic

STANDARDIZED_INPUT = Path("tables/08_standardized_enrichment/standardized_enrichment.csv")
FT_QC_INPUTS = {
    key: Path(f"outputs/{key}/all_structures.csv")
    for key in ("crystalformer_finetuned", "crystallm_finetuned")
}
FT_OUTPUT_DIR = Path("reproduced/figure3_ft_descriptors")
EXPECTED_RETAINED = {"crystalformer_finetuned": 1380, "crystallm_finetuned": 217}


def mapped_retained_qc(qc, cohort, standardized):
    import pandas as pd

    if len(qc) != 2000:
        raise RuntimeError(f"{cohort}: expected 2000 harmonized QC rows, got {len(qc)}")
    if "status" not in qc:
        raise RuntimeError(f"{cohort}: missing QC status")
    key = "sample_uid" if "sample_uid" in qc else "structure_id"
    if key not in qc:
        raise RuntimeError(f"{cohort}: missing QC identifiers")
    ids = qc[key].fillna("").astype(str).str.strip()
    if ids.eq("").any() or ids.duplicated().any():
        raise RuntimeError(f"{cohort}: empty or duplicate QC identifiers")
    status = qc["status"].fillna("").astype(str).str.strip().str.lower()
    if not status.isin(["validated", "rejected"]).all():
        raise RuntimeError(f"{cohort}: unknown QC status")
    selected = standardized.loc[standardized["analysis_cohort"].eq(cohort)].copy()
    required = {"sample_uid", "structure_id", "source_sample_id", "status"}
    if required.difference(selected.columns):
        raise RuntimeError(f"{cohort}: enrichment missing identity/status columns")
    if selected["sample_uid"].fillna("").eq("").any() or selected["sample_uid"].duplicated().any():
        raise RuntimeError(f"{cohort}: duplicate or missing enrichment sample_uid")
    if not selected["sample_uid"].eq(selected["structure_id"]).all():
        raise RuntimeError(f"{cohort}: enrichment sample_uid != structure_id")
    if not selected["status"].eq("validated").all():
        raise RuntimeError(f"{cohort}: enrichment contains non-validated rows")
    retained = ids.loc[status.eq("validated")]
    if key == "sample_uid" or set(retained).issubset(set(selected["sample_uid"])):
        canonical = retained
    else:
        source = selected["source_sample_id"]
        if source.fillna("").eq("").any() or source.duplicated().any():
            raise RuntimeError(f"{cohort}: missing or duplicate source_sample_id")
        mapping = selected.set_index("source_sample_id")["sample_uid"]
        canonical = retained.map(mapping)
        if canonical.isna().any():
            absent = retained.loc[canonical.isna()].tolist()
            raise RuntimeError(f"{cohort}: QC IDs not mapped by enrichment source_sample_id: {absent[:5]}")
    if canonical.duplicated().any() or set(canonical) != set(selected["sample_uid"]):
        raise RuntimeError(f"{cohort}: retained QC IDs and enrichment IDs differ")
    return pd.DataFrame({
        "qc_structure_id": retained.to_numpy(),
        "sample_uid": canonical.to_numpy(),
        "structure_id": canonical.to_numpy(),
    })


def _existing_cif(row, repo_root):
    for field in ("cif_path_original", "cif_path"):
        value = str(row.get(field) or "")
        if not value:
            continue
        path = Path(value)
        if not path.is_absolute():
            path = repo_root / path
        if path.is_file():
            return str(path.resolve())
    raise FileNotFoundError(f"{row['sample_uid']}: no recorded CIF path exists")


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_figure3_ft_inputs(
    *, standardized_input=STANDARDIZED_INPUT, qc_inputs=None, output_dir=FT_OUTPUT_DIR,
    repo_root=".", config_path="config/descriptors_v2_magnetic.yaml",
):
    import pandas as pd
    import yaml
    from .config_v2 import load_magnetic_descriptor_v2_runtime_config

    root = Path(repo_root).resolve()
    output = Path(output_dir)
    config_path = Path(config_path)
    config = load_magnetic_descriptor_v2_runtime_config(config_path, project_root=root)
    config_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    magnetic_path = Path(config_data["descriptors_v2_magnetic"]["magnetic_screening_config"])
    if not magnetic_path.is_absolute():
        magnetic_path = root / magnetic_path
    paths = {**FT_QC_INPUTS, **(qc_inputs or {})}
    if set(paths) != set(FT_QC_INPUTS):
        raise ValueError("Only CrystalFormer FT and CrystaLLM FT can be prepared")
    standardized = pd.read_csv(standardized_input, low_memory=False, dtype=str).fillna("")
    prepared = {}
    provenance = {
        "standardized_input": str(standardized_input),
        "standardized_sha256": _sha256(standardized_input),
        "descriptor_config": str(config_path), "descriptor_config_sha256": _sha256(config_path),
        "magnetism_config_sha256": _sha256(magnetic_path),
        "scientific_code_sha256": {
            name: _sha256(Path(__file__).with_name(name))
            for name in ("batch_v2.py", "extractor_v2.py", "magnetic_composition.py",
                         "magnetic_geometry.py", "magnetic_sites.py")
        },
        "geometry": {
            "method": config.local_geometry_method, "cutoff": config.local_geometry_cutoff,
            "tolerance": config.local_geometry_tolerance,
            "get_all_sites": config.local_geometry_get_all_sites,
            "use_weights": config.local_geometry_use_weights,
        },
        "element_sets": {
            "transition_3d": config.magnetic_elements.transition_3d,
            "selected_4d_5d": config.magnetic_elements.selected_4d_5d,
            "lanthanides": config.magnetic_elements.lanthanides,
        },
        "versions": {"python": platform.python_version()}, "cohorts": {},
    }
    for package in ("pymatgen", "pymatgen-core", "numpy", "spglib", "pandas"):
        try:
            provenance["versions"][package] = version(package)
        except PackageNotFoundError:
            provenance["versions"][package] = None
    # Validate both populations and all recorded CIF paths before writing either manifest.
    for cohort, path in paths.items():
        qc = pd.read_csv(path, low_memory=False, dtype=str).fillna("")
        mapping = mapped_retained_qc(qc, cohort, standardized)
        rows = standardized.loc[standardized["analysis_cohort"].eq(cohort)].copy()
        if len(rows) != EXPECTED_RETAINED[cohort]:
            raise RuntimeError(f"{cohort}: expected {EXPECTED_RETAINED[cohort]} retained rows, got {len(rows)}")
        rows = rows.merge(mapping, on=["sample_uid", "structure_id"], validate="one_to_one")
        records = rows.to_dict("records")
        for row in records:
            row["cif_path"] = _existing_cif(row, root)
        prepared[cohort] = (rows.columns.tolist(), records, mapping)
        provenance["cohorts"][cohort] = {
            "qc_input": str(path), "qc_sha256": _sha256(path),
            "population": len(qc), "retained": len(rows),
        }
    manifests = {}
    for cohort, (fields, records, mapping) in prepared.items():
        manifest = output / "manifests" / f"{cohort}.csv"
        write_stage_csv_atomic(manifest, records, fields)
        write_stage_csv_atomic(
            output / "manifests" / f"{cohort}_qc_ids.csv",
            mapping.to_dict("records"), list(mapping.columns),
        )
        provenance["cohorts"][cohort]["manifest_sha256"] = _sha256(manifest)
        manifests[cohort] = manifest
    output.mkdir(parents=True, exist_ok=True)
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return manifests


def compute_figure3_ft_descriptors(manifests, *, output_dir=FT_OUTPUT_DIR,
                                    repo_root=".", config_path="config/descriptors_v2_magnetic.yaml"):
    import pandas as pd
    from .batch_v2 import run_magnetic_descriptor_v2_batch

    outputs = {}
    for cohort, manifest in manifests.items():
        path = Path(output_dir) / f"{cohort}_descriptor_v2_magnetic.csv"
        report = run_magnetic_descriptor_v2_batch(
            input_path=manifest, output_path=path, descriptor_config_path=config_path,
            project_root=repo_root,
        )
        expected = pd.read_csv(manifest, dtype=str)["sample_uid"].tolist()
        actual = pd.read_csv(path, dtype=str)
        if report.output_count != len(expected) or actual["sample_uid"].tolist() != expected:
            raise RuntimeError(f"{cohort}: descriptor row count/order/IDs changed")
        if not actual["structure_id"].eq(actual["sample_uid"]).all():
            raise RuntimeError(f"{cohort}: descriptor identity mismatch")
        outputs[cohort] = path
    return outputs
