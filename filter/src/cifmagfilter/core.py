from __future__ import annotations

import math
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .reference import (
    select_numeric_features as _select_numeric_features,
    robust_fit as _reference_robust_fit,
    robust_transform as _reference_robust_transform,
    knn_distance as _reference_knn_distance,
    knn_distance_training as _reference_knn_distance_training,
    finish_scores as _reference_finish_scores,
    score_against_references as _score_against_references,
    score_reference_training as _score_reference_training,
)

try:
    from pymatgen.core import Element, Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    from pymatgen.analysis.bond_valence import BVAnalyzer, calculate_bv_sum, calculate_bv_sum_unordered
    from pymatgen.analysis.local_env import CrystalNN
except Exception:
    Element = Structure = SpacegroupAnalyzer = BVAnalyzer = CrystalNN = None
    calculate_bv_sum = calculate_bv_sum_unordered = None

try:
    from smact.screening import smact_validity
except Exception:
    smact_validity = None

MAGNETIC_3D = {"Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu"}
WEAK_4D5D = {"Mo", "Tc", "Ru", "Rh", "Pd", "W", "Re", "Os", "Ir", "Pt"}
RARE_EARTH = {"Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb"}
ACTINIDES = {"U", "Np", "Pu", "Am", "Cm"}
LIGANDS = {"O", "F", "Cl", "Br", "I", "S", "Se", "Te", "N", "P", "As", "Sb", "B", "C", "Si", "Ge"}
STRONG_ANIONS = {"O", "F", "Cl", "Br", "I", "S", "Se", "Te", "N"}
F3_COUNT = {"Ce": 1, "Pr": 2, "Nd": 3, "Pm": 4, "Sm": 5, "Eu": 6, "Gd": 7,
            "Tb": 8, "Dy": 9, "Ho": 10, "Er": 11, "Tm": 12, "Yb": 13}
ELEMENTAL_PRIOR = {
    "Fe": .95, "Co": .95, "Ni": .85, "Mn": .85, "Cr": .70, "V": .45, "Ti": .25, "Cu": .30,
    "Gd": .95, "Tb": .90, "Dy": .90, "Ho": .85, "Er": .80, "Nd": .80, "Pr": .75,
    "Sm": .70, "Eu": .75, "Ce": .45, "Yb": .35, "U": .70, "Np": .65, "Pu": .60,
    "Ru": .35, "Rh": .20, "Pd": .12, "Os": .30, "Ir": .25, "Pt": .10, "Mo": .18,
    "W": .12, "Re": .25,
}
META_COLUMNS = {
    "dataset", "structure_id", "source_path", "formula_reduced", "label_order", "magnetic_binary",
    "source_group", "is_known_ordering", "is_generator", "parse_success", "parse_error",
}

# Public neutral terminology for legacy canonical column names. The raw column names
# are retained so the historical extraction does not need to be rerun.
PUBLIC_DESCRIPTOR_ALIASES = {
    "magnetic_center__mean_center_confidence": "magnetic_center__mean_center_support_score",
    "magnetic_center__max_center_confidence": "magnetic_center__max_center_support_score",
    "magnetic_center__fraction_centers_4d5d_weak": "magnetic_center__fraction_centers_4d5d",
    "magnetic_pair__magnetic_sublattice_connected_fraction": "magnetic_pair__candidate_center_pair_graph_lcc_fraction",
    "pair_motif__bridge_chemistry_diversity": "pair_motif__bridge_chemistry_evenness",
    "pair_motif__pair_family_diversity": "pair_motif__pair_family_evenness",
}


def public_descriptor_name(raw_name: str) -> str:
    return PUBLIC_DESCRIPTOR_ALIASES.get(raw_name, raw_name)


def clip01(x: float, default: float = 0.0) -> float:
    try:
        x = float(x)
    except Exception:
        return default
    return float(np.clip(x, 0.0, 1.0)) if np.isfinite(x) else default


def as_float(x: Any, default: float = np.nan) -> float:
    try:
        y = float(x)
        return y if np.isfinite(y) else default
    except Exception:
        return default


def nanmean(values: list[float], default: float = np.nan) -> float:
    x = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    return float(x.mean()) if len(x) else default


def soft_or(values: list[float]) -> float:
    x = pd.to_numeric(pd.Series(values), errors="coerce").dropna().to_numpy(float)
    if len(x) == 0:
        return 0.0
    x = np.clip(x, 0.0, 1.0)
    return float(1.0 - np.prod(1.0 - x))


def element_symbol(site) -> str:
    try:
        return str(site.specie.symbol)
    except Exception:
        elems = list(site.species.elements)
        return str(elems[0].symbol) if elems else "X"


def moment_family(sym: str) -> str:
    if sym in MAGNETIC_3D:
        return "3d"
    if sym in WEAK_4D5D:
        return "4d5d_weak"
    if sym in RARE_EARTH:
        return "rare_earth"
    if sym in ACTINIDES:
        return "actinide"
    return "other"


def is_moment_element(sym: str) -> bool:
    return moment_family(sym) != "other"


def radius(sym: str, metallic: bool = False) -> float:
    try:
        e = Element(sym)
        attrs = ["metallic_radius", "atomic_radius", "atomic_radius_calculated", "covalent_radius"] if metallic else [
            "covalent_radius", "atomic_radius", "atomic_radius_calculated"
        ]
        for attr in attrs:
            r = getattr(e, attr, None)
            if r is not None:
                return float(r)
    except Exception:
        pass
    return 1.3


def transition_d_count(sym: str, ox: float) -> float:
    if sym not in MAGNETIC_3D | WEAK_4D5D or not np.isfinite(ox):
        return np.nan
    try:
        group = Element(sym).group
        return float(group - ox) if group is not None else np.nan
    except Exception:
        return np.nan


def rare_earth_f_count(sym: str, ox: float) -> float:
    if sym not in RARE_EARTH or not np.isfinite(ox) or sym not in F3_COUNT:
        return np.nan
    return float(np.clip(F3_COUNT[sym] + (3.0 - ox), 0.0, 14.0))


def open_shell_score(d_count: float, f_count: float) -> float:
    vals = []
    if np.isfinite(d_count):
        vals.append(float(0.2 < d_count < 9.8))
    if np.isfinite(f_count):
        vals.append(float(0.2 < f_count < 13.8))
    return nanmean(vals)


def closed_shell_suppression(sym: str, d_count: float, f_count: float, ox: float) -> float:
    s = 0.0
    if np.isfinite(d_count) and (d_count <= .2 or d_count >= 9.8):
        s = 1.0
    if np.isfinite(f_count) and (f_count <= .2 or f_count >= 13.8):
        s = 1.0
    if sym in {"Zn", "Cd", "Hg"}:
        s = 1.0
    if sym in {"Ag", "Au"}:
        s = max(s, .8)
    if sym in {"Pd", "Pt"} and (not np.isfinite(ox) or ox in {0.0, 2.0, 4.0}):
        s = max(s, .45)
    if sym in {"Mo", "W"} and np.isfinite(ox) and ox >= 5.5:
        s = 1.0
    if sym == "Ti" and np.isfinite(ox) and ox >= 3.8:
        s = 1.0
    if sym == "V" and np.isfinite(ox) and ox >= 4.8:
        s = 1.0
    if sym == "Ce" and np.isfinite(ox) and ox >= 3.8:
        s = 1.0
    if sym == "Yb" and np.isfinite(ox) and ox <= 2.2:
        s = 1.0
    return clip01(s)


def load_site_priors(path: str | Path | None) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    for c in ["dataset", "structure_id"]:
        if c in df.columns:
            df[c] = df[c].astype(str)
    if "dataset" in df.columns:
        df["dataset"] = df["dataset"].str.lower()
    return df


def prior_value(row: pd.Series | None, names: list[str]) -> float:
    if row is None:
        return np.nan
    lower = {str(c).lower(): c for c in row.index}
    for name in names:
        c = name if name in row.index else lower.get(name.lower())
        if c is not None:
            x = as_float(row.get(c))
            if np.isfinite(x):
                return x
    return np.nan


def site_prior(priors: pd.DataFrame, dataset: str, structure_id: str, idx: int, sym: str) -> pd.Series | None:
    if priors.empty or not {"dataset", "structure_id"}.issubset(priors.columns):
        return None
    sub = priors[(priors["dataset"] == dataset.lower()) & (priors["structure_id"] == str(structure_id))]
    if sub.empty:
        return None
    if "site_index" in sub.columns:
        m = pd.to_numeric(sub["site_index"], errors="coerce").eq(idx)
        if m.any():
            return sub[m].iloc[0]
    if "element" in sub.columns:
        m = sub["element"].astype(str).eq(sym)
        if m.any():
            return sub[m].iloc[0]
    return None


def estimate_oxidation_states(structure: Structure) -> list[float]:
    if BVAnalyzer is not None:
        try:
            vals = BVAnalyzer().get_valences(structure)
            if len(vals) == len(structure):
                return [as_float(x) for x in vals]
        except Exception:
            pass
    try:
        guesses = structure.composition.oxi_state_guesses()
        if guesses:
            g = guesses[0]
            return [as_float(g.get(element_symbol(site), np.nan)) for site in structure]
    except Exception:
        pass
    return [np.nan] * len(structure)




def min_interatomic_distance(structure: Structure) -> float:
    if len(structure) < 2:
        return np.nan
    best = np.inf
    for i in range(len(structure)):
        for j in range(i + 1, len(structure)):
            try:
                best = min(best, float(structure.get_distance(i, j)))
            except Exception:
                pass
    return float(best) if np.isfinite(best) else np.nan


def structural_features(structure: Structure, symprec: float = 0.1, min_dist_warning: float = 0.6,
                large_nsites: int = 300) -> dict[str, Any]:
    n = len(structure)
    occ_not1 = 0
    disordered = 0
    for site in structure:
        try:
            occ = float(sum(site.species.values()))
            occ_not1 += int(round(occ, 6) != 1.0)
            disordered += int(not site.is_ordered)
        except Exception:
            pass
    mind = min_interatomic_distance(structure)
    sym_failed = 0
    sg = sg_symbol = cs = None
    try:
        sga = SpacegroupAnalyzer(structure, symprec=symprec)
        sg = int(sga.get_space_group_number())
        sg_symbol = str(sga.get_space_group_symbol())
        cs = str(sga.get_crystal_system())
    except Exception:
        sym_failed = 1
    return {
        "n_sites": n,
        "n_elements": int(len(structure.composition.elements)),
        "volume_per_atom": float(structure.volume / max(n, 1)),
        "density": as_float(structure.density),
        "min_interatomic_distance": mind,
        "short_contact_warning": int(np.isfinite(mind) and mind < min_dist_warning),
        "has_disorder": int(disordered > 0),
        "occupancy_not_1_count": int(occ_not1),
        "too_large_structure": int(n > large_nsites),
        "symmetry_failed": int(sym_failed),
        # Symmetry metadata are retained for reporting/visualization but are not
        # part of the quantitative reference-space feature vector.
        "spacegroup_number": sg if sg is not None else np.nan,
        "spacegroup_symbol": sg_symbol,
        "crystal_system": cs,
    }


def _site_oxi(site) -> float:
    try:
        return as_float(getattr(site.specie, "oxi_state", np.nan))
    except Exception:
        return np.nan


def chemical_evidence(
    structure: Structure,
    dataset: str,
    structure_id: str,
    source: Path,
    min_oxidation_coverage: float = 1.0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    bv_struct = None
    bv_success = 0
    try:
        bv_struct = BVAnalyzer().get_oxi_state_decorated_structure(structure.copy()) if BVAnalyzer else None
        bv_success = int(bv_struct is not None)
    except Exception:
        bv_struct = None

    ox_guess_success = 0
    ox_guess_count = 0
    comp_guess = None
    try:
        guesses = structure.composition.reduced_composition.oxi_state_guesses()
        ox_guess_success = 1
        ox_guess_count = len(guesses)
        comp_guess = guesses[0] if guesses else None
    except Exception:
        pass

    rows = []
    residuals = []
    mag_residuals = []
    anion_residuals = []
    bv_ok = 0
    decorated = bv_struct if bv_struct is not None else structure
    for i, site in enumerate(structure):
        sym = element_symbol(site)
        ox = _site_oxi(bv_struct[i]) if bv_struct is not None else np.nan
        if not np.isfinite(ox) and comp_guess is not None:
            ox = as_float(comp_guess.get(sym, np.nan))
        residual = np.nan
        if bv_struct is not None and calculate_bv_sum is not None:
            try:
                nn = bv_struct.get_neighbors(bv_struct[i], 3.5)
                bsum = float(calculate_bv_sum(bv_struct[i], nn)) if bv_struct[i].is_ordered else float(calculate_bv_sum_unordered(bv_struct[i], nn))
                residual = abs(bsum - ox) if np.isfinite(ox) else np.nan
                if np.isfinite(residual):
                    bv_ok += 1
                    residuals.append(residual)
                    if is_moment_element(sym):
                        mag_residuals.append(residual)
                    if sym in STRONG_ANIONS:
                        anion_residuals.append(residual)
            except Exception:
                pass
        rows.append({"dataset": dataset, "structure_id": structure_id, "source_path": str(source),
                     "site_index": i, "element": sym, "oxidation_state": ox, "bv_residual": residual,
                     "oxidation_guess_confidence": 0.9 if bv_struct is not None and np.isfinite(ox) else (0.5 if np.isfinite(ox) else 0.0)})

    site_df = pd.DataFrame(rows)
    ox_vals = pd.to_numeric(site_df.get("oxidation_state", pd.Series(dtype=float)), errors="coerce")
    oxidation_state_coverage = float(ox_vals.notna().mean()) if len(ox_vals) else np.nan
    # Do not silently treat unknown oxidation states as zero charge.  The
    # neutrality score is reported only when the requested fraction of sites
    # has an assigned oxidation state (default: complete site-wise coverage).
    if np.isfinite(oxidation_state_coverage) and oxidation_state_coverage >= float(min_oxidation_coverage):
        charge = float(ox_vals.dropna().sum())
        charge_consistency = 1.0 / (1.0 + abs(charge))
    else:
        charge = np.nan
        charge_consistency = np.nan

    cn_vals = []
    ligand_vals = []
    magnetic_neighbor_vals = []
    opposite_vals = []
    if bv_struct is not None and CrystalNN is not None:
        try:
            cnn = CrystalNN()
            for i, site in enumerate(bv_struct):
                try:
                    nn_info = cnn.get_nn_info(bv_struct, i)
                    cn_vals.append(float(cnn.get_cn(bv_struct, i)))
                    els, opp_w, total_w = [], 0.0, 0.0
                    ox_i = _site_oxi(site)
                    for nn in nn_info:
                        nsite = nn["site"]
                        w = float(nn.get("weight", 1.0))
                        sym = element_symbol(nsite)
                        els.append(sym)
                        total_w += w
                        ox_j = _site_oxi(nsite)
                        if np.isfinite(ox_i) and np.isfinite(ox_j) and ox_i * ox_j < 0:
                            opp_w += w
                    if els:
                        ligand_vals.append(sum(e in LIGANDS for e in els) / len(els))
                        magnetic_neighbor_vals.append(sum(is_moment_element(e) for e in els) / len(els))
                    if total_w > 0:
                        opposite_vals.append(opp_w / total_w)
                except Exception:
                    pass
        except Exception:
            pass

    smact_valid = smact_mixed = np.nan
    if smact_validity is not None:
        formula = structure.composition.reduced_formula
        try:
            smact_valid = float(bool(smact_validity(formula, include_alloys=True)))
        except Exception:
            try:
                smact_valid = float(bool(smact_validity(formula)))
            except Exception:
                pass
        try:
            smact_mixed = float(bool(smact_validity(formula, include_alloys=True, mixed_valence=True)))
        except Exception:
            pass

    def mean_or_nan(x):
        return float(np.mean(x)) if x else np.nan

    def frac_le(x, thr=0.5):
        return float(np.mean(np.asarray(x) <= thr)) if x else np.nan

    summary = {
        "bv_success": int(bv_success),
        "oxi_guess_success": int(ox_guess_success),
        "oxi_guess_count": int(ox_guess_count),
        "oxidation_state_coverage": oxidation_state_coverage,
        "charge_balance_consistency": charge_consistency,
        "bv_residual_mean": mean_or_nan(residuals),
        "bv_residual_median": float(np.median(residuals)) if residuals else np.nan,
        "bv_residual_max": float(np.max(residuals)) if residuals else np.nan,
        "fraction_sites_bv_consistent": frac_le(residuals),
        "fraction_magnetic_sites_bv_consistent": frac_le(mag_residuals),
        "fraction_anion_sites_bv_consistent": frac_le(anion_residuals),
        "fraction_sites_bv_successful": float(bv_ok / max(len(structure), 1)),
        "mean_cn_crystalnn": mean_or_nan(cn_vals),
        "mean_ligand_fraction_in_nn": mean_or_nan(ligand_vals),
        "mean_magnetic_neighbor_fraction_in_nn": mean_or_nan(magnetic_neighbor_vals),
        "mean_opposite_sign_fraction_weighted": mean_or_nan(opposite_vals),
        "smact_valid": smact_valid,
        "smact_valid_mixed_valence": smact_mixed,
    }
    return site_df, summary


def merge_site_priors(auto_priors: pd.DataFrame, external_priors: pd.DataFrame, dataset: str, structure_id: str) -> pd.DataFrame:
    if external_priors.empty:
        return auto_priors
    ext = external_priors.copy()
    if {"dataset", "structure_id"}.issubset(ext.columns):
        ext = ext[(ext["dataset"].astype(str).str.lower() == dataset.lower()) & (ext["structure_id"].astype(str) == str(structure_id))]
    if ext.empty:
        return auto_priors
    return pd.concat([ext, auto_priors], ignore_index=True, sort=False)

def local_environment(structure: Structure, idx: int, cutoff: float) -> dict[str, float]:
    site = structure[idx]
    try:
        neigh = structure.get_neighbors(site, cutoff, include_index=True)
    except TypeError:
        neigh = structure.get_neighbors(site, cutoff)
    total = ligand = metal = moment = 0
    nearest = np.nan
    for nn in neigh:
        j = getattr(nn, "index", None)
        if j is None or int(j) == idx:
            continue
        sym = element_symbol(structure[int(j)])
        dist = as_float(getattr(nn, "nn_distance", np.nan))
        total += 1
        if sym in LIGANDS:
            ligand += 1
        else:
            metal += 1
        if is_moment_element(sym):
            moment += 1
            nearest = dist if not np.isfinite(nearest) else min(nearest, dist)
    if total == 0:
        return {"neighbor_count": 0, "ligand_fraction": 0.0, "metal_fraction": 0.0,
                "moment_neighbor_fraction": 0.0, "nearest_moment_distance": np.nan}
    return {"neighbor_count": total, "ligand_fraction": ligand / total, "metal_fraction": metal / total,
            "moment_neighbor_fraction": moment / total, "nearest_moment_distance": nearest}


def site_score(sym: str, ox: float, prior: pd.Series | None, env: dict[str, float], comp: dict[str, float]) -> dict[str, float]:
    d = prior_value(prior, ["d_electron_count", "mean_d_electron_count"])
    f = prior_value(prior, ["f_electron_count", "mean_f_electron_count"])
    if not np.isfinite(d):
        d = transition_d_count(sym, ox)
    if not np.isfinite(f):
        f = rare_earth_f_count(sym, ox)
    open_s = open_shell_score(d, f)
    bv_res = prior_value(prior, ["bv_residual", "site_bv_residual", "bond_valence_residual"])
    bv_score = np.nan if not np.isfinite(bv_res) else clip01(1.0 - (bv_res - .5) / 1.5) if bv_res > .5 else 1.0
    old_support = prior_value(prior, ["site_support_score", "magnetic_site_score", "magnetic_support_score"])
    old_support = clip01(old_support) if np.isfinite(old_support) else np.nan
    ligand_coord = clip01(env["ligand_fraction"])
    metal_env = nanmean([env["metal_fraction"], comp["metal_fraction"], env["moment_neighbor_fraction"]], 0.0)
    suppression = closed_shell_suppression(sym, d, f, ox)
    ionic = open_s * nanmean([bv_score, old_support, ligand_coord]) if np.isfinite(open_s) else np.nan
    metallic = ELEMENTAL_PRIOR.get(sym, 0.0) * nanmean([metal_env, 1.0 - comp["ligand_fraction"]], 0.0)
    re_score = 0.0
    if sym in RARE_EARTH:
        f_open = 1.0 if np.isfinite(f) and .2 < f < 13.8 else np.nan
        re_score = ELEMENTAL_PRIOR.get(sym, .5) * nanmean([f_open, .7, metal_env], 0.0)
    factor = .05 if suppression >= .95 else 1.0 - .75 * suppression
    effective = soft_or([
        clip01(ionic) * factor if np.isfinite(ionic) else np.nan,
        clip01(metallic) * factor,
        clip01(re_score) * factor,
    ])
    return {"oxidation_state": ox, "d_electron_count": d, "f_electron_count": f, "open_shell_score": open_s,
            "ionic_score": ionic, "metallic_score": metallic, "rare_earth_score": re_score,
            "closed_shell_suppression": suppression, "center_confidence": effective}


def composition_stats(structure: Structure) -> dict[str, float]:
    syms = [element_symbol(s) for s in structure]
    n = max(len(syms), 1)
    ligand = sum(s in LIGANDS for s in syms) / n
    moment = sum(is_moment_element(s) for s in syms) / n
    return {"ligand_fraction": ligand, "metal_fraction": 1.0 - ligand, "moment_element_fraction": moment}


def build_magnetic_centers(structure: Structure, dataset: str, structure_id: str, source: Path,
                priors: pd.DataFrame, neighbor_cutoff: float) -> tuple[pd.DataFrame, dict[str, Any]]:
    comp = composition_stats(structure)
    ox_auto = estimate_oxidation_states(structure)
    rows = []
    for i, site in enumerate(structure):
        sym = element_symbol(site)
        pr = site_prior(priors, dataset, structure_id, i, sym)
        ox = prior_value(pr, ["oxidation_state", "oxi_state", "assigned_oxi_state", "bv_oxidation_state"])
        if not np.isfinite(ox):
            ox = ox_auto[i]
        env = local_environment(structure, i, neighbor_cutoff)
        sc = site_score(sym, ox, pr, env, comp)
        rows.append({"dataset": dataset, "structure_id": structure_id, "source_path": str(source), "site_index": i,
                     "element": sym, "moment_family": moment_family(sym), **comp, **env, **sc,
                     "is_magnetic_center": int(sc["center_confidence"] >= .25)})
    df = pd.DataFrame(rows)
    magnetic = df[df["is_magnetic_center"].eq(1)] if len(df) else df
    summary = {
        "n_sites": len(df), "n_magnetic_centers": len(magnetic),
        "fraction_magnetic_centers": len(magnetic) / max(len(df), 1),
        "mean_center_confidence": as_float(df["center_confidence"].mean(), 0.0) if len(df) else 0.0,
        "max_center_confidence": as_float(df["center_confidence"].max(), 0.0) if len(df) else 0.0,
        "mean_ionic_score": as_float(df["ionic_score"].mean(), 0.0) if len(df) else 0.0,
        "mean_metallic_score": as_float(df["metallic_score"].mean(), 0.0) if len(df) else 0.0,
        "mean_rare_earth_score": as_float(df["rare_earth_score"].mean(), 0.0) if len(df) else 0.0,
        "mean_closed_shell_suppression": as_float(df["closed_shell_suppression"].mean(), 0.0) if len(df) else 0.0,
        "composition_ligand_fraction": comp["ligand_fraction"],
        "composition_metal_fraction": comp["metal_fraction"],
        "composition_moment_element_fraction": comp["moment_element_fraction"],
    }
    for fam in ["3d", "4d5d_weak", "rare_earth", "actinide"]:
        summary[f"fraction_centers_{fam}"] = float(magnetic["moment_family"].eq(fam).mean()) if len(magnetic) else 0.0
    return df, summary



def bond_cutoff(a: str, b: str, scale: float) -> float:
    return scale * (radius(a) + radius(b))


def vector_from_to(structure: Structure, i: int, j: int) -> tuple[float, np.ndarray]:
    si, sj = structure[i], structure[j]
    try:
        d, image = si.distance_and_image(sj)
        image = np.asarray(image, dtype=float)
    except Exception:
        try:
            d, image = structure.lattice.get_distance_and_image(si.frac_coords, sj.frac_coords)
            image = np.asarray(image, dtype=float)
        except Exception:
            best_d, image = np.inf, np.zeros(3)
            for a in (-1, 0, 1):
                for b in (-1, 0, 1):
                    for c in (-1, 0, 1):
                        img = np.array([a, b, c], dtype=float)
                        vec = structure.lattice.get_cartesian_coords(sj.frac_coords + img - si.frac_coords)
                        dd = float(np.linalg.norm(vec))
                        if dd < best_d:
                            best_d, image = dd, img
            d = best_d
    vec = structure.lattice.get_cartesian_coords(sj.frac_coords + image - si.frac_coords)
    return float(d), np.asarray(vec, dtype=float)


def angle_between(v1: np.ndarray, v2: np.ndarray) -> float:
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 <= 1e-12 or n2 <= 1e-12:
        return np.nan
    x = float(np.dot(v1, v2) / (n1 * n2))
    return float(np.degrees(np.arccos(np.clip(x, -1.0, 1.0))))


def ligand_bridge_map(structure: Structure, centers: list[int], info: dict[int, Any], bond_scale: float,
                      max_mx_distance: float = 3.5, tol90: float = 18.0, tol180: float = 35.0) -> dict[tuple[int, int], list[dict[str, Any]]]:
    out: dict[tuple[int, int], list[dict[str, Any]]] = {}
    center_set = set(centers)
    for k, site in enumerate(structure):
        if k in center_set:
            continue
        x = element_symbol(site)
        if x not in LIGANDS:
            continue
        neigh = []
        for i in centers:
            m = str(info[i].element)
            d, vec = vector_from_to(structure, k, i)
            cutoff = min(bond_cutoff(m, x, bond_scale), max_mx_distance)
            if d <= cutoff:
                neigh.append((i, m, d, vec))
        for a in range(len(neigh)):
            for b in range(a + 1, len(neigh)):
                i, mi, di, vi = neigh[a]
                j, mj, dj, vj = neigh[b]
                key = tuple(sorted((i, j)))
                ang = angle_between(vi, vj)
                regime = "other"
                if np.isfinite(ang):
                    if abs(ang - 90.0) <= tol90:
                        regime = "90"
                    elif ang >= 180.0 - tol180:
                        regime = "180"
                out.setdefault(key, []).append({"element": x, "angle": ang, "regime": regime,
                                                 "strong_anion": x in STRONG_ANIONS, "bridge_site_index": k,
                                                 "distance_i": di, "distance_j": dj})
    return out


def weighted_fraction(df: pd.DataFrame, col: str) -> float:
    if df.empty or col not in df.columns:
        return 0.0
    w = pd.to_numeric(df["pair_weight"], errors="coerce").fillna(0.0).to_numpy(float)
    x = df[col].astype(bool).astype(float).to_numpy(float)
    return float((w * x).sum() / w.sum()) if w.sum() > 1e-12 else 0.0


def connected_fraction(nodes: list[int], edges: list[tuple[int, int]]) -> float:
    if not nodes:
        return 0.0
    if len(nodes) == 1:
        return 1.0
    adj = {n: set() for n in nodes}
    for a, b in edges:
        if a in adj and b in adj:
            adj[a].add(b); adj[b].add(a)
    seen, best = set(), 0
    for start in nodes:
        if start in seen:
            continue
        stack, count = [start], 0
        seen.add(start)
        while stack:
            u = stack.pop(); count += 1
            for v in adj[u]:
                if v not in seen:
                    seen.add(v); stack.append(v)
        best = max(best, count)
    return best / len(nodes)


def build_magnetic_pairs(structure: Structure, sites: pd.DataFrame, dataset: str, structure_id: str, source: Path,
                max_mm_distance: float, contact_norm_cutoff: float, bond_scale: float,
                min_center_score: float, min_pair_weight: float) -> tuple[pd.DataFrame, dict[str, Any]]:
    supported = sites[pd.to_numeric(sites["center_confidence"], errors="coerce").fillna(0.0).ge(min_center_score)]
    info = {int(r.site_index): r for r in supported.itertuples(index=False)}
    centers = sorted(info)
    bridges = ligand_bridge_map(structure, centers, info, bond_scale=bond_scale)
    rows = []
    for a in range(len(centers)):
        for b in range(a + 1, len(centers)):
            i, j = centers[a], centers[b]
            d, _ = vector_from_to(structure, i, j)
            key = (i, j)
            br = bridges.get(key, [])
            if d > max_mm_distance and not br:
                continue
            si, sj = info[i], info[j]
            wi, wj = float(si.center_confidence), float(sj.center_confidence)
            pair_weight = math.sqrt(max(wi, 0.0) * max(wj, 0.0))
            if pair_weight < min_pair_weight:
                continue
            mi, mj = str(si.element), str(sj.element)
            norm_met = d / max(radius(mi, True) + radius(mj, True), 1e-9)
            norm_cov = d / max(radius(mi) + radius(mj), 1e-9)
            direct = norm_met <= contact_norm_cutoff
            metallic = direct and (not br or norm_met <= contact_norm_cutoff * .92)
            re_tm = ((si.moment_family == "rare_earth" and sj.moment_family in {"3d", "4d5d_weak"}) or
                     (sj.moment_family == "rare_earth" and si.moment_family in {"3d", "4d5d_weak"}))
            angles = [x["angle"] for x in br if np.isfinite(x["angle"])]
            rows.append({
                "dataset": dataset, "structure_id": structure_id, "source_path": str(source),
                "site_i": i, "site_j": j, "element_i": mi, "element_j": mj,
                "family_i": si.moment_family, "family_j": sj.moment_family,
                "center_score_i": wi, "center_score_j": wj, "pair_weight": pair_weight,
                "mm_distance_ang": d, "mm_distance_norm_metallic_radius": norm_met,
                "mm_distance_norm_covalent_radius": norm_cov,
                "n_common_ligand_bridges": len(br), "is_ligand_mediated": bool(br),
                "has_strong_anion_bridge": any(x["strong_anion"] for x in br),
                "is_direct_contact_geometry": bool(direct), "is_compact_metal_metal_geometry": bool(metallic),
                "is_mxm_90_geometry": any(x["regime"] == "90" for x in br),
                "is_mxm_180_geometry": any(x["regime"] == "180" for x in br),
                "is_re_tm_pair": bool(re_tm),
                "bridge_elements": ";".join(sorted({x["element"] for x in br})),
                "mean_m_x_m_angle_deg": float(np.mean(angles)) if angles else np.nan,
            })
    df = pd.DataFrame(rows)
    graph_edges = [(int(r.site_i), int(r.site_j)) for r in df.itertuples()] if len(df) else []
    summary = {
        "n_supported_centers": len(centers),
        "n_weighted_pairs": len(df),
        "total_pair_weight": float(pd.to_numeric(df.get("pair_weight", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()),
        "mean_pair_weight": as_float(pd.to_numeric(df.get("pair_weight", pd.Series(dtype=float)), errors="coerce").mean(), 0.0),
        "mean_mm_distance": as_float(pd.to_numeric(df.get("mm_distance_ang", pd.Series(dtype=float)), errors="coerce").mean()),
        "mean_mm_distance_norm": as_float(pd.to_numeric(df.get("mm_distance_norm_metallic_radius", pd.Series(dtype=float)), errors="coerce").mean()),
        "weighted_fraction_direct_contact_geometry": weighted_fraction(df, "is_direct_contact_geometry"),
        "weighted_fraction_ligand_mediated": weighted_fraction(df, "is_ligand_mediated"),
        "weighted_fraction_mxm_90_geometry": weighted_fraction(df, "is_mxm_90_geometry"),
        "weighted_fraction_mxm_180_geometry": weighted_fraction(df, "is_mxm_180_geometry"),
        "weighted_fraction_compact_metal_metal_geometry": weighted_fraction(df, "is_compact_metal_metal_geometry"),
        "weighted_fraction_re_tm": weighted_fraction(df, "is_re_tm_pair"),
        "magnetic_sublattice_connected_fraction": connected_fraction(centers, graph_edges),
    }
    return df, summary

def entropy_fraction(values: pd.Series) -> float:
    c = values.dropna().astype(str).value_counts()
    if len(c) <= 1:
        return 0.0
    p = c.to_numpy(float) / c.sum()
    return float(-(p * np.log(p + 1e-12)).sum() / np.log(len(c)))


def pair_motif_features(pairs: pd.DataFrame) -> dict[str, float]:
    if pairs.empty:
        return {"bridge_chemistry_diversity": 0.0, "pair_family_diversity": 0.0}
    fam = pairs.apply(lambda r: "-".join(sorted([str(r.family_i), str(r.family_j)])), axis=1)
    bridge = pairs.loc[pairs["bridge_elements"].astype(str).ne(""), "bridge_elements"]
    return {
        "bridge_chemistry_diversity": entropy_fraction(bridge),
        "pair_family_diversity": entropy_fraction(fam),
    }



def structure_features(cif: Path, dataset: str, priors: pd.DataFrame, neighbor_cutoff: float = 3.2,
                       max_mm_distance: float = 8.0, contact_norm_cutoff: float = 1.20,
                       bond_scale: float = 1.30, min_center_score: float = .05,
                       min_pair_weight: float = .05, max_sites: int = 500,
                       symprec: float = 0.10, min_oxidation_coverage: float = 1.0,
                       reject_disordered: bool = True):
    sid = cif.stem
    if Structure is None:
        raise RuntimeError("pymatgen is required for CIF descriptor extraction")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            structure = Structure.from_file(str(cif))
    except Exception as exc:
        return None, None, {"dataset": dataset, "structure_id": sid, "source_path": str(cif),
                            "parse_success": 0, "parse_error": repr(exc)}
    if max_sites and len(structure) > max_sites:
        return None, None, {"dataset": dataset, "structure_id": sid, "source_path": str(cif),
                            "parse_success": 0, "parse_error": f"n_sites>{max_sites}"}
    if reject_disordered and any(not site.is_ordered for site in structure):
        return None, None, {
            "dataset": dataset, "structure_id": sid, "source_path": str(cif),
            "parse_success": 0,
            "parse_error": "disordered_structure_not_supported_in_canonical_mode",
        }

    structural = structural_features(structure, symprec=symprec)
    auto_priors, chemistry = chemical_evidence(
        structure, dataset, sid, cif, min_oxidation_coverage=min_oxidation_coverage
    )
    site_priors = merge_site_priors(auto_priors, priors, dataset, sid)
    sites, centers = build_magnetic_centers(structure, dataset, sid, cif, site_priors, neighbor_cutoff)
    pairs, pair_features = build_magnetic_pairs(structure, sites, dataset, sid, cif, max_mm_distance,
                            contact_norm_cutoff, bond_scale, min_center_score, min_pair_weight)
    motifs = pair_motif_features(pairs)
    try:
        formula = structure.composition.reduced_formula
    except Exception:
        formula = str(structure.composition)
    row = {"dataset": dataset, "structure_id": sid, "source_path": str(cif), "formula_reduced": formula,
           "parse_success": 1, "parse_error": ""}
    row.update({f"structure__{k}": v for k, v in structural.items()})
    row.update({f"chemistry__{k}": v for k, v in chemistry.items()})
    row.update({f"magnetic_center__{k}": v for k, v in centers.items()})
    row.update({f"magnetic_pair__{k}": v for k, v in pair_features.items()})
    row.update({f"pair_motif__{k}": v for k, v in motifs.items()})
    return sites, pairs, row


REGISTERED_DESCRIPTORS = [
    "structure__n_sites",
    "structure__n_elements",
    "structure__volume_per_atom",
    "structure__density",
    "structure__min_interatomic_distance",
    "structure__has_disorder",
    "structure__occupancy_not_1_count",
    "structure__symmetry_failed",
    "chemistry__bv_success",
    "chemistry__oxi_guess_success",
    "chemistry__oxi_guess_count",
    "chemistry__oxidation_state_coverage",
    "chemistry__charge_balance_consistency",
    "chemistry__bv_residual_mean",
    "chemistry__bv_residual_median",
    "chemistry__bv_residual_max",
    "chemistry__fraction_sites_bv_consistent",
    "chemistry__fraction_magnetic_sites_bv_consistent",
    "chemistry__fraction_anion_sites_bv_consistent",
    "chemistry__fraction_sites_bv_successful",
    "chemistry__mean_cn_crystalnn",
    "chemistry__mean_ligand_fraction_in_nn",
    "chemistry__mean_magnetic_neighbor_fraction_in_nn",
    "chemistry__mean_opposite_sign_fraction_weighted",
    "chemistry__smact_valid",
    "chemistry__smact_valid_mixed_valence",
    "magnetic_center__n_magnetic_centers",
    "magnetic_center__fraction_magnetic_centers",
    "magnetic_center__mean_center_confidence",
    "magnetic_center__max_center_confidence",
    "magnetic_center__mean_ionic_score",
    "magnetic_center__mean_metallic_score",
    "magnetic_center__mean_rare_earth_score",
    "magnetic_center__mean_closed_shell_suppression",
    "magnetic_center__composition_ligand_fraction",
    "magnetic_center__composition_moment_element_fraction",
    "magnetic_center__fraction_centers_3d",
    "magnetic_center__fraction_centers_4d5d_weak",
    "magnetic_center__fraction_centers_rare_earth",
    "magnetic_center__fraction_centers_actinide",
    "magnetic_pair__n_supported_centers",
    "magnetic_pair__n_weighted_pairs",
    "magnetic_pair__total_pair_weight",
    "magnetic_pair__mean_pair_weight",
    "magnetic_pair__mean_mm_distance",
    "magnetic_pair__mean_mm_distance_norm",
    "magnetic_pair__weighted_fraction_direct_contact_geometry",
    "magnetic_pair__weighted_fraction_ligand_mediated",
    "magnetic_pair__weighted_fraction_mxm_90_geometry",
    "magnetic_pair__weighted_fraction_mxm_180_geometry",
    "magnetic_pair__weighted_fraction_compact_metal_metal_geometry",
    "magnetic_pair__weighted_fraction_re_tm",
    "magnetic_pair__magnetic_sublattice_connected_fraction",
    "pair_motif__bridge_chemistry_diversity",
    "pair_motif__pair_family_diversity",
]

# Canonical paper metric policy. These descriptors remain in extraction outputs
# for diagnostics/provenance but are not eligible coordinates of the paper metric space.
# The five raw counts depend on the crystallographic cell representation; the BV
# success-fraction coordinate is an exact duplicate of chemistry__bv_success in the
# canonical extraction. No CIF re-extraction is required to apply this policy.
CANONICAL_MAIN_EXCLUSIONS = {
    "chemistry__fraction_sites_bv_successful": "exact_duplicate_of_chemistry__bv_success_in_canonical_extraction",
    "structure__n_sites": "raw_extensive_cell_size_dependent",
    "magnetic_center__n_magnetic_centers": "raw_extensive_cell_size_dependent",
    "magnetic_pair__n_supported_centers": "raw_extensive_cell_size_dependent",
    "magnetic_pair__n_weighted_pairs": "raw_extensive_cell_size_dependent",
    "magnetic_pair__total_pair_weight": "raw_extensive_cell_size_dependent",
}

MAIN_FEATURES = [c for c in REGISTERED_DESCRIPTORS if c not in CANONICAL_MAIN_EXCLUSIONS]


COMPOSITION_FEATURES = [
    "structure__n_elements", "magnetic_center__composition_ligand_fraction",
    "magnetic_center__composition_moment_element_fraction", "magnetic_center__fraction_centers_3d",
    "magnetic_center__fraction_centers_4d5d_weak", "magnetic_center__fraction_centers_rare_earth",
    "magnetic_center__fraction_centers_actinide",
]


MAGNETIC_GRAPH_FEATURES = [c for c in MAIN_FEATURES if c.startswith("magnetic_center__") or c.startswith("magnetic_pair__") or c.startswith("pair_motif__")]

FEATURE_SETS = {
    "main": MAIN_FEATURES,
    "composition": COMPOSITION_FEATURES,
    "magnetic_graph": MAGNETIC_GRAPH_FEATURES,
}


def numeric_feature_columns(
    df: pd.DataFrame,
    min_coverage: float = 0.02,
    feature_set: str = "main",
    near_constant_tol: float = 1e-8,
) -> list[str]:
    """Select usable canonical registered features.

    Delegates to :mod:`cifmagfilter.reference` so public scoring and paper
    reproduction use the same feature-selection rule.
    """
    if feature_set not in FEATURE_SETS:
        raise ValueError(f"Unknown feature_set={feature_set}; choose from {sorted(FEATURE_SETS)}")
    return _select_numeric_features(
        df,
        FEATURE_SETS[feature_set],
        min_coverage=float(min_coverage),
        near_constant_tol=float(near_constant_tol),
    )


def robust_fit(df: pd.DataFrame, feature_cols: list[str], mask: np.ndarray, clip_z: float = 8.0):
    """Backward-compatible wrapper for the canonical reference transform."""
    return _reference_robust_fit(df, feature_cols, fit_mask=mask, clip_z=clip_z)


def robust_transform(df: pd.DataFrame, feature_cols: list[str], center: np.ndarray, scale: np.ndarray, clip_z: float = 8.0):
    """Backward-compatible wrapper for the canonical reference transform."""
    return _reference_robust_transform(df, feature_cols, center, scale, clip_z)


def knn_distance(X: np.ndarray, ref: np.ndarray, k: int) -> np.ndarray:
    return _reference_knn_distance(X, ref, k)


def knn_distance_training(X: np.ndarray, ref_idx: np.ndarray, k: int) -> np.ndarray:
    return _reference_knn_distance_training(X, ref_idx, k)


def _finish_reference_scores(out: pd.DataFrame, refs: list[str], magnetic_classes: list[str]) -> pd.DataFrame:
    return _reference_finish_scores(out, refs, magnetic_classes)


def reference_scores(meta: pd.DataFrame, X: np.ndarray, refs: dict[str, np.ndarray], magnetic_classes: list[str], k: int) -> pd.DataFrame:
    return _score_against_references(meta, X, refs, magnetic_classes, k)


def reference_scores_training(meta: pd.DataFrame, X: np.ndarray, labels: pd.Series,
                              reference_classes: list[str], magnetic_classes: list[str], k: int) -> pd.DataFrame:
    return _score_reference_training(meta, X, labels, reference_classes, magnetic_classes, k)
