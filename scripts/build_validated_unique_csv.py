import argparse
from pathlib import Path
import pandas as pd

from pymatgen.core import Structure
from pymatgen.analysis.structure_matcher import StructureMatcher


def collect_unique_structures(input_dir: Path):
    cif_files = sorted(input_dir.rglob("*.cif"))
    print(f"Found CIF files: {len(cif_files)}")

    matcher = StructureMatcher()
    unique_structures = []
    rows = []

    for i, cif_path in enumerate(cif_files, start=1):
        try:
            struct = Structure.from_file(str(cif_path))
        except Exception as e:
            print(f"[WARN] Failed to parse {cif_path}: {e}")
            continue

        is_dup = False
        for us in unique_structures:
            try:
                if (
                    struct.composition.reduced_composition
                    == us.composition.reduced_composition
                    and matcher.fit(struct, us)
                ):
                    is_dup = True
                    break
            except Exception:
                continue

        if is_dup:
            continue

        unique_structures.append(struct)
        rows.append({
            "structure_id": f"{input_dir.parent.name}__{i:06d}",
            "source_path": str(cif_path),
            "formula": struct.composition.reduced_formula,
            "cif": struct.to(fmt="cif"),
        })

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-csv", required=True)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    df = collect_unique_structures(input_dir)
    df.to_csv(output_csv, index=False)

    print(f"Saved unique validated CSV: {output_csv}")
    print(f"Rows: {len(df)}")


if __name__ == "__main__":
    main()