from pathlib import Path
import csv


ROOT = Path("/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench")

INPUT_CSV = ROOT / "tables" / "master_structures.downsampled.with_status.classes.csv"
OUT_CSV = ROOT / "tables" / "master_structures.downsampled.with_status.classes.clean.csv"


KEEP_COLUMNS = [
    "sample_uid",
    "model_name",
    "model_short",
    "run_uid",
    "source_sample_id",
    "cif_file_name",
    "formula_reduced",
    "formula_pretty",
    "status",
    "status_source",
    "rejection_reason",
    "compound_class",
]


def main():
    with open(INPUT_CSV, "r", encoding="utf-8", errors="replace", newline="") as fin, \
         open(OUT_CSV, "w", encoding="utf-8", newline="") as fout:

        reader = csv.reader(fin)
        writer = csv.writer(fout)

        header = [h.strip() for h in next(reader)]

        available_columns = [c for c in KEEP_COLUMNS if c in header]
        indices = [header.index(c) for c in available_columns]

        writer.writerow(available_columns)

        n = 0

        for row in reader:
            clean_row = []

            for idx in indices:
                if idx < len(row):
                    clean_row.append(row[idx].strip())
                else:
                    clean_row.append("")

            writer.writerow(clean_row)
            n += 1

    print("Saved:")
    print(OUT_CSV)
    print(f"Rows: {n}")
    print("Columns:")
    print(available_columns)


if __name__ == "__main__":
    main()