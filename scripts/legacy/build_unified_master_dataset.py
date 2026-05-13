#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(
    "/mnt/tank/scratch/kkapranova/MagGenBench/"
    "MagGenBench"
)

TABLES_DIR = BASE_DIR / "tables"
SAMPLES_DIR = BASE_DIR / "samples"

OUT_MASTER_STRUCTURES = TABLES_DIR / "master_structures.csv"
OUT_MASTER_RUNS = TABLES_DIR / "master_runs.csv"


MODEL_CONFIG = {
    "MatterGen": {
        "short": "mg",
        "structures_candidates": [
            "mattergen_structures.csv",
        ],
        "runs_candidates": [
            "mattergen_runs.csv",
        ],
        "cif_dir": SAMPLES_DIR / "mattergen_cifs",
    },
    "CrystalFormer": {
        "short": "cf",
        "structures_candidates": [
            "crystalformer_generations.csv",
            "crystalformer_structures.csv",
            "generations_crystalformer.csv",
            "cf_generations.csv",
            "generations.csv",
        ],
        "runs_candidates": [
            "crystalformer_runs.csv",
            "cf_runs.csv",
            "runs_crystalformer.csv",
            "runs.csv",
        ],
        "cif_dir": SAMPLES_DIR / "crystalformer_cifs",
    },
    "CrystaLLM": {
        "short": "cllm",
        "structures_candidates": [
            "crystalllm_generations.csv",
            "crystalllm_structures.csv",
            "generations_crystalllm.csv",
            "cllm_generations.csv",
            "generations.csv",
        ],
        "runs_candidates": [
            "crystalllm_runs.csv",
            "cllm_runs.csv",
            "runs_crystalllm.csv",
            "runs.csv",
        ],
        "cif_dir": SAMPLES_DIR / "crystalllm_cifs",
    },
    "Con-CDVAE": {
        "short": "cdvae",
        "structures_candidates": [
            "con_cdvae_structures.csv",
            "concdvae_structures.csv",
            "con_cdvae_generations.csv",
            "concdvae_generations.csv",
        ],
        "runs_candidates": [
            "con_cdvae_runs.csv",
            "concdvae_runs.csv",
        ],
        "cif_dir": SAMPLES_DIR / "concdvae_cifs",
    },
}


# ============================================================
# HELPERS
# ============================================================

def find_existing_file(directory: Path, candidates: List[str], required: bool = True) -> Optional[Path]:
    for name in candidates:
        p = directory / name
        if p.exists():
            return p
    if required:
        raise FileNotFoundError(
            f"Could not find any of these files in {directory}:\n  - " + "\n  - ".join(candidates)
        )
    return None


def read_csv_safe(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def first_existing_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def normalize_string(s: str) -> str:
    s = str(s).strip()
    s = re.sub(r"[^\w\-.]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def build_uid(prefix: str, *parts: str) -> str:
    clean_parts = [normalize_string(p) for p in parts if str(p).strip()]
    if not clean_parts:
        return prefix
    return f"{prefix}__" + "__".join(clean_parts)


def safe_json_dumps(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return "{}"


def to_optional_str(x) -> Optional[str]:
    if pd.isna(x):
        return None
    s = str(x).strip()
    return s if s else None


def parse_crystallm_source_sample_id(value: str) -> Tuple[Optional[str], Optional[int]]:
    """
    Parse strings like:
      crystallm_benchmark_30x100_seed1337_t08_k10__Co2FeAl__0001
    and return:
      ("Co2FeAl", 1)
    """
    if value is None:
        return None, None

    s = str(value).strip()
    if not s:
        return None, None

    m = re.search(r"__([^_]+)__0*([0-9]+)$", s)
    if not m:
        return None, None

    formula_dir = m.group(1).strip()
    idx = int(m.group(2))
    return formula_dir, idx


def build_cif_index(cif_root: Path) -> Dict[str, object]:
    by_name: Dict[str, List[Path]] = {}
    by_stem: Dict[str, List[Path]] = {}
    all_paths: List[Path] = []

    if not cif_root.exists():
        print(f"[WARN] CIF dir does not exist: {cif_root}")
        return {"by_name": by_name, "by_stem": by_stem, "all_paths": all_paths}

    for p in cif_root.rglob("*.cif"):
        all_paths.append(p)
        by_name.setdefault(p.name, []).append(p)
        by_stem.setdefault(p.stem, []).append(p)

    return {
        "by_name": by_name,
        "by_stem": by_stem,
        "all_paths": all_paths,
    }


def pick_best_cif_path(
    row: pd.Series,
    cif_index: Dict[str, object],
    candidate_cols: List[str],
    model_name: Optional[str] = None,
) -> Optional[str]:
    by_name = cif_index["by_name"]
    by_stem = cif_index["by_stem"]
    all_paths = cif_index["all_paths"]

    candidate_values = []

    for c in candidate_cols:
        if c not in row.index:
            continue
        val = row[c]
        if pd.isna(val):
            continue
        sval = str(val).strip()
        if sval:
            candidate_values.append(sval)

    for sval in candidate_values:
        p = Path(sval)
        if p.exists() and p.suffix.lower() == ".cif":
            return str(p)

    for sval in candidate_values:
        fname = Path(sval).name
        if fname in by_name and len(by_name[fname]) >= 1:
            return str(by_name[fname][0])

    for sval in candidate_values:
        stem = Path(sval).stem
        if stem in by_stem and len(by_stem[stem]) >= 1:
            return str(by_stem[stem][0])

# Model-specific fallback: Con-CDVAE
    # IMPORTANT: handle this BEFORE generic substring matching,
    # otherwise "eval_gen_FM0" will incorrectly match __0000.cif for all rows.
    if model_name == "Con-CDVAE":
        src_sample = to_optional_str(row.get("source_sample_id"))
        src_run = to_optional_str(row.get("source_run_name"))

        # Best case: parse source_sample_id like eval_gen_FM0.pt__29
        if src_sample:
            m = re.match(r"(eval_gen_FM\d+)\.pt__(\d+)$", src_sample, flags=re.IGNORECASE)
            if m:
                fm = m.group(1)
                idx = int(m.group(2))
                expected_name = f"{fm}__{idx:04d}.cif"

                if expected_name in by_name and len(by_name[expected_name]) >= 1:
                    return str(by_name[expected_name][0])

                for p in all_paths:
                    if p.parent.name.lower() == fm.lower() and p.name.lower() == expected_name.lower():
                        return str(p)

        # Fallback: parse source_run_name + source_sample_id separately
        if src_run and src_sample:
            fm_match = re.match(r"(eval_gen_FM\d+)\.pt$", src_run, flags=re.IGNORECASE)
            idx_match = re.search(r"__(\d+)$", src_sample)
            if fm_match and idx_match:
                fm = fm_match.group(1)
                idx = int(idx_match.group(1))
                expected_name = f"{fm}__{idx:04d}.cif"

                if expected_name in by_name and len(by_name[expected_name]) >= 1:
                    return str(by_name[expected_name][0])

                for p in all_paths:
                    if p.parent.name.lower() == fm.lower() and p.name.lower() == expected_name.lower():
                        return str(p)

        return None

    lowered_candidates = [v.lower() for v in candidate_values]

    for p in all_paths:
        p_name = p.name.lower()
        p_stem = p.stem.lower()
        for cand in lowered_candidates:
            cand_name = Path(cand).name.lower()
            cand_stem = Path(cand).stem.lower()

            if cand_name and cand_name in p_name:
                return str(p)
            if cand_stem and cand_stem in p_stem:
                return str(p)

    if model_name == "CrystaLLM":
        src_sample = to_optional_str(row.get("source_sample_id"))
        if src_sample:
            formula_dir, idx = parse_crystallm_source_sample_id(src_sample)
            if formula_dir is not None and idx is not None:
                expected_name = f"sample_{idx}.cif"

                for p in all_paths:
                    if p.parent.name == formula_dir and p.name == expected_name:
                        return str(p)

        formula_dir_candidates = []
        if src_sample:
            formula_dir, idx = parse_crystallm_source_sample_id(src_sample)
            if formula_dir:
                formula_dir_candidates.append(formula_dir)

        sample_candidates = []
        if src_sample:
            _, idx = parse_crystallm_source_sample_id(src_sample)
            if idx is not None:
                sample_candidates.append(f"sample_{idx}")
                sample_candidates.append(f"sample_{idx}.cif")

        for c in ["file_name", "file_stem", "cif_path_orig"]:
            if c in row.index and pd.notna(row[c]):
                s = str(row[c]).strip()
                if s:
                    sample_candidates.append(s)

        for sc in sample_candidates:
            fname = Path(sc).name
            stem = Path(sc).stem

            if fname in by_name and len(by_name[fname]) == 1:
                return str(by_name[fname][0])

            if stem in by_stem and len(by_stem[stem]) == 1:
                return str(by_stem[stem][0])

        for p in all_paths:
            parent_name = p.parent.name
            p_name = p.name
            p_stem = p.stem

            formula_ok = False
            sample_ok = False

            for fc in formula_dir_candidates:
                if fc and fc == parent_name:
                    formula_ok = True
                    break

            for sc in sample_candidates:
                sc_name = Path(sc).name
                sc_stem = Path(sc).stem
                if sc_name and sc_name == p_name:
                    sample_ok = True
                    break
                if sc_stem and sc_stem == p_stem:
                    sample_ok = True
                    break

            if formula_ok and sample_ok:
                return str(p)

        return None
    return None


def standardize_structure_columns(df: pd.DataFrame) -> pd.DataFrame:
    colmap = {
        "formula_reduced": ["formula_reduced", "reduced_formula"],
        "formula_full": ["formula_full", "formula_raw", "formula", "formula_sum"],
        "n_atoms": ["n_atoms", "n_sites", "num_atoms"],
        "elements": ["elements"],
        "chemical_system": ["chemical_system", "chemsys"],

        "a": ["a", "cell_a"],
        "b": ["b", "cell_b"],
        "c": ["c", "cell_c"],
        "alpha": ["alpha", "cell_alpha"],
        "beta": ["beta", "cell_beta"],
        "gamma": ["gamma", "cell_gamma"],
        "volume": ["volume", "cell_volume"],
        "density": ["density"],

        "spacegroup_number": ["spacegroup_number", "sg_number", "space_group_number"],
        "spacegroup_symbol": ["spacegroup_symbol", "sg_symbol", "space_group_symbol"],

        "sites_json": ["sites_json"],
        "parse_ok": ["parse_ok"],
        "parse_error": ["parse_error"],

        "benchmark_group": ["benchmark_group"],
        "split_type": ["split_type"],

        "source_sample_id": ["sample_id", "generation_id", "id"],
        "source_run_name": ["run_name", "run_id", "subrun_id"],
        "file_name": ["file_name"],
        "file_stem": ["file_stem"],
        "cif_path_orig": ["cif_path", "structure_path", "path"],
    }

    for target, candidates in colmap.items():
        col = first_existing_col(df, candidates)
        if col is not None:
            df[target] = df[col]
        else:
            df[target] = None

    if "file_name" not in df.columns or df["file_name"].isna().all():
        if "cif_path_orig" in df.columns:
            df["file_name"] = df["cif_path_orig"].apply(
                lambda x: Path(str(x)).name if pd.notna(x) and str(x).strip() else None
            )

    if "file_stem" not in df.columns or df["file_stem"].isna().all():
        if "file_name" in df.columns:
            df["file_stem"] = df["file_name"].apply(
                lambda x: Path(str(x)).stem if pd.notna(x) and str(x).strip() else None
            )

    return df


def standardize_run_columns(df: pd.DataFrame) -> pd.DataFrame:
    colmap = {
        "source_run_id": ["run_id", "run_name", "subrun_id"],
        "run_name_std": ["run_name", "run_id", "subrun_id"],
        "run_dir_std": ["run_dir", "subrun_dir", "output_dir"],
        "benchmark_group": ["benchmark_group"],
        "split_type": ["split_type"],
        "seed_std": ["seed"],
        "checkpoint_std": ["checkpoint_path", "checkpoint_name", "restore_path", "pretrained_name"],
    }

    for target, candidates in colmap.items():
        col = first_existing_col(df, candidates)
        if col is not None:
            df[target] = df[col]
        else:
            df[target] = None

    return df


def infer_run_uid_from_structure_row(row: pd.Series, model_short: str) -> str:
    src_run = to_optional_str(row.get("source_run_name"))
    bench = to_optional_str(row.get("benchmark_group"))
    split_type = to_optional_str(row.get("split_type"))
    file_stem = to_optional_str(row.get("file_stem"))

    if bench and src_run:
        return build_uid(model_short, bench, src_run)

    if split_type and src_run:
        return build_uid(model_short, split_type, src_run)

    if src_run:
        return build_uid(model_short, src_run)

    if bench and split_type and file_stem:
        return build_uid(model_short, bench, split_type, file_stem)

    if bench and file_stem:
        return build_uid(model_short, bench, file_stem)

    if file_stem:
        return build_uid(model_short, file_stem)

    return build_uid(model_short, "unknown_run")


def infer_sample_uid(row: pd.Series, model_short: str) -> str:
    run_uid = to_optional_str(row.get("run_uid")) or build_uid(model_short, "unknown_run")

    cif_stem = to_optional_str(row.get("cif_stem"))
    cif_file_name = to_optional_str(row.get("cif_file_name"))
    file_stem = to_optional_str(row.get("file_stem"))
    src_sample = to_optional_str(row.get("source_sample_id"))

    # CrystaLLM special handling FIRST, because sample_1 repeats across formula folders
    if model_short == "cllm" and src_sample:
        formula_dir, idx = parse_crystallm_source_sample_id(src_sample)
        if formula_dir is not None and idx is not None:
            return f"{run_uid}__{normalize_string(formula_dir)}__sample_{idx}"

    # For all other models, real matched CIF stem is great
    if cif_stem:
        return f"{run_uid}__{normalize_string(cif_stem)}"

    if cif_file_name:
        return f"{run_uid}__{normalize_string(Path(cif_file_name).stem)}"

    if file_stem:
        return f"{run_uid}__{normalize_string(file_stem)}"

    if src_sample:
        return f"{run_uid}__{normalize_string(src_sample)}"

    return f"{run_uid}__sample"


def build_run_uid_for_runs_row(row: pd.Series, model_short: str) -> str:
    source_run_id = to_optional_str(row.get("source_run_id"))
    run_name_std = to_optional_str(row.get("run_name_std"))
    benchmark_group = to_optional_str(row.get("benchmark_group"))
    split_type = to_optional_str(row.get("split_type"))

    if benchmark_group and source_run_id:
        return build_uid(model_short, benchmark_group, source_run_id)

    if benchmark_group and run_name_std:
        return build_uid(model_short, benchmark_group, run_name_std)

    if split_type and source_run_id:
        return build_uid(model_short, split_type, source_run_id)

    if split_type and run_name_std:
        return build_uid(model_short, split_type, run_name_std)

    if source_run_id:
        return build_uid(model_short, source_run_id)

    if run_name_std:
        return build_uid(model_short, run_name_std)

    return build_uid(model_short, "unknown_run")


def load_model_tables(model_name: str, cfg: Dict) -> Tuple[pd.DataFrame, pd.DataFrame]:
    struct_path = find_existing_file(TABLES_DIR, cfg["structures_candidates"], required=True)
    runs_path = find_existing_file(TABLES_DIR, cfg["runs_candidates"], required=True)

    print(f"[INFO] {model_name}: structures <- {struct_path.name}")
    print(f"[INFO] {model_name}: runs       <- {runs_path.name}")

    df_struct = read_csv_safe(struct_path)
    df_runs = read_csv_safe(runs_path)

    df_struct["model_name"] = model_name
    df_struct["model_short"] = cfg["short"]
    df_struct["source_table"] = struct_path.name
    df_runs["model_name"] = model_name
    df_runs["model_short"] = cfg["short"]
    df_runs["source_runs_table"] = runs_path.name

    df_struct = standardize_structure_columns(df_struct)
    df_runs = standardize_run_columns(df_runs)

    return df_struct, df_runs


def unify_structures_for_model(model_name: str, cfg: Dict) -> pd.DataFrame:
    df_struct, _ = load_model_tables(model_name, cfg)
    cif_index = build_cif_index(cfg["cif_dir"])

    cif_candidate_cols = [
        "cif_path_orig",
        "cif_path",
        "file_name",
        "file_stem",
        "source_sample_id",
    ]

    df_struct["cif_path"] = df_struct.apply(
        lambda row: pick_best_cif_path(
            row=row,
            cif_index=cif_index,
            candidate_cols=cif_candidate_cols,
            model_name=model_name,
        ),
        axis=1
    )

    df_struct["cif_exists"] = df_struct["cif_path"].apply(
        lambda x: Path(x).exists() if pd.notna(x) and str(x).strip() else False
    )
    df_struct["cif_file_name"] = df_struct["cif_path"].apply(
        lambda x: Path(str(x)).name if pd.notna(x) and str(x).strip() else None
    )
    df_struct["cif_stem"] = df_struct["cif_path"].apply(
        lambda x: Path(str(x)).stem if pd.notna(x) and str(x).strip() else None
    )

    df_struct["file_stem"] = df_struct["file_stem"].where(
        df_struct["file_stem"].notna(),
        df_struct["cif_stem"]
    )

    df_struct["run_uid"] = df_struct.apply(
        lambda row: infer_run_uid_from_structure_row(row, cfg["short"]),
        axis=1
    )
    df_struct["sample_uid"] = df_struct.apply(
        lambda row: infer_sample_uid(row, cfg["short"]),
        axis=1
    )

    keep_cols = [
        "sample_uid",
        "model_name",
        "model_short",
        "run_uid",
        "source_table",
        "source_sample_id",
        "source_run_name",

        "benchmark_group",
        "split_type",

        "cif_path",
        "cif_exists",
        "cif_file_name",
        "cif_stem",
        "file_name",
        "file_stem",

        "formula_reduced",
        "formula_full",
        "n_atoms",
        "elements",
        "chemical_system",

        "a",
        "b",
        "c",
        "alpha",
        "beta",
        "gamma",
        "volume",
        "density",

        "spacegroup_number",
        "spacegroup_symbol",

        "sites_json",
        "parse_ok",
        "parse_error",
    ]

    orig_extra = [c for c in df_struct.columns if c not in keep_cols]
    df_out = df_struct[keep_cols + orig_extra].copy()

    return df_out


def unify_runs_for_model(model_name: str, cfg: Dict) -> pd.DataFrame:
    _, df_runs = load_model_tables(model_name, cfg)

    df_runs["run_uid"] = df_runs.apply(
        lambda row: build_run_uid_for_runs_row(row, cfg["short"]),
        axis=1
    )

    orig_cols = list(df_runs.columns)

    def row_to_json(row):
        data = {}
        for c in orig_cols:
            val = row[c]
            if pd.isna(val):
                data[c] = None
            else:
                data[c] = val
        return safe_json_dumps(data)

    df_runs["param_json"] = df_runs.apply(row_to_json, axis=1)

    keep_cols = [
        "run_uid",
        "model_name",
        "model_short",
        "source_runs_table",
        "source_run_id",
        "run_name_std",
        "run_dir_std",
        "benchmark_group",
        "split_type",
        "seed_std",
        "checkpoint_std",
        "param_json",
    ]

    extra_cols = [c for c in df_runs.columns if c not in keep_cols]
    df_out = df_runs[keep_cols + extra_cols].copy()

    return df_out


def main():
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    all_structs = []
    all_runs = []

    for model_name, cfg in MODEL_CONFIG.items():
        print("=" * 80)
        print(f"[INFO] Processing model: {model_name}")

        df_struct = unify_structures_for_model(model_name, cfg)
        df_runs = unify_runs_for_model(model_name, cfg)

        print(f"[INFO] {model_name}: structures rows = {len(df_struct)}")
        print(f"[INFO] {model_name}: runs rows       = {len(df_runs)}")

        all_structs.append(df_struct)
        all_runs.append(df_runs)

    master_struct = pd.concat(all_structs, ignore_index=True, sort=False)
    master_runs = pd.concat(all_runs, ignore_index=True, sort=False)

    if "run_uid" in master_runs.columns:
        before = len(master_runs)
        master_runs = master_runs.drop_duplicates(subset=["run_uid"]).reset_index(drop=True)
        after = len(master_runs)
        if after != before:
            print(f"[INFO] Dropped duplicate runs: {before - after}")

    if "sample_uid" in master_struct.columns:
        dup_mask = master_struct.duplicated(subset=["sample_uid"], keep=False)
        n_dup = int(dup_mask.sum())
        if n_dup > 0:
            print(f"[WARN] Duplicate sample_uid rows detected: {n_dup}")
            dup_path = TABLES_DIR / "debug_duplicate_sample_uids.csv"
            master_struct.loc[dup_mask].to_csv(dup_path, index=False)
            print(f"[WARN] Saved duplicate sample_uids to: {dup_path}")

    struct_sort_cols = [c for c in ["model_name", "run_uid", "sample_uid"] if c in master_struct.columns]
    run_sort_cols = [c for c in ["model_name", "run_uid"] if c in master_runs.columns]

    if struct_sort_cols:
        master_struct = master_struct.sort_values(struct_sort_cols).reset_index(drop=True)
    if run_sort_cols:
        master_runs = master_runs.sort_values(run_sort_cols).reset_index(drop=True)

    master_struct.to_csv(OUT_MASTER_STRUCTURES, index=False)
    master_runs.to_csv(OUT_MASTER_RUNS, index=False)

    print("=" * 80)
    print("[DONE]")
    print(f"[INFO] Saved master structures: {OUT_MASTER_STRUCTURES}")
    print(f"[INFO] Saved master runs:       {OUT_MASTER_RUNS}")
    print(f"[INFO] Master structures rows: {len(master_struct)}")
    print(f"[INFO] Master runs rows:       {len(master_runs)}")

    print("\n[SUMMARY] Structures by model:")
    print(master_struct["model_name"].value_counts(dropna=False).to_string())

    print("\n[SUMMARY] CIF existence by model:")
    tmp = (
        master_struct.groupby("model_name", dropna=False)["cif_exists"]
        .agg(["sum", "count"])
        .rename(columns={"sum": "n_cif_found", "count": "n_rows"})
    )
    print(tmp.to_string())


if __name__ == "__main__":
    main()