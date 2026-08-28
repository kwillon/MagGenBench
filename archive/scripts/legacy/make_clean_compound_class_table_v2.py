from pathlib import Path
import csv

ROOT = Path("/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench")

INPUT_CSV = ROOT / "tables" / "master_structures.downsampled.with_status.classes.csv"
OUT_CSV = ROOT / "tables" / "master_structures.downsampled.with_status.classes.clean_v2.csv"

KEEP_COLUMNS = [
    "sample_uid",
    "model_name",
    "model_short",
    "run_uid",
    "source_sample_id",
    "cif_path",
    "cif_file_name",
    "formula_reduced",
    "formula_full",
]

TAIL_COLUMNS = [
    "status",
    "status_source",
    "rejection_reason",
    "compound_class",
]


def clean_value(x):
    return str(x).strip()


def main():
    with open(INPUT_CSV, "r", encoding="utf-8", errors="replace", newline="") as fin, \
         open(OUT_CSV, "w", encoding="utf-8", newline="") as fout:

        reader = csv.reader(fin)
        writer = csv.writer(fout)

        header = [h.strip() for h in next(reader)]

        available_columns = [c for c in KEEP_COLUMNS if c in header]
        indices = [header.index(c) for c in available_columns]

        writer.writerow(available_columns + TAIL_COLUMNS)

        n = 0
        n_bad_tail = 0

        for row in reader:
            clean_row = []

            for idx in indices:
                if idx < len(row):
                    clean_row.append(clean_value(row[idx]))
                else:
                    clean_row.append("")

            if len(row) >= 4 and clean_value(row[-4]).lower() in {
                "validated",
                "rejected",
                "unknown",
                "not_found",
            }:
                tail = [
                    clean_value(row[-4]),
                    clean_value(row[-3]),
                    clean_value(row[-2]),
                    clean_value(row[-1]),
                ]
            else:
                tail = ["", "", "", ""]
                n_bad_tail += 1

            writer.writerow(clean_row + tail)
            n += 1

    print("Saved:")
    print(OUT_CSV)
    print(f"Rows: {n}")
    print(f"Rows with bad tail: {n_bad_tail}")


if __name__ == "__main__":
    main()