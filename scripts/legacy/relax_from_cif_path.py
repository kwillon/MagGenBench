import warnings
warnings.simplefilter("ignore")

import os
import json
import traceback
from pathlib import Path
from time import time

import pandas as pd
from tqdm import tqdm

from pymatgen.core import Structure
from pymatgen.io.ase import AseAtomsAdaptor

from ase.optimize import FIRE
from ase.filters import FrechetCellFilter
from ase.constraints import FixSymmetry


def make_mattersim_calc(device="cuda"):
    """
    MatterSim ASE calculator.
    Requires installed mattersim package.
    """
    from mattersim.forcefield.potential import MatterSimCalculator
    return MatterSimCalculator(device=device)


def make_orb_calc(model_path, device="cuda"):
    from orb_models.forcefield import pretrained
    from orb_models.forcefield.calculator import ORBCalculator

    orbff = pretrained.orb_v2(model_path, device=device)
    calc = ORBCalculator(orbff, device=device)
    return calc


def make_matgl_calc(model_path, device="cuda"):
    import matgl
    from matgl.ext.ase import PESCalculator

    pot = matgl.load_model(model_path, device=device)
    calc = PESCalculator(pot)
    return calc


def make_mace_calc(model_path, device="cuda", default_dtype="float64"):
    from mace.calculators import mace_mp

    calc = mace_mp(
        model=model_path,
        dispersion=False,
        default_dtype=default_dtype,
        device=device,
    )
    return calc


def make_dp_calc(model_path):
    from deepmd.calculator import DP
    return DP(model_path)


def make_calc(model, model_path=None, device="cuda"):
    if model == "mattersim":
        return make_mattersim_calc(device=device)

    if model == "orb":
        return make_orb_calc(model_path=model_path, device=device)

    if model == "matgl":
        return make_matgl_calc(model_path=model_path, device=device)

    if model == "mace":
        return make_mace_calc(model_path=model_path, device=device)

    if model == "dp":
        return make_dp_calc(model_path=model_path)

    raise ValueError(f"Unknown model: {model}")


def structure_to_cif_string(structure):
    """
    Store relaxed structure as CIF string, not as dict.
    This is easier to read later with Structure.from_str(..., fmt='cif').
    """
    return structure.to(fmt="cif")


def relax_one_structure(
    structure,
    calc,
    do_relaxation=True,
    fmax=0.05,
    steps=300,
    fixsymmetry=False,
):
    adaptor = AseAtomsAdaptor()

    atoms = adaptor.get_atoms(structure)
    atoms.calc = calc

    initial_energy_total = float(atoms.get_potential_energy())
    n_atoms = len(atoms)

    converged = None
    n_steps = 0

    if do_relaxation:
        if fixsymmetry:
            try:
                atoms.set_constraint(FixSymmetry(atoms))
            except Exception:
                pass

        optimizer_input = FrechetCellFilter(atoms)
        optimizer = FIRE(optimizer_input)

        converged = bool(optimizer.run(fmax=fmax, steps=steps))
        n_steps = optimizer.nsteps

        final_energy_total = float(atoms.get_potential_energy())
        relaxed_structure = adaptor.get_structure(atoms)
    else:
        final_energy_total = initial_energy_total
        relaxed_structure = structure

    initial_energy_per_atom = initial_energy_total / n_atoms
    final_energy_per_atom = final_energy_total / n_atoms
    delta_e_per_atom = final_energy_per_atom - initial_energy_per_atom

    return {
        "relax_success": True,
        "relax_error": "",
        "relax_converged": converged,
        "relax_n_steps": n_steps,
        "n_atoms": n_atoms,
        "initial_energy_total_eV": initial_energy_total,
        "final_energy_total_eV": final_energy_total,
        "initial_energy_per_atom_eV": initial_energy_per_atom,
        "final_energy_per_atom_eV": final_energy_per_atom,
        "delta_e_per_atom_eV": delta_e_per_atom,
        "relaxed_cif": structure_to_cif_string(relaxed_structure),
        "relaxed_formula": relaxed_structure.composition.reduced_formula,
    }


def main(args):
    input_csv = Path(args.input_csv)
    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_csv, low_memory=False)

    if args.cif_col not in df.columns:
        raise ValueError(
            f"Column '{args.cif_col}' not found. Available columns: {list(df.columns)}"
        )

    if args.limit is not None:
        df = df.head(args.limit).copy()

    print("Input:", input_csv)
    print("Output:", output_csv)
    print("Rows:", len(df))
    print("CIF column:", args.cif_col)
    print("Calculator:", args.model)
    print("Device:", args.device)
    print("Relaxation:", args.relaxation)
    print("fmax:", args.fmax)
    print("steps:", args.steps)
    print("fixsymmetry:", args.fixsymmetry)

    calc = make_calc(
        model=args.model,
        model_path=args.model_path,
        device=args.device,
    )

    prefix = args.prefix
    out = df.copy()

    result_columns = [
        f"{prefix}_relax_success",
        f"{prefix}_relax_error",
        f"{prefix}_relax_converged",
        f"{prefix}_relax_n_steps",
        f"{prefix}_n_atoms",
        f"{prefix}_initial_energy_total_eV",
        f"{prefix}_final_energy_total_eV",
        f"{prefix}_initial_energy_per_atom_eV",
        f"{prefix}_final_energy_per_atom_eV",
        f"{prefix}_delta_e_per_atom_eV",
        f"{prefix}_relaxed_cif",
        f"{prefix}_relaxed_formula",
    ]

    for col in result_columns:
        out[col] = ""

    start = time()

    for idx, row in tqdm(out.iterrows(), total=len(out)):
        cif_path = str(row[args.cif_col]).strip()

        try:
            if not cif_path or cif_path.lower() in {"nan", "none", "null"}:
                raise ValueError("empty_cif_path")

            if not Path(cif_path).exists():
                raise FileNotFoundError(f"cif_not_found: {cif_path}")

            structure = Structure.from_file(cif_path)

            result = relax_one_structure(
                structure=structure,
                calc=calc,
                do_relaxation=args.relaxation,
                fmax=args.fmax,
                steps=args.steps,
                fixsymmetry=args.fixsymmetry,
            )

        except Exception as e:
            result = {
                "relax_success": False,
                "relax_error": str(e).replace("\n", " ")[:500],
                "relax_converged": False,
                "relax_n_steps": 0,
                "n_atoms": "",
                "initial_energy_total_eV": "",
                "final_energy_total_eV": "",
                "initial_energy_per_atom_eV": "",
                "final_energy_per_atom_eV": "",
                "delta_e_per_atom_eV": "",
                "relaxed_cif": "",
                "relaxed_formula": "",
            }

            if args.verbose_errors:
                print("\nERROR for row:", idx)
                print("sample_uid:", row.get("sample_uid", ""))
                print("cif_path:", cif_path)
                traceback.print_exc()

        for key, value in result.items():
            out.at[idx, f"{prefix}_{key}"] = value

        if args.checkpoint_every and (idx + 1) % args.checkpoint_every == 0:
            checkpoint_path = output_csv.with_suffix(".checkpoint.csv")
            out.to_csv(checkpoint_path, index=False)
            print(f"\nCheckpoint saved: {checkpoint_path}")

    out.to_csv(output_csv, index=False)

    end = time()
    print("\nSaved:", output_csv)
    print(f"Time: {(end - start) / 60:.2f} min")

    print("\nRelax success counts:")
    print(out[f"{prefix}_relax_success"].value_counts(dropna=False))

    print("\nConverged counts:")
    print(out[f"{prefix}_relax_converged"].value_counts(dropna=False))

    print("\nEnergy columns:")
    print(out[
        [
            f"{prefix}_initial_energy_per_atom_eV",
            f"{prefix}_final_energy_per_atom_eV",
            f"{prefix}_delta_e_per_atom_eV",
        ]
    ].head())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-csv", required=True)

    parser.add_argument("--cif-col", default="cif_path")

    parser.add_argument(
        "--model",
        choices=["mattersim", "orb", "matgl", "mace", "dp"],
        default="mattersim",
    )
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--device", default="cuda")

    parser.add_argument("--prefix", default="mattersim")

    parser.add_argument("--relaxation", action="store_true")
    parser.add_argument("--fmax", type=float, default=0.05)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--fixsymmetry", action="store_true")

    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--checkpoint-every", type=int, default=100)
    parser.add_argument("--verbose-errors", action="store_true")

    args = parser.parse_args()
    main(args)