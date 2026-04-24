#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
normalize_and_merge_train.py

Делает компактный train_reference.csv формата:

    id,reduced_formula,spacegroup

для выбранной модели.

Примеры:
    python normalize_and_merge_train.py --model mattergen
    python normalize_and_merge_train.py --model crystalllm
    python normalize_and_merge_train.py --model concdvae

Если нужно сохранить расширенную таблицу для отладки:
    python normalize_and_merge_train.py --model mattergen --write-debug
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from pymatgen.core import Composition, Structure


# ---------------------------------------------------------------------
# Убираем шумные pymatgen warnings при чтении CIF
# ---------------------------------------------------------------------

warnings.filterwarnings(
    "ignore",
    message="Issues encountered while parsing CIF.*",
    category=UserWarning,
)

warnings.filterwarnings(
    "ignore",
    message="No Pauling electronegativity.*",
    category=UserWarning,
)


# ---------------------------------------------------------------------
# Пути проекта
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(
    "/mnt/tank/scratch/kkapranova/sww-magnetic-validation-pipeline-master/"
    "sww-magnetic-validation-pipeline-master"
)

RAW_DATA_DIR = PROJECT_ROOT / "datasets" / "raw_data"

MODEL_OUT_DIRS: Dict[str, Path] = {
    "mattergen": PROJECT_ROOT / "datasets" / "mattergen",
    "crystalllm": PROJECT_ROOT / "datasets" / "crystalllm",
    "concdvae": PROJECT_ROOT / "datasets" / "concdvae",
    "crystalformer": PROJECT_ROOT / "datasets" / "crystalformer",
}

# ---------------------------------------------------------------------
# ВАЖНО: проверь соответствие источников моделям.
#
# Сейчас стоит стартовая схема:
# - mattergen:  mp_20 + alex_mp_20
# - crystalllm: mp_20 + carbon_24 + mpts_52
# - concdvae:   mp_20 + mp4conz
# - crystalformer:   mp_20 
#
# Почему concdvae только mp4conz:
# в прошлой версии mp_20 + mp4conz дали 54272 строк до dedup
# и 27136 после dedup, то есть это выглядело как полный дубль.
#
# Если окажется, что для Con-CDVAE действительно нужны оба файла,
# можно вернуть mp_20_train.csv в список.
# ---------------------------------------------------------------------

MODEL_SOURCES: Dict[str, List[Path]] = {
    "mattergen": [
        RAW_DATA_DIR / "mp_20_train.csv",
        RAW_DATA_DIR / "alex_mp_20_train.csv",
    ],
    "crystalllm": [
        RAW_DATA_DIR / "mp_20_train.csv",
        RAW_DATA_DIR / "carbon_24_train.csv",
        RAW_DATA_DIR / "mpts_52_train.csv",
        RAW_DATA_DIR / "perov_5_train.csv",
    ],
    "concdvae": [
        RAW_DATA_DIR / "mp4conz_train.csv",
        RAW_DATA_DIR / "mp_20_train.csv",
    ],
    "crystalformer": [
        RAW_DATA_DIR / "mp_20_train.csv",
    ],
}


# ---------------------------------------------------------------------
# Возможные имена колонок
# ---------------------------------------------------------------------

ID_COL_CANDIDATES = [
    "material_id",
    "id",
    "mp_id",
    "entry_id",
]

FORMULA_COL_CANDIDATES = [
    "reduced_formula",
    "pretty_formula",
    "formula",
    "composition_reduced",
]

SPACEGROUP_COL_CANDIDATES = [
    "spacegroup_number",
    "spacegroup.number",
    "spacegroup",
    "space_group",
    "sg_number",
    "symmetry_number",
]

CIF_COL_CANDIDATES = [
    "cif",
    "cif_str",
    "cif_string",
    "structure_cif",
]


def find_first_existing_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def normalize_formula(value: object) -> Optional[str]:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return Composition(text).reduced_formula
    except Exception:
        return text


def safe_int(value: object) -> Optional[int]:
    if value is None or pd.isna(value):
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def parse_structure_from_cif(value: object) -> Optional[Structure]:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return Structure.from_str(text, fmt="cif")
    except Exception:
        return None


def get_id(row: pd.Series, id_col: Optional[str], source_dataset: str, idx: int) -> str:
    if id_col is not None:
        value = row.get(id_col)
        if value is not None and not pd.isna(value):
            text = str(value).strip()
            if text:
                return text
    return f"{source_dataset}__row_{idx}"


def get_formula(row: pd.Series, formula_col: Optional[str], cif_col: Optional[str]) -> Optional[str]:
    if formula_col is not None:
        formula = normalize_formula(row.get(formula_col))
        if formula:
            return formula

    if cif_col is not None:
        structure = parse_structure_from_cif(row.get(cif_col))
        if structure is not None:
            try:
                return structure.composition.reduced_formula
            except Exception:
                return None

    return None


def get_spacegroup(row: pd.Series, sg_col: Optional[str], cif_col: Optional[str]) -> Optional[int]:
    if sg_col is not None:
        sg = safe_int(row.get(sg_col))
        if sg is not None:
            return sg

    if cif_col is not None:
        structure = parse_structure_from_cif(row.get(cif_col))
        if structure is not None:
            try:
                return int(structure.get_space_group_info()[1])
            except Exception:
                return None

    return None


def normalize_one_csv(csv_path: Path) -> pd.DataFrame:
    print(f"[INFO] Reading: {csv_path}")
    df = pd.read_csv(csv_path)

    source_dataset = csv_path.stem

    id_col = find_first_existing_column(df, ID_COL_CANDIDATES)
    formula_col = find_first_existing_column(df, FORMULA_COL_CANDIDATES)
    sg_col = find_first_existing_column(df, SPACEGROUP_COL_CANDIDATES)
    cif_col = find_first_existing_column(df, CIF_COL_CANDIDATES)

    print(
        "[INFO] Matched columns:",
        json.dumps(
            {
                "id_col": id_col,
                "formula_col": formula_col,
                "sg_col": sg_col,
                "cif_col": cif_col,
            },
            ensure_ascii=False,
        ),
    )

    rows = []
    debug_rows = []

    for idx, row in df.iterrows():
        out_id = get_id(row, id_col, source_dataset, idx)
        reduced_formula = get_formula(row, formula_col, cif_col)
        spacegroup = get_spacegroup(row, sg_col, cif_col)

        rows.append(
            {
                "id": out_id,
                "reduced_formula": reduced_formula,
                "spacegroup": spacegroup,
            }
        )

        debug_rows.append(
            {
                "id": out_id,
                "source_dataset": source_dataset,
                "source_row": idx,
                "reduced_formula": reduced_formula,
                "spacegroup": spacegroup,
            }
        )

    out = pd.DataFrame(rows)
    out["_source_dataset"] = source_dataset
    out["_source_row"] = range(len(out))

    print(
        f"[INFO] Built compact dataframe for {source_dataset}: "
        f"{len(out)} rows | "
        f"formula non-null={out['reduced_formula'].notna().sum()} | "
        f"sg non-null={out['spacegroup'].notna().sum()}"
    )

    return out


def deduplicate(df: pd.DataFrame, dedup_key: str) -> Tuple[pd.DataFrame, Dict[str, int]]:
    before = len(df)

    if dedup_key == "none":
        after_df = df.copy()
    elif dedup_key == "id":
        after_df = df.drop_duplicates(subset=["id"], keep="first")
    elif dedup_key == "formula_sg":
        # Не удаляем строки, где formula/sg не распарсились.
        ok = df["reduced_formula"].notna() & df["spacegroup"].notna()
        good = df[ok].drop_duplicates(subset=["reduced_formula", "spacegroup"], keep="first")
        bad = df[~ok]
        after_df = pd.concat([good, bad], ignore_index=True)
    elif dedup_key == "id_formula_sg":
        after_df = df.drop_duplicates(subset=["id", "reduced_formula", "spacegroup"], keep="first")
    else:
        raise ValueError(f"Unknown dedup_key: {dedup_key}")

    after = len(after_df)
    stats = {"before": before, "after": after, "removed": before - after}
    return after_df, stats


def build_train_reference(model: str, dedup_key: str, write_debug: bool) -> None:
    if model not in MODEL_SOURCES:
        raise ValueError(f"Unknown model: {model}. Allowed: {sorted(MODEL_SOURCES)}")

    input_files = MODEL_SOURCES[model]
    output_dir = MODEL_OUT_DIRS[model]
    output_dir.mkdir(parents=True, exist_ok=True)

    missing = [str(p) for p in input_files if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing input files:\n" + "\n".join(missing))

    parts = [normalize_one_csv(path) for path in input_files]
    merged = pd.concat(parts, ignore_index=True)

    print(f"[INFO] Rows before dedup for {model}: {len(merged)}")
    merged, stats = deduplicate(merged, dedup_key=dedup_key)

    # Для стабильного порядка.
    merged = merged.sort_values(
        by=["reduced_formula", "spacegroup", "id"],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)

    # Финальный компактный файл — только 3 нужные колонки.
    final_df = merged[["id", "reduced_formula", "spacegroup"]].copy()

    # spacegroup лучше сохранить как nullable integer.
    final_df["spacegroup"] = pd.to_numeric(final_df["spacegroup"], errors="coerce").astype("Int64")

    out_path = output_dir / "train_reference.csv"
    final_df.to_csv(out_path, index=False)

    print(f"[OK] Saved compact train_reference: {out_path}")
    print(f"[OK] Final shape: {final_df.shape}")
    print(f"[OK] Dedup stats: {stats}")

    if write_debug:
        debug_path = output_dir / "train_reference_debug.csv"
        merged.to_csv(debug_path, index=False)
        print(f"[OK] Saved debug table: {debug_path}")

    readme_path = output_dir / "README_train_reference.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(f"# train_reference for {model}\n\n")
        f.write("This file is a compact normalized training reference table for novelty comparison.\n\n")
        f.write("## Output file\n")
        f.write("- `train_reference.csv`\n\n")
        f.write("## Output columns\n")
        f.write("- `id`\n")
        f.write("- `reduced_formula`\n")
        f.write("- `spacegroup`\n\n")
        f.write("## Sources\n")
        for path in input_files:
            f.write(f"- `{path}`\n")
        f.write("\n## Deduplication\n")
        f.write(f"- dedup_key: `{dedup_key}`\n")
        f.write(f"- rows before dedup: {stats['before']}\n")
        f.write(f"- rows after dedup: {stats['after']}\n")
        f.write(f"- removed duplicates: {stats['removed']}\n")

    print(f"[OK] Saved README: {readme_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        required=True,
        choices=sorted(MODEL_SOURCES),
        help="Model name",
    )
    parser.add_argument(
        "--dedup-key",
        default="id",
        choices=["id", "formula_sg", "id_formula_sg", "none"],
        help=(
            "Deduplication strategy. "
            "Recommended: id for MP-like ids; formula_sg is stricter but may remove polymorphs incorrectly."
        ),
    )
    parser.add_argument(
        "--write-debug",
        action="store_true",
        help="Also save train_reference_debug.csv with source_dataset/source_row",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_train_reference(
        model=args.model,
        dedup_key=args.dedup_key,
        write_debug=args.write_debug,
    )


if __name__ == "__main__":
    main()
