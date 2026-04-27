from pathlib import Path
import csv
import re
import warnings
from collections import Counter, defaultdict

import pandas as pd
from pymatgen.core import Composition, Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


ROOT = Path("/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench")

INPUT_CSV = ROOT / "tables" / "master_structures.downsampled.with_status.classes.csv"
OUT_CSV = ROOT / "tables" / "benchmark_ready_generated.csv"
OUTPUTS_DIR = ROOT / "outputs"


MODEL_LABELS = {
    "cdvae": "Con-CDVAE",
    "concdvae": "Con-CDVAE",
    "con-cdvae": "Con-CDVAE",

    "mg": "MatterGen",
    "mattergen": "MatterGen",

    "cf": "CrystalFormer",
    "crystalformer": "CrystalFormer",

    "cllm": "CrystalLLM",
    "crystalllm": "CrystalLLM",
    "crystallm": "CrystalLLM",
}


MODEL_TO_OUTPUT_DIR = {
    "Con-CDVAE": OUTPUTS_DIR / "concdvae",
    "MatterGen": OUTPUTS_DIR / "mattergen",
    "CrystalFormer": OUTPUTS_DIR / "crystalformer",
    "CrystalLLM": OUTPUTS_DIR / "crystallm",
}


def norm_value(x):
    x = str(x).strip()
    if not x or x.lower() in {"nan", "none", "null"}:
        return ""
    return x


def norm_model(x):
    x = norm_value(x).lower().replace("_", "").replace("-", "")
    return MODEL_LABELS.get(x, x)


def norm_formula(x):
    x = norm_value(x)
    if not x:
        return ""

    try:
        return Composition(x).reduced_formula
    except Exception:
        return x


def element_set_from_formula(formula):
    formula = norm_formula(formula)
    if not formula:
        return ""

    elems = re.findall(r"[A-Z][a-z]?", formula)
    return "-".join(sorted(set(elems)))


def find_col(header, candidates):
    clean = [h.strip() for h in header]
    lower = {h.lower(): i for i, h in enumerate(clean)}

    for c in candidates:
        if c in clean:
            return clean.index(c)
        if c.lower() in lower:
            return lower[c.lower()]

    return None


def get(row, idx):
    if idx is None or idx >= len(row):
        return ""
    return str(row[idx]).strip()


def get_tail_status(row, status_idx):
    # New columns are appended at the end:
    # status,status_source,rejection_reason,compound_class
    if len(row) >= 4:
        candidate = str(row[-4]).strip().lower()
        if candidate in {"validated", "rejected", "unknown", "not_found"}:
            return candidate

    candidate = get(row, status_idx).strip().lower()
    if candidate in {"validated", "rejected", "unknown", "not_found"}:
        return candidate

    return ""


def build_cif_index():
    """
    Build searchable CIF index:
    cif_index[model][filename or stem] -> list[Path]
    """
    cif_index = defaultdict(lambda: defaultdict(list))

    for model_label, model_dir in MODEL_TO_OUTPUT_DIR.items():
        if not model_dir.exists():
            print(f"[WARN] output dir not found for {model_label}: {model_dir}")
            continue

        n = 0

        for p in model_dir.rglob("*.cif"):
            cif_index[model_label][p.name].append(p)
            cif_index[model_label][p.stem].append(p)
            n += 1

        print(f"Indexed CIFs for {model_label}: {n} files from {model_dir}")

    return cif_index


def candidate_names_from_row(row, idxs):
    candidates = []

    for name, idx in idxs.items():
        val = get(row, idx)
        if not val:
            continue

        p = Path(val)

        candidates.extend([
            val,
            p.name,
            p.stem,
        ])

        if not val.endswith(".cif"):
            candidates.append(val + ".cif")
            candidates.append(p.name + ".cif")
            candidates.append(p.stem + ".cif")

    # Deduplicate while preserving order.
    out = []
    seen = set()
    for c in candidates:
        c = str(c).strip()
        if c and c not in seen:
            out.append(c)
            seen.add(c)

    return out


def resolve_cif_path(model, old_cif_path, candidates, cif_index):
    """
    Prefer existing old path. Otherwise search by filename/stem in new outputs/<model>.
    """
    old_cif_path = norm_value(old_cif_path)

    if old_cif_path:
        p = Path(old_cif_path)
        if p.exists():
            return p, "old_cif_path"

    model_index = cif_index.get(model, {})

    for c in candidates:
        hits = model_index.get(c, [])
        if len(hits) == 1:
            return hits[0], "outputs_index_unique"

    # If multiple hits, prefer validated/rejected folder hits over all_structures copies.
    for c in candidates:
        hits = model_index.get(c, [])
        if len(hits) > 1:
            preferred = [
                h for h in hits
                if "validated_structures" in str(h) or "rejected_structures" in str(h)
            ]
            if len(preferred) == 1:
                return preferred[0], "outputs_index_preferred"

            # fallback to first sorted path
            return sorted(hits, key=lambda x: str(x))[0], "outputs_index_multiple_first"

    return None, "not_found"


def parse_cif(cif_path):
    result = {
        "cif_exists": False,
        "cif_parsed": False,
        "spacegroup": "",
        "a": "",
        "b": "",
        "c": "",
        "alpha": "",
        "beta": "",
        "gamma": "",
        "parse_error": "",
    }

    if cif_path is None:
        result["parse_error"] = "cif_path_not_resolved"
        return result

    p = Path(cif_path)

    if not p.exists():
        result["parse_error"] = "cif_file_not_found"
        return result

    result["cif_exists"] = True

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            structure = Structure.from_file(str(p))

        lat = structure.lattice

        result["a"] = float(lat.a)
        result["b"] = float(lat.b)
        result["c"] = float(lat.c)
        result["alpha"] = float(lat.alpha)
        result["beta"] = float(lat.beta)
        result["gamma"] = float(lat.gamma)

        sg_number = ""

        for symprec in [0.1, 0.01, 0.001]:
            try:
                analyzer = SpacegroupAnalyzer(
                    structure,
                    symprec=symprec,
                    angle_tolerance=5,
                )
                sg_number = analyzer.get_space_group_number()
                break
            except Exception:
                pass

        result["spacegroup"] = sg_number
        result["cif_parsed"] = True

    except Exception as e:
        result["parse_error"] = str(e).replace("\n", " ")[:200]

    return result


def main():
    cif_index = build_cif_index()

    with open(INPUT_CSV, "r", encoding="utf-8", errors="replace", newline="") as fin, \
         open(OUT_CSV, "w", encoding="utf-8", newline="") as fout:

        reader = csv.reader(fin)
        writer = csv.writer(fout)

        header = [h.strip() for h in next(reader)]

        model_idx = find_col(header, ["model_short", "model_name", "model"])
        formula_idx = find_col(header, ["formula_reduced", "reduced_formula", "formula", "formula_pretty"])
        cif_path_idx = find_col(header, ["cif_path", "path"])
        status_idx = find_col(header, ["status"])

        candidate_idxs = {
            "cif_path": cif_path_idx,
            "cif_file_name": find_col(header, ["cif_file_name"]),
            "cif_stem": find_col(header, ["cif_stem"]),
            "file_name": find_col(header, ["file_name"]),
            "file_stem": find_col(header, ["file_stem"]),
            "sample_uid": find_col(header, ["sample_uid"]),
            "source_sample_id": find_col(header, ["source_sample_id"]),
        }

        if model_idx is None:
            raise ValueError("Could not find model column")
        if formula_idx is None:
            raise ValueError("Could not find formula column")
        if cif_path_idx is None:
            raise ValueError("Could not find cif_path column")
        if status_idx is None:
            raise ValueError("Could not find status column")

        print("\nDetected columns:")
        print(f"  model_idx      = {model_idx} -> {header[model_idx]}")
        print(f"  formula_idx    = {formula_idx} -> {header[formula_idx]}")
        print(f"  cif_path_idx   = {cif_path_idx} -> {header[cif_path_idx]}")
        print(f"  status_idx     = {status_idx} -> {header[status_idx]}")
        print("  candidate idxs =")
        for k, v in candidate_idxs.items():
            print(f"    {k}: {v if v is not None else 'NOT FOUND'}")

        writer.writerow([
            "model",
            "formula",
            "element_set",
            "spacegroup",
            "a",
            "b",
            "c",
            "alpha",
            "beta",
            "gamma",
            "status",
            "resolved_cif_path",
            "cif_resolution_source",
            "cif_exists",
            "cif_parsed",
            "parse_error",
        ])

        n_rows = 0
        counts = Counter()
        status_counts = Counter()
        parse_counts = Counter()
        resolution_counts = Counter()

        for row in reader:
            model = norm_model(get(row, model_idx))
            formula = norm_formula(get(row, formula_idx))
            old_cif_path = get(row, cif_path_idx)
            status = get_tail_status(row, status_idx)

            candidates = candidate_names_from_row(row, candidate_idxs)
            resolved_path, resolution_source = resolve_cif_path(
                model=model,
                old_cif_path=old_cif_path,
                candidates=candidates,
                cif_index=cif_index,
            )

            parsed = parse_cif(resolved_path)

            writer.writerow([
                model,
                formula,
                element_set_from_formula(formula),
                parsed["spacegroup"],
                parsed["a"],
                parsed["b"],
                parsed["c"],
                parsed["alpha"],
                parsed["beta"],
                parsed["gamma"],
                status,
                str(resolved_path) if resolved_path is not None else "",
                resolution_source,
                parsed["cif_exists"],
                parsed["cif_parsed"],
                parsed["parse_error"],
            ])

            n_rows += 1
            counts[model] += 1
            status_counts[(model, status)] += 1
            parse_counts[(model, parsed["cif_parsed"])] += 1
            resolution_counts[(model, resolution_source)] += 1

            if n_rows % 500 == 0:
                print(f"Processed {n_rows} rows...", flush=True)

    print("\nSaved:")
    print(OUT_CSV)
    print(f"Rows: {n_rows}")

    print("\nCounts by model:")
    for model, n in counts.items():
        print(model, n)

    print("\nStatus counts:")
    for (model, status), n in sorted(status_counts.items()):
        print(model, status, n)

    print("\nCIF resolution counts:")
    for (model, src), n in sorted(resolution_counts.items()):
        print(model, src, n)

    print("\nCIF parse counts:")
    for (model, parsed), n in sorted(parse_counts.items()):
        print(model, parsed, n)

    df = pd.read_csv(OUT_CSV)

    print("\nNon-empty values by model:")
    for model, g in df.groupby("model"):
        print(f"\n{model}")
        for col in ["formula", "spacegroup", "a", "b", "c", "alpha", "beta", "gamma", "status", "cif_parsed"]:
            print(f"{col}: {g[col].notna().sum()} / {len(g)}")

    print("\nStatus table:")
    print(pd.crosstab(df["model"], df["status"]))

    print("\nCIF parsed table:")
    print(pd.crosstab(df["model"], df["cif_parsed"]))

    print("\nResolution source table:")
    print(pd.crosstab(df["model"], df["cif_resolution_source"]))


if __name__ == "__main__":
    main()