#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Balanced MatterGen downsampling: 3050 -> 2000

What it does
------------
1) Reads:
   - mattergen_structures.csv
   - master_structures.csv
   - master_runs.csv
2) Downsamples MatterGen structures to target_n, preserving the run-level
   distribution as closely as possible.
   By default, each run gets a proportional quota based on its current size,
   so every benchmark_group / seed / dft_mag_density / guidance combination
   stays represented.
3) Writes:
   - mattergen_structures.downsampled.csv
   - master_structures.downsampled.csv
   - master_runs.downsampled.csv
4) Optionally moves dropped MatterGen CIFs to an archive folder instead of deleting.

Why this is better
------------------
- It does NOT just remove the last 1050 rows.
- It preserves all runs whenever possible.
- It keeps approximately equal material per seed/run relative to the original.
- It keeps master tables synchronized with the selected MatterGen subset.
"""

from __future__ import annotations

import argparse
import math
import shutil
from pathlib import Path
from typing import Dict, List

import pandas as pd


BASE_DIR = Path(
    "/mnt/tank/scratch/kkapranova/sww-magnetic-validation-pipeline-master/"
    "sww-magnetic-validation-pipeline-master"
)

TABLES_DIR = BASE_DIR / "tables"
SAMPLES_DIR = BASE_DIR / "samples"
MATTERGEN_CIF_DIR = SAMPLES_DIR / "mattergen_cifs"

MATTERGEN_STRUCTURES_CSV = TABLES_DIR / "mattergen_structures.csv"
MASTER_STRUCTURES_CSV = TABLES_DIR / "master_structures.csv"
MASTER_RUNS_CSV = TABLES_DIR / "master_runs.csv"

OUT_MATTERGEN_STRUCTURES = TABLES_DIR / "mattergen_structures.downsampled.csv"
OUT_MASTER_STRUCTURES = TABLES_DIR / "master_structures.downsampled.csv"
OUT_MASTER_RUNS = TABLES_DIR / "master_runs.downsampled.csv"

DEFAULT_TARGET_N = 2000
DEFAULT_RANDOM_STATE = 42


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def largest_remainder_allocation(counts: pd.Series, target_n: int) -> Dict[str, int]:
    """
    Proportional integer allocation with largest remainder method.
    """
    total = int(counts.sum())
    if target_n > total:
        raise ValueError(f"target_n={target_n} is greater than total={total}")

    raw = counts / total * target_n
    floor_alloc = raw.apply(math.floor).astype(int)
    remainders = raw - floor_alloc

    allocated = int(floor_alloc.sum())
    remaining = target_n - allocated

    if remaining > 0:
        winners = remainders.sort_values(ascending=False).index[:remaining]
        floor_alloc.loc[winners] += 1

    return floor_alloc.to_dict()


def sample_mattergen_by_run(
    df: pd.DataFrame,
    target_n: int,
    random_state: int,
) -> pd.DataFrame:
    """
    Downsample MatterGen structures proportionally by run_name.
    This is effectively stratified by the full run configuration because
    each run_name already corresponds to a unique benchmark/seed/condition combo.
    """
    if "run_name" not in df.columns:
        raise ValueError("mattergen_structures.csv must contain 'run_name'")

    counts = df["run_name"].value_counts().sort_index()
    alloc = largest_remainder_allocation(counts, target_n)

    parts: List[pd.DataFrame] = []
    for run_name, group in df.groupby("run_name", sort=False):
        n_take = int(alloc.get(run_name, 0))
        if n_take <= 0:
            continue
        if n_take >= len(group):
            parts.append(group.copy())
        else:
            # stable reproducible sample
            parts.append(group.sample(n=n_take, random_state=random_state))

    out = pd.concat(parts, ignore_index=True)
    return out


def print_distribution(name: str, df: pd.DataFrame) -> None:
    print(f"\n[{name}] rows = {len(df)}")
    for col in ["benchmark_group", "split_type", "dft_mag_density", "guidance"]:
        if col in df.columns:
            print(f"\n[{name}] distribution by {col}:")
            print(df[col].value_counts(dropna=False).sort_index().to_string())

    if "seed" in df.columns:
        vc = df["seed"].value_counts()
        print(f"\n[{name}] seed count summary:")
        print(vc.describe().to_string())

    if "run_name" in df.columns:
        vc = df["run_name"].value_counts()
        print(f"\n[{name}] run count summary:")
        print(vc.describe().to_string())


def update_master_structures(master_df: pd.DataFrame, selected_mg: pd.DataFrame) -> pd.DataFrame:
    """
    Replace MatterGen rows in master_structures with the selected subset.
    Match via cif_path, which is the most robust link for downstream pipeline use.
    """
    mg_master = master_df[master_df["model_name"] == "MatterGen"].copy()
    non_mg = master_df[master_df["model_name"] != "MatterGen"].copy()

    selected_paths = set(selected_mg["cif_path"].dropna().astype(str))

    mg_master_filtered = mg_master[mg_master["cif_path"].astype(str).isin(selected_paths)].copy()

    out = pd.concat([non_mg, mg_master_filtered], ignore_index=True, sort=False)
    return out


def update_master_runs(master_runs: pd.DataFrame, selected_master_structures: pd.DataFrame) -> pd.DataFrame:
    """
    Keep all non-MatterGen runs.
    For MatterGen, keep only runs still referenced by master_structures.
    """
    non_mg_runs = master_runs[master_runs["model_name"] != "MatterGen"].copy()
    mg_runs = master_runs[master_runs["model_name"] == "MatterGen"].copy()

    if "run_uid" not in selected_master_structures.columns:
        raise ValueError("master_structures must contain 'run_uid'")

    keep_run_uids = set(
        selected_master_structures.loc[
            selected_master_structures["model_name"] == "MatterGen", "run_uid"
        ].dropna().astype(str)
    )

    mg_runs_filtered = mg_runs[mg_runs["run_uid"].astype(str).isin(keep_run_uids)].copy()

    out = pd.concat([non_mg_runs, mg_runs_filtered], ignore_index=True, sort=False)
    return out


def archive_dropped_cifs(selected_mg: pd.DataFrame, archive_dir: Path, dry_run: bool = True) -> None:
    """
    Move dropped MatterGen CIF files into archive_dir preserving relative paths.
    """
    selected_paths = set(selected_mg["cif_path"].dropna().astype(str))
    all_paths = [p for p in MATTERGEN_CIF_DIR.rglob("*.cif")]

    to_move = [p for p in all_paths if str(p) not in selected_paths]

    print(f"\n[FILES] MatterGen CIF total: {len(all_paths)}")
    print(f"[FILES] MatterGen CIF selected: {len(selected_paths)}")
    print(f"[FILES] MatterGen CIF to archive: {len(to_move)}")

    if dry_run:
        print("[FILES] Dry run enabled. No files moved.")
        return

    archive_dir.mkdir(parents=True, exist_ok=True)

    for src in to_move:
        rel = src.relative_to(MATTERGEN_CIF_DIR)
        dst = archive_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))

    print(f"[FILES] Archived dropped CIFs to: {archive_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target_n", type=int, default=DEFAULT_TARGET_N)
    parser.add_argument("--random_state", type=int, default=DEFAULT_RANDOM_STATE)
    parser.add_argument(
        "--archive_dropped_cifs",
        action="store_true",
        help="Move dropped MatterGen CIF files into an archive folder.",
    )
    parser.add_argument(
        "--archive_dir",
        type=str,
        default=str(SAMPLES_DIR / "mattergen_cifs_archived"),
        help="Where to move dropped CIF files if --archive_dropped_cifs is set.",
    )
    parser.add_argument(
        "--apply_in_place",
        action="store_true",
        help="Overwrite original CSV files after writing .downsampled.csv outputs.",
    )
    parser.add_argument(
        "--dry_run_files",
        action="store_true",
        help="With --archive_dropped_cifs, print what would move but do not move files.",
    )
    args = parser.parse_args()

    mg = read_csv(MATTERGEN_STRUCTURES_CSV)
    master_struct = read_csv(MASTER_STRUCTURES_CSV)
    master_runs = read_csv(MASTER_RUNS_CSV)

    if len(mg) != 3050:
        print(f"[WARN] mattergen_structures.csv has {len(mg)} rows, not 3050.")

    print_distribution("MatterGen ORIGINAL", mg)

    selected_mg = sample_mattergen_by_run(
        df=mg,
        target_n=args.target_n,
        random_state=args.random_state,
    ).copy()

    # Stable sort for readability
    sort_cols = [c for c in ["benchmark_group", "dft_mag_density", "seed", "run_name", "row_index_within_run"] if c in selected_mg.columns]
    if sort_cols:
        selected_mg = selected_mg.sort_values(sort_cols).reset_index(drop=True)

    print_distribution("MatterGen DOWNSAMPLED", selected_mg)

    selected_master_struct = update_master_structures(master_struct, selected_mg)
    selected_master_runs = update_master_runs(master_runs, selected_master_struct)

    # Save outputs first
    selected_mg.to_csv(OUT_MATTERGEN_STRUCTURES, index=False)
    selected_master_struct.to_csv(OUT_MASTER_STRUCTURES, index=False)
    selected_master_runs.to_csv(OUT_MASTER_RUNS, index=False)

    print(f"\n[SAVED] {OUT_MATTERGEN_STRUCTURES}")
    print(f"[SAVED] {OUT_MASTER_STRUCTURES}")
    print(f"[SAVED] {OUT_MASTER_RUNS}")

    # Optional file archiving
    if args.archive_dropped_cifs:
        archive_dropped_cifs(
            selected_mg=selected_mg,
            archive_dir=Path(args.archive_dir),
            dry_run=args.dry_run_files,
        )

    # Optional overwrite originals
    if args.apply_in_place:
        shutil.copy2(OUT_MATTERGEN_STRUCTURES, MATTERGEN_STRUCTURES_CSV)
        shutil.copy2(OUT_MASTER_STRUCTURES, MASTER_STRUCTURES_CSV)
        shutil.copy2(OUT_MASTER_RUNS, MASTER_RUNS_CSV)
        print("\n[APPLY] Overwrote original CSV files with downsampled versions.")

    # Quick sanity checks
    print("\n[CHECKS]")
    print("Downsampled MatterGen rows:", len(selected_mg))
    print("Downsampled master_structures rows:", len(selected_master_struct))
    print("Downsampled master_runs rows:", len(selected_master_runs))

    if "model_name" in selected_master_struct.columns:
        print("\n[CHECKS] master_structures by model:")
        print(selected_master_struct["model_name"].value_counts(dropna=False).to_string())

    if "model_name" in selected_master_runs.columns:
        print("\n[CHECKS] master_runs by model:")
        print(selected_master_runs["model_name"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
