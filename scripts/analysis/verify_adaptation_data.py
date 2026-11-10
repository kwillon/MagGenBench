"""Verify adaptation metadata and optional private payloads without deserialization.

Default: validate all local payloads. --metadata-only explicitly excludes data
content validation. --source-root also checks originals and the prior inventory.
"""
from __future__ import annotations

import argparse
import array
from collections import Counter
import csv
from decimal import Decimal
from fractions import Fraction
import gzip
import hashlib
import json
import math
from pathlib import Path
import pickletools
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "adaptation_data"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def literal_pickle(path):
    """Interpret primitive literals only; never call pickle.load or reducers."""
    if path.name.endswith(".gz"):
        with gzip.open(path, "rb") as handle:
            data = handle.read(16_000_001)
    else:
        data = path.read_bytes()
    require(len(data) <= 16_000_000, "Static literal input exceeds size limit")
    stack, memo, mark = [], {}, object()

    def chunk():
        index = len(stack) - 1
        while index >= 0 and stack[index] is not mark:
            index -= 1
        require(index >= 0, "Missing literal MARK")
        values = stack[index + 1:]
        del stack[index:]
        return values

    for opcode, value, _ in pickletools.genops(data):
        name = opcode.name
        if name in ("PROTO", "FRAME"):
            continue
        if name == "MARK":
            stack.append(mark)
        elif name in ("BINUNICODE", "SHORT_BINUNICODE", "BINUNICODE8", "UNICODE",
                      "BININT", "BININT1", "BININT2", "INT", "LONG", "LONG1",
                      "LONG4", "BINFLOAT", "FLOAT"):
            stack.append(value)
        elif name == "NONE":
            stack.append(None)
        elif name in ("NEWTRUE", "NEWFALSE"):
            stack.append(name == "NEWTRUE")
        elif name == "EMPTY_LIST":
            stack.append([])
        elif name == "EMPTY_DICT":
            stack.append({})
        elif name == "EMPTY_TUPLE":
            stack.append(())
        elif name == "MEMOIZE":
            memo[len(memo)] = stack[-1]
        elif name in ("BINPUT", "LONG_BINPUT", "PUT"):
            memo[int(value)] = stack[-1]
        elif name in ("BINGET", "LONG_BINGET", "GET"):
            stack.append(memo[int(value)])
        elif name == "APPEND":
            item = stack.pop()
            stack[-1].append(item)
        elif name == "APPENDS":
            items = chunk()
            stack[-1].extend(items)
        elif name == "SETITEM":
            item, key = stack.pop(), stack.pop()
            stack[-1][key] = item
        elif name == "SETITEMS":
            items = chunk()
            require(len(items) % 2 == 0, "Odd dictionary item stream")
            for key, item in zip(items[::2], items[1::2]):
                stack[-1][key] = item
        elif name == "TUPLE":
            stack.append(tuple(chunk()))
        elif name in ("TUPLE1", "TUPLE2", "TUPLE3"):
            count = int(name[-1])
            items = tuple(stack[-count:])
            del stack[-count:]
            stack.append(items)
        elif name == "STOP":
            require(len(stack) == 1, "Invalid final literal stack")
            return stack[0]
        else:
            raise ValueError("Nonliteral opcode forbidden: " + name)
    raise ValueError("Missing literal STOP")


def composition_key(formula):
    atoms = re.findall(r"([A-Z][a-z]?)([0-9.]*)", formula)
    require("".join(e + n for e, n in atoms) == formula, "Unsupported Formula")
    counts = {element: Fraction(number or "1") for element, number in atoms}
    denominator = math.lcm(*(v.denominator for v in counts.values()))
    integers = {e: int(v * denominator) for e, v in counts.items()}
    divisor = math.gcd(*integers.values())
    return tuple(sorted((e, v // divisor) for e, v in integers.items()))


def normalize_text(text):
    return " ".join("\n".join(line for line in text.splitlines()
                    if line.strip() and not line.lstrip().startswith("#")).split())


def verify(metadata_only=False, source_root=None):
    sources = json.loads((PACKAGE / "provenance/sources.json").read_text())
    files = read_csv(PACKAGE / "provenance/files.csv")
    require(len(files) == 15, "Expected exactly 15 selected source artifacts")
    require(len({r["path"] for r in files}) == 15, "Duplicate destination")
    require(sources["shared"]["seed_execution_verified"] is False,
            "Do not upgrade a seed label into execution evidence")
    paths = ["adaptation_data/" + row["path"] for row in files]
    ignored = subprocess.run(["git", "check-ignore", "--", *paths], cwd=ROOT,
                             text=True,
                             capture_output=True, check=True).stdout.splitlines()
    require(set(ignored) == set(paths), "A payload is not ignored by Git")
    tracked = subprocess.check_output(
        ["git", "ls-files", "adaptation_data/local_only"], cwd=ROOT, text=True)
    require(not tracked.strip(), "Restricted payload has entered the Git index")
    for row in files:
        relative = Path(row["path"])
        require(not relative.is_absolute() and ".." not in relative.parts and
                relative.parts[0] == "local_only", "Invalid payload path")
        require(re.fullmatch(r"[0-9a-f]{64}", row["sha256"]), "Invalid SHA256")
        require(row["redistribution_status"] == "unresolved", "License hold changed")
    for match in re.finditer(r"\[[^\]]*\]\(([^)]+)\)",
                             (PACKAGE / "README.md").read_text()):
        link = match[1]
        if not link.startswith(("https://", "http://", "#")):
            require((PACKAGE / link.split("#")[0]).exists(), "Broken link: " + link)
    require((ROOT / "adaptation_data/README.md").exists(), "Root README link missing")
    require("(adaptation_data/README.md)" in (ROOT / "README.md").read_text(),
            "Root README does not link to adaptation data")
    result = {"status": "PASS", "mode": "metadata_only" if metadata_only else "full",
              "payload_files": len(files), "payload_bytes": sum(int(r["bytes"]) for r in files),
              "payloads_ignored_and_not_staged": True, "local_markdown_links": "PASS",
              "redistribution_clearance": "unresolved; no payload release"}
    if metadata_only:
        return result
    inventory = None
    if source_root:
        inventory_path = source_root / "MagGenBench_dataset_inventory.csv"
        require(sha256(inventory_path) == sources["audit"]["inventory_sha256"],
                "Prior inventory changed")
        inventory = {Path(r["file_path"]).as_posix().casefold(): r
                     for r in read_csv(inventory_path)}
        require(sha256(source_root / "MagGenBench_dataset_audit.md") ==
                sources["audit"]["report_sha256"], "Prior audit changed")
    for row in files:
        path = PACKAGE / row["path"]
        require(path.is_file(), "Missing private payload: " + str(path))
        require(path.stat().st_size == int(row["bytes"]) and sha256(path) == row["sha256"],
                "Packaged bytes differ from copy manifest: " + row["path"])
        if path.suffix == ".csv":
            require(len(read_csv(path)) == int(row["records"]), "CSV record count mismatch")
        if source_root:
            original = source_root / row["source_relative_path"]
            baseline = inventory[original.as_posix().casefold()]
            require(sha256(original) == row["sha256"] == baseline["sha256"],
                    "Source or prior audit hash mismatch: " + str(original))
            require(original.stat().st_size == int(row["bytes"]) == int(baseline["size"]),
                    "Source size mismatch")
    shared = {s: read_csv(PACKAGE / p) for s, p in sources["shared"]["files"].items()}
    require({s: len(rows) for s, rows in shared.items()} == {"train": 1139, "val": 142, "test": 145},
            "Shared counts changed")
    all_rows = sum(shared.values(), [])
    require(Counter(r["Source"] for r in all_rows) == {"novamag": 1426}, "Source labels changed")
    require(len({r["material_id"] for r in all_rows}) == 1426, "Duplicate material IDs")
    require(len({r["Row_ID"] for r in all_rows}) == 1426, "Duplicate source-local Row_ID")
    require(len({r["cif"].strip().replace("\r\n", "\n") for r in all_rows}) == 1426,
            "Duplicate original CIF text")
    groups = {s: {composition_key(r["Formula"]) for r in rows} for s, rows in shared.items()}
    require({s: len(v) for s, v in groups.items()} == {"train": 185, "val": 23, "test": 24},
            "Reduced-composition groups changed")
    for a, b in (("train", "val"), ("train", "test"), ("val", "test")):
        require(not groups[a] & groups[b], "Composition-group leakage")
    cf = sources["models"]["crystalformer"]
    variant = read_csv(PACKAGE / cf["files"]["train"])
    excluded = read_csv(PACKAGE / cf["exclusions"])
    original = {r["material_id"]: r for r in shared["train"]}
    require(len(variant) == 1134 and len(excluded) == 5, "CF variant count mismatch")
    require({r["material_id"] for r in variant} == original.keys() -
            {r["material_id"] for r in excluded}, "CF exclusions mismatch")
    differences = []
    for row in variant:
        before = original[row["material_id"]]
        require(all(row[k] == before[k] for k in row if k != "candidate_mag_density"),
                "CF identity/CIF changed")
        if row["candidate_mag_density"] != before["candidate_mag_density"]:
            differences.append(abs(Decimal(row["candidate_mag_density"]) -
                                   Decimal(before["candidate_mag_density"])))
    require(len(differences) == 918 and max(differences) == Decimal("9.7e-17"),
            "CF decimal reserialization no longer matches audit")
    for split in ("val", "test"):
        require(cf["files"][split] == sources["shared"]["files"][split],
                "Do not duplicate unchanged CF validation/test")
    cl = sources["models"]["crystallm"]
    summary = json.loads((PACKAGE / cl["normalization_summary"]).read_text())
    manifest = read_csv(PACKAGE / cl["normalization_manifest"])
    require([(r["split"], r["structure_id"], r["status"]) for r in manifest] ==
            [(s, r["material_id"], "ok") for s, rows in shared.items() for r in rows],
            "Existing normalization provenance differs from shared IDs/splits")
    tokens_dir = PACKAGE / cl["tokens"]
    meta = literal_pickle(tokens_dir / "meta.pkl")
    require(meta["vocab_size"] == 371, "Vocabulary changed")
    token_counts = {}
    for split, rows in shared.items():
        tuples = literal_pickle(PACKAGE / cl["normalized"] / (split + "_normalized_raw.pkl.gz"))
        require([x[0] for x in tuples] == [r["material_id"] for r in rows],
                "Normalized identities/order mismatch")
        require(summary[split] == {"input": len(rows), "normalized": len(rows), "failed": 0,
                "output": "data/magnetic_seed1041/" + split + "_normalized_raw.pkl.gz"},
                "Normalization summary mismatch")
        if split == "test":
            continue
        tokens = array.array("H")
        tokens.frombytes((tokens_dir / (split + ".bin")).read_bytes())
        if sys.byteorder != "little":
            tokens.byteswap()
        require(all(0 <= t < 371 for t in tokens), "Token outside vocabulary")
        decoded = "".join(meta["itos"][int(t)] for t in tokens)
        documents = [d for d in re.split(r"(?m)(?=^data_)", decoded)
                     if d.lstrip().startswith("data_")]
        require(Counter(map(normalize_text, documents)) ==
                Counter(normalize_text(x[1]) for x in tuples), "Token CIF texts differ")
        starts = literal_pickle(tokens_dir / ("starts.pkl" if split == "train" else "starts_val.pkl"))
        require(len(starts) == len(rows) and all(type(i) is int and 0 <= i < len(tokens) for i in starts),
                "Invalid start offsets")
        token_counts[split] = len(tokens)
    require(token_counts == {"train": 830129, "val": 86015}, "Token counts changed")
    expected_paths = {r["path"] for r in files}
    actual_paths = {p.relative_to(PACKAGE).as_posix() for p in (PACKAGE / "local_only").rglob("*")
                    if p.is_file()}
    require(actual_paths == expected_paths, "Unexpected or missing local payload file")
    result.update(shared_counts={s: len(rows) for s, rows in shared.items()},
                  source_labels={"novamag": 1426}, unique_structures=1426,
                  reduced_composition_groups={s: len(v) for s, v in groups.items()},
                  crystalformer_counts={"train": 1134, "val": 142, "test": 145},
                  crystalformer_exclusions=5,
                  preexisting_density_reserialization={"rows": 918, "max_abs_difference": "9.7e-17"},
                  normalized_counts={s: len(rows) for s, rows in shared.items()},
                  token_counts=token_counts, token_document_counts={"train": 1139, "val": 142},
                  sha256_and_counts="PASS", source_inventory_checked=bool(source_root),
                  raw_bytes_preserved=True, unsafe_deserialization_used=False)
    preparation_manifest = PACKAGE / 'preparation/manifest.json'
    if preparation_manifest.exists():
        preparation = json.loads(preparation_manifest.read_text())
        ledger = PACKAGE / 'preparation' / preparation['selection_ledger']['path']
        require(sha256(ledger) == preparation['selection_ledger']['sha256'],
                'Preparation ledger hash mismatch')
        ledger_rows = read_csv(ledger)
        require(len(ledger_rows) == 5203, 'Preparation ledger count changed')
        selected = [r for r in ledger_rows if r['selection_status'] == 'retained']
        require({r['material_id'] for r in selected} == {r['material_id'] for r in all_rows},
                'Preparation membership differs from shared splits')
        require(Counter(r['split'] for r in selected) == {'train': 1139, 'val': 142, 'test': 145},
                'Preparation split assignments changed')
        require(subprocess.run(['git', 'check-ignore', ledger.relative_to(ROOT).as_posix()],
                               cwd=ROOT, capture_output=True).returncode == 0,
                'Record-level preparation evidence is not ignored')
        require(not subprocess.check_output(['git', 'ls-files', ledger.relative_to(ROOT).as_posix()],
                                            cwd=ROOT).strip(), 'Preparation ledger is staged')
        result['preparation_ledger_records'] = len(ledger_rows)
        result['preparation_retained_records'] = len(selected)
        result['preparation_ledger_ignored'] = True
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--write-report", action="store_true",
                        help="Save measured results to provenance/verification.json")
    args = parser.parse_args()
    result = verify(args.metadata_only, args.source_root)
    if args.write_report:
        require(not args.metadata_only, "Do not overwrite full evidence with metadata-only results")
        (PACKAGE / "provenance/verification.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
