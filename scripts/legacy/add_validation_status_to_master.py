from pathlib import Path
import csv
from collections import Counter, defaultdict


ROOT = Path("/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench")

MASTER_CSV = ROOT / "tables" / "master_structures.downsampled.csv"
OUT_CSV = ROOT / "tables" / "master_structures.downsampled.with_status.csv"
OUTPUTS_DIR = ROOT / "outputs"


MODEL_ALIASES = {
    "cdvae": "concdvae",
    "concdvae": "concdvae",
    "con-cdvae": "concdvae",

    "mg": "mattergen",
    "mattergen": "mattergen",

    "cf": "crystalformer",
    "crystalformer": "crystalformer",

    "cllm": "crystalllm",
    "crystalllm": "crystalllm",
    "crystallm": "crystalllm",
    "crystal-llm": "crystalllm",
}


def norm_model(x):
    if x is None:
        return ""
    x = str(x).strip().lower().replace("_", "").replace("-", "")
    return MODEL_ALIASES.get(x, x)


def norm_value(x):
    if x is None:
        return ""
    x = str(x).strip()
    if not x or x.lower() in {"nan", "none", "null"}:
        return ""
    return x


def path_variants(x):
    x = norm_value(x)
    if not x:
        return set()

    p = Path(x)
    vals = {
        x,
        p.name,
        p.stem,
    }

    if not x.endswith(".cif"):
        vals.add(x + ".cif")
        vals.add(p.name + ".cif")
        vals.add(p.stem + ".cif")

    return {v for v in vals if v}


def get_cell(row, header, names):
    for name in names:
        if name in header:
            idx = header.index(name)
            if idx < len(row):
                return norm_value(row[idx])
    return ""


def detect_status_from_row(row, header):
    """
    Detect validation status from all_structures.csv row.
    Supports several possible column names.
    """

    # Direct status columns
    for col in [
        "status",
        "validation_status",
        "structure_status",
        "final_status",
        "is_valid_status",
    ]:
        if col in header:
            val = norm_value(row[header.index(col)]).lower()
            if val in {"validated", "valid", "passed", "pass", "accepted"}:
                return "validated"
            if val in {"rejected", "invalid", "failed", "fail"}:
                return "rejected"

    # Boolean validity columns
    for col in [
        "is_valid",
        "valid",
        "validated",
        "passed_validation",
        "is_validated",
        "validation_passed",
    ]:
        if col in header:
            val = norm_value(row[header.index(col)]).lower()
            if val in {"true", "1", "yes", "y"}:
                return "validated"
            if val in {"false", "0", "no", "n"}:
                return "rejected"

    # If rejection reason exists and is non-empty, this is rejected
    for col in [
        "rejection_reason",
        "rejection_reasons",
        "reject_reason",
        "failed_reason",
        "failure_reason",
    ]:
        if col in header:
            val = norm_value(row[header.index(col)])
            if val:
                return "rejected"

    return "unknown"


def detect_rejection_reason(row, header):
    for col in [
        "rejection_reason",
        "rejection_reasons",
        "reject_reason",
        "failed_reason",
        "failure_reason",
    ]:
        if col in header:
            return norm_value(row[header.index(col)])
    return ""


def find_all_structures_csvs():
    """
    Finds outputs/<model>/all_structures.csv.
    Handles crystallm/crystalllm spelling mismatch.
    """
    result = {}

    for model_dir in OUTPUTS_DIR.iterdir():
        if not model_dir.is_dir():
            continue

        model = norm_model(model_dir.name)
        path = model_dir / "all_structures.csv"

        if path.exists():
            result[model] = path

    return result


def load_all_structures():
    """
    Load statuses from outputs/<model>/all_structures.csv.

    Returns:
    - ordered_statuses[model] = list of statuses in row order
    - ordered_reasons[model] = list of rejection reasons in row order
    - unique_index[(model, key)] = (status, reason)
    """
    all_csvs = find_all_structures_csvs()

    print("Found all_structures.csv files:")
    for model, path in all_csvs.items():
        print(f"  {model}: {path}")

    ordered_statuses = defaultdict(list)
    ordered_reasons = defaultdict(list)

    raw_index = defaultdict(list)

    candidate_cols = [
        "sample_uid",
        "structure_uid",
        "structure_id",
        "id",
        "material_id",
        "source_sample_id",
        "cif_file_name",
        "cif_filename",
        "filename",
        "file_name",
        "cif_stem",
        "file_stem",
        "cif_path",
        "path",
    ]

    for model, path in all_csvs.items():
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(f)
            header = [h.strip() for h in next(reader)]

            counts = Counter()

            for i, row in enumerate(reader):
                status = detect_status_from_row(row, header)
                reason = detect_rejection_reason(row, header)

                ordered_statuses[model].append(status)
                ordered_reasons[model].append(reason)
                counts[status] += 1

                keys = set()

                # Row-order keys
                keys.add(f"row_index::{i}")
                keys.add(f"row_number::{i + 1}")

                # Real identifier keys
                for col in candidate_cols:
                    if col in header:
                        idx = header.index(col)
                        if idx < len(row):
                            val = norm_value(row[idx])
                            for v in path_variants(val):
                                keys.add(f"{col}::{v}")

                for key in keys:
                    raw_index[(model, key)].append((status, reason))

            print(f"\nLoaded {model} from all_structures.csv:")
            print(dict(counts))

    # Keep only unique non-conflicting keys.
    unique_index = {}

    for key, values in raw_index.items():
        unique_values = set(values)
        if len(values) == 1 and len(unique_values) == 1:
            unique_index[key] = values[0]

    return ordered_statuses, ordered_reasons, unique_index


def main():
    ordered_statuses, ordered_reasons, unique_index = load_all_structures()

    counts = Counter()
    counts_by_model = defaultdict(Counter)
    source_counts = Counter()

    row_counter_by_model = defaultdict(int)

    with open(MASTER_CSV, "r", encoding="utf-8", errors="replace", newline="") as fin, \
         open(OUT_CSV, "w", encoding="utf-8", newline="") as fout:

        reader = csv.reader(fin)
        writer = csv.writer(fout)

        header = [h.strip() for h in next(reader)]

        print("\nMaster columns:")
        for i, col in enumerate(header[:20]):
            print(i, col)

        writer.writerow(header + ["status", "status_source", "rejection_reason"])

        for row in reader:
            model = get_cell(row, header, ["model_short", "model_name", "model"])
            model = norm_model(model)

            model_row_i = row_counter_by_model[model]
            row_counter_by_model[model] += 1

            candidate_keys = []

            for col in [
                "sample_uid",
                "structure_uid",
                "structure_id",
                "id",
                "source_sample_id",
                "cif_file_name",
                "cif_filename",
                "filename",
                "file_name",
                "cif_stem",
                "file_stem",
                "cif_path",
                "path",
            ]:
                val = get_cell(row, header, [col])
                for v in path_variants(val):
                    candidate_keys.append(f"{col}::{v}")

            status = "unknown"
            reason = ""
            status_source = "not_matched"

            # 1. Exact unique identifier match
            for key in candidate_keys:
                lookup = (model, key)
                if lookup in unique_index:
                    status, reason = unique_index[lookup]
                    status_source = "all_structures_unique_key"
                    break

            # 2. Safe row-order fallback
            # This is useful when master_structures was created directly from all_structures
            # and has 2000 rows per model in the same order.
            if status == "unknown":
                if model in ordered_statuses and model_row_i < len(ordered_statuses[model]):
                    status = ordered_statuses[model][model_row_i]
                    reason = ordered_reasons[model][model_row_i]
                    status_source = "all_structures_row_order"

            counts[status] += 1
            counts_by_model[model][status] += 1
            source_counts[status_source] += 1

            writer.writerow(row + [status, status_source, reason])

    print("\nSaved:")
    print(OUT_CSV)

    print("\nStatus counts:")
    print(dict(counts))

    print("\nStatus counts by model:")
    for model, c in counts_by_model.items():
        print(model, dict(c))

    print("\nStatus source counts:")
    print(dict(source_counts))


if __name__ == "__main__":
    main()