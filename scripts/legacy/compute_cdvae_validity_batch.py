import os
import json
import argparse
from pathlib import Path
import multiprocessing as mp
import numpy as np

from pymatgen.core import Structure

from eval_utils import smact_validity, structure_validity


class Crystal:
    def __init__(self, structure: Structure):
        self.structure = structure
        self.constructed = structure is not None

        if self.constructed:
            self.atom_types = [site.specie.number for site in self.structure]
            self.get_composition()
            self.get_validity()
        else:
            self.comp_valid = False
            self.struct_valid = False
            self.valid = False

    def get_composition(self):
        from collections import Counter
        elem_counter = Counter(self.atom_types)

        elems = list(elem_counter.keys())
        counts = list(elem_counter.values())

        counts = np.array(counts)
        counts = counts / np.gcd.reduce(counts)

        self.elems = elems
        self.comps = tuple(counts.astype(int).tolist())

    def get_validity(self):
        self.comp_valid = smact_validity(self.elems, self.comps)
        self.struct_valid = structure_validity(self.structure)
        self.valid = self.comp_valid and self.struct_valid


def load_cif(path):
    try:
        return Structure.from_file(str(path))
    except Exception:
        return None


def process_cif(path):
    struct = load_cif(path)
    if struct is None:
        return None
    try:
        return Crystal(struct)
    except:
        return None


def compute_metrics(crystals):
    if not crystals:
        return {"comp_valid": 0, "struct_valid": 0, "valid": 0}

    comp_valid = np.mean([c.comp_valid for c in crystals])
    struct_valid = np.mean([c.struct_valid for c in crystals])
    valid = np.mean([c.valid for c in crystals])

    return {
        "comp_valid": float(comp_valid),
        "struct_valid": float(struct_valid),
        "valid": float(valid),
    }


def run_for_model(model_dir, num_workers=16):
    model_dir = Path(model_dir)
    model_name = model_dir.name

    cif_files = list(model_dir.rglob("*.cif"))

    print(f"\n=== {model_name} ===")
    print(f"Found CIFs: {len(cif_files)}")

    with mp.Pool(num_workers) as pool:
        crystals = pool.map(process_cif, cif_files)

    crystals = [c for c in crystals if c is not None]

    print(f"Parsed crystals: {len(crystals)}")

    metrics = compute_metrics(crystals)

    result = {
        "model": model_name,
        "n_cifs": len(cif_files),
        "n_parsed": len(crystals),
        "cdvae_validity": metrics,
    }

    out_path = model_dir / "cdvae_validity_from_cifs.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dirs", nargs="+", required=True)
    parser.add_argument("--num-workers", type=int, default=16)
    args = parser.parse_args()

    all_results = []

    for d in args.dirs:
        res = run_for_model(d, args.num_workers)
        all_results.append(res)

    with open("outputs_balanced/cdvae_validity_summary_from_cifs.json", "w") as f:
        json.dump(all_results, f, indent=2)


if __name__ == "__main__":
    main()