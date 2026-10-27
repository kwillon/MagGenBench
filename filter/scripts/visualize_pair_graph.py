from __future__ import annotations

"""
Article-grade CIF magnetic site/pair graph visualizer.

Physics/visualization fixes compared with early v5 scripts:
  1) Background atoms are hidden by default. Grey O/ligand atoms are no longer shown as
     disconnected graph nodes unless requested with --show-all-atoms.
  2) Ligand-mediated / 90° / 180° superexchange-like motifs are drawn as M-X-M paths
     through bridge ligand sites when bridge indices are available. The M-M dashed line is
     used only as a fallback proxy when the bridge site is unavailable.
  3) M-M direct / metallic-direct edges are never labelled with M-X-M angles. Angles are
     shown only for ligand-mediated motifs.
  4) If a D4 row has both direct and ligand-mediated flags, the visual class is
     direct+bridged: the direct M-M contact is shown as direct, and bridged support is shown
     separately if a bridge site can be resolved.

Important: These are descriptor graphs extracted from CIFs, not predicted exchange
Hamiltonians or magnetic-order assignments.
"""

import argparse
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except Exception:
    NETWORKX_AVAILABLE = False

try:
    from pymatgen.core import Structure
except Exception as exc:
    raise RuntimeError("pymatgen is required for graph visualization") from exc


NODE_COLORS = {
    "3d": "#1f77b4",
    "rare_earth": "#7b3294",
    "actinide": "#b15928",
    "4d5d_weak": "#ff7f0e",
    "bridge_ligand": "#4d4d4d",
    "other": "#999999",
}

EDGE_STYLES = {
    "metallic_direct": {"color": "#d73027", "ls": "-", "label": "metallic/direct M-M"},
    "direct_exchange": {"color": "#fc8d59", "ls": "-", "label": "direct M-M"},
    "direct_and_bridged": {"color": "#8c510a", "ls": "-", "label": "direct + bridged"},
    "superexchange_180": {"color": "#4575b4", "ls": "--", "label": "M-X-M ~180°"},
    "superexchange_90": {"color": "#1a9850", "ls": "--", "label": "M-X-M ~90°"},
    "ligand_mediated": {"color": "#74add1", "ls": ":", "label": "ligand-mediated M-X-M"},
    "rare_earth_tm": {"color": "#984ea3", "ls": "-.", "label": "RE-TM pair"},
    "generic": {"color": "#6b6b6b", "ls": "-", "label": "weighted M-M pair"},
}

LIGANDS = {"O", "F", "Cl", "Br", "I", "S", "Se", "Te", "N", "P", "As", "Sb", "B", "C", "Si", "Ge"}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def as_float(x: Any, default: float = np.nan) -> float:
    try:
        if pd.isna(x):
            return default
        y = float(x)
        if math.isfinite(y):
            return y
        return default
    except Exception:
        return default


def bool_flag(row: pd.Series, col: str) -> bool:
    if col not in row.index:
        return False
    x = row[col]
    if pd.isna(x):
        return False
    if isinstance(x, str):
        return x.strip().lower() in {"1", "true", "yes", "y"}
    try:
        return bool(int(float(x)))
    except Exception:
        return bool(x)


def normalize_keys(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "dataset" not in out.columns or "structure_id" not in out.columns:
        raise ValueError("CSV must contain dataset and structure_id")
    out["dataset"] = out["dataset"].astype(str).str.lower()
    out["structure_id"] = out["structure_id"].astype(str)
    return out


def read_csv(path: Path) -> pd.DataFrame:
    return normalize_keys(pd.read_csv(path, low_memory=False))


def species_symbol(structure: Structure, idx: int) -> str:
    try:
        return str(structure[idx].specie.symbol)
    except Exception:
        try:
            return str(structure[idx].species.elements[0].symbol)
        except Exception:
            return f"site{idx}"


def resolve_cif_path(cif_root: Path, dataset: str, structure_id: str, explicit: str | None = None) -> Path:
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p
        raise FileNotFoundError(f"Explicit --cif-path does not exist: {p}")

    dataset_variants = [dataset, dataset.upper(), dataset.capitalize()]
    if dataset == "fim":
        dataset_variants += ["FiM"]
    if dataset in {"afm", "fm", "fim", "nm"}:
        dataset_variants += [f"test_mp_cifs_2000/{dataset.upper()}", f"test_mp_cifs_2000/{'FiM' if dataset == 'fim' else dataset.upper()}"]

    for ds in dataset_variants:
        root = cif_root / ds
        for ext in [".cif", ".mcif"]:
            p = root / f"{structure_id}{ext}"
            if p.exists():
                return p
        if root.exists():
            hits = list(root.rglob(f"{structure_id}.cif")) + list(root.rglob(f"{structure_id}.mcif"))
            if hits:
                return hits[0]

    # Last-resort global search. Slow but robust for selected cases.
    hits = list(cif_root.rglob(f"{structure_id}.cif")) + list(cif_root.rglob(f"{structure_id}.mcif"))
    if hits:
        return hits[0]
    raise FileNotFoundError(f"Could not resolve CIF for {dataset}/{structure_id} under {cif_root}")


def pick_col(df: pd.DataFrame, names: list[str]) -> str | None:
    low = {c.lower(): c for c in df.columns}
    for n in names:
        if n.lower() in low:
            return low[n.lower()]
    for n in names:
        nl = n.lower()
        for c in df.columns:
            if nl in c.lower():
                return c
    return None


def parse_int_list(x: Any) -> list[int]:
    if x is None or pd.isna(x):
        return []
    s = str(x)
    vals = []
    for m in re.findall(r"-?\d+", s):
        try:
            vals.append(int(m))
        except Exception:
            pass
    return vals


def edge_type_from_row(row: pd.Series) -> str:
    direct = bool_flag(row, "is_direct_exchange_candidate") or bool_flag(row, "is_metallic_direct_candidate")
    metallic = bool_flag(row, "is_metallic_direct_candidate")
    ligand = bool_flag(row, "is_ligand_mediated_candidate")
    se90 = bool_flag(row, "is_superexchange_90_candidate")
    se180 = bool_flag(row, "is_superexchange_180_candidate")
    re_tm = bool_flag(row, "is_rare_earth_transition_metal_pair")

    # Physically safer priority: direct M-M contacts should not be labelled by M-X-M angle.
    if direct and ligand:
        return "direct_and_bridged"
    if metallic:
        return "metallic_direct"
    if direct:
        return "direct_exchange"
    if ligand and se180:
        return "superexchange_180"
    if ligand and se90:
        return "superexchange_90"
    if ligand:
        return "ligand_mediated"
    if re_tm:
        return "rare_earth_tm"
    return "generic"


def edge_is_ligand_mediated(edge_type: str) -> bool:
    return edge_type in {"superexchange_180", "superexchange_90", "ligand_mediated", "direct_and_bridged"}


def edge_is_direct(edge_type: str) -> bool:
    return edge_type in {"metallic_direct", "direct_exchange", "direct_and_bridged"}


def node_size(score: float) -> float:
    s = np.clip(as_float(score, 0.0), 0.0, 1.0)
    return 120 + 520 * s


def edge_width(weight: float) -> float:
    w = np.clip(as_float(weight, 0.0), 0.0, 1.0)
    return 1.2 + 4.8 * w


def project(coords: np.ndarray, mode: str) -> np.ndarray:
    if len(coords) == 1:
        return np.array([[0.0, 0.0]])
    if mode in {"xy", "ab", "a"}:
        return coords[:, :2]
    if mode in {"xz", "ac", "c"}:
        return coords[:, [0, 2]]
    if mode in {"yz", "bc", "b"}:
        return coords[:, 1:]
    X = coords - coords.mean(axis=0, keepdims=True)
    _, _, vh = np.linalg.svd(X, full_matrices=False)
    return X @ vh[:2].T


def prepare_nodes(c3: pd.DataFrame, structure: Structure, dataset: str, sid: str) -> pd.DataFrame:
    sub = c3[(c3["dataset"] == dataset) & (c3["structure_id"] == sid)].copy()
    if sub.empty:
        raise ValueError(f"No C3 rows for {dataset}/{sid}")
    site_col = pick_col(sub, ["site_index", "site_idx", "index"])
    if site_col is None:
        raise ValueError("C3 table lacks site_index")
    score_col = pick_col(sub, ["c3_supported_center_score", "supported_center_score", "magnetic_center_confidence_c3", "effective_moment_score_c3"])
    family_col = pick_col(sub, ["family", "moment_family_c3", "center_family_c3"])
    elem_col = pick_col(sub, ["element", "site_element"])
    rows = []
    for _, r in sub.iterrows():
        idx = pd.to_numeric(pd.Series([r[site_col]]), errors="coerce").iloc[0]
        if pd.isna(idx):
            continue
        idx = int(idx)
        if idx < 0 or idx >= len(structure):
            continue
        fam = str(r[family_col]) if family_col and pd.notna(r[family_col]) else "other"
        if fam not in NODE_COLORS:
            fam = "other"
        elem = str(r[elem_col]) if elem_col and pd.notna(r[elem_col]) else species_symbol(structure, idx)
        sc = as_float(r[score_col], 0.0) if score_col else 0.0
        xyz = structure[idx].coords
        rows.append({
            "site_index": idx,
            "element": elem,
            "label": f"{elem}{idx}",
            "family": fam,
            "node_score": sc,
            "x": float(xyz[0]), "y": float(xyz[1]), "z": float(xyz[2]),
            "node_role": "magnetic_center",
        })
    if not rows:
        raise ValueError(f"No valid C3 node rows for {dataset}/{sid}")
    return pd.DataFrame(rows).drop_duplicates("site_index")


def prepare_edges(pair: pd.DataFrame, dataset: str, sid: str, min_weight: float, top_n: int) -> pd.DataFrame:
    sub = pair[(pair["dataset"] == dataset) & (pair["structure_id"] == sid)].copy()
    if sub.empty:
        return pd.DataFrame()
    i_col = pick_col(sub, ["site_index_i", "site_i", "i"])
    j_col = pick_col(sub, ["site_index_j", "site_j", "j"])
    if i_col is None or j_col is None:
        raise ValueError("Pair table lacks i/j site index columns")
    w_col = pick_col(sub, ["pair_weight_v4", "pair_weight", "weight"])
    d_col = pick_col(sub, ["mm_distance", "distance_mm", "distance_ij", "m_m_distance"])
    angle_col = pick_col(sub, ["best_bridge_angle_deg", "m_x_m_angle_deg", "angle_deg", "bridge_angle_deg"])
    bridge_col = pick_col(sub, ["best_bridge_index", "bridge_index", "bridge_site_index", "bridge_indices", "bridge_site_indices", "bridge_sites"])
    bridge_elem_col = pick_col(sub, ["bridge_elements", "bridge_element"])
    rows = []
    for _, r in sub.iterrows():
        i = pd.to_numeric(pd.Series([r[i_col]]), errors="coerce").iloc[0]
        j = pd.to_numeric(pd.Series([r[j_col]]), errors="coerce").iloc[0]
        if pd.isna(i) or pd.isna(j):
            continue
        et = edge_type_from_row(r)
        bridge_indices = parse_int_list(r[bridge_col]) if bridge_col else []
        rows.append({
            "site_i": int(i),
            "site_j": int(j),
            "pair_weight_v4": as_float(r[w_col], 0.0) if w_col else 0.0,
            "distance_mm": as_float(r[d_col], np.nan) if d_col else np.nan,
            "angle_deg": as_float(r[angle_col], np.nan) if angle_col else np.nan,
            "bridge_indices": ";".join(str(x) for x in bridge_indices),
            "bridge_elements": str(r[bridge_elem_col]) if bridge_elem_col and pd.notna(r[bridge_elem_col]) else "",
            "edge_type": et,
            "visual_note": "angle belongs to M-X-M bridge, not direct M-M" if edge_is_ligand_mediated(et) else "direct/generic M-M descriptor edge",
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["pair_key"] = out.apply(lambda r: tuple(sorted((int(r.site_i), int(r.site_j)))), axis=1)
    out = out.sort_values("pair_weight_v4", ascending=False).drop_duplicates("pair_key").drop(columns="pair_key")
    out = out[out["pair_weight_v4"] >= min_weight].copy()
    out = out.sort_values("pair_weight_v4", ascending=False)
    if top_n and top_n > 0:
        out = out.head(top_n).copy()
    return out.reset_index(drop=True)


def add_bridge_nodes(nodes: pd.DataFrame, edges: pd.DataFrame, structure: Structure) -> pd.DataFrame:
    rows = []
    existing = set(nodes["site_index"].astype(int))
    bridge_set = set()
    for x in edges.get("bridge_indices", pd.Series([], dtype=str)).astype(str):
        for idx in parse_int_list(x):
            if 0 <= idx < len(structure):
                bridge_set.add(idx)
    for idx in sorted(bridge_set):
        if idx in existing:
            continue
        elem = species_symbol(structure, idx)
        xyz = structure[idx].coords
        rows.append({
            "site_index": idx,
            "element": elem,
            "label": f"{elem}{idx}",
            "family": "bridge_ligand" if elem in LIGANDS else "other",
            "node_score": 0.15,
            "x": float(xyz[0]), "y": float(xyz[1]), "z": float(xyz[2]),
            "node_role": "bridge_ligand" if elem in LIGANDS else "bridge_site",
        })
    if rows:
        return pd.concat([nodes, pd.DataFrame(rows)], ignore_index=True).drop_duplicates("site_index")
    return nodes


def draw_overlay(
    structure: Structure,
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    path: Path,
    projection: str,
    label_nodes: bool,
    label_edges: bool,
    show_all_atoms: bool,
    show_bridge_ligands: bool,
    title: str,
) -> None:
    plot_nodes = add_bridge_nodes(nodes, edges, structure) if show_bridge_ligands else nodes.copy()
    all_coords = np.array([site.coords for site in structure.sites], dtype=float)
    all_proj = project(all_coords, projection)
    idx_to_xy = {int(i): tuple(all_proj[int(i)]) for i in range(len(structure))}

    fig, ax = plt.subplots(figsize=(8.5, 7.0), dpi=250)
    if show_all_atoms:
        graph_idx = set(plot_nodes["site_index"].astype(int))
        bg_idx = [i for i in range(len(structure)) if i not in graph_idx]
        if bg_idx:
            ax.scatter(all_proj[bg_idx, 0], all_proj[bg_idx, 1], s=15, c="#d0d0d0", alpha=0.45, linewidths=0, zorder=1, label="non-graph atoms")

    # Draw edges. Ligand-mediated edges are M-X-M paths when bridge indices are available.
    used_styles = set()
    for _, e in edges.iterrows():
        i, j = int(e["site_i"]), int(e["site_j"])
        if i not in idx_to_xy or j not in idx_to_xy:
            continue
        et = str(e["edge_type"])
        st = EDGE_STYLES.get(et, EDGE_STYLES["generic"])
        w = edge_width(e["pair_weight_v4"])
        xi, yi = idx_to_xy[i]
        xj, yj = idx_to_xy[j]
        bridge_indices = parse_int_list(e.get("bridge_indices", ""))

        if edge_is_ligand_mediated(et) and bridge_indices and show_bridge_ligands:
            # Draw the strongest/first available bridge path.
            k = next((b for b in bridge_indices if b in idx_to_xy), None)
            if k is not None:
                xk, yk = idx_to_xy[k]
                ax.plot([xi, xk], [yi, yk], color=st["color"], linestyle=st["ls"], linewidth=w, alpha=0.85, zorder=2)
                ax.plot([xk, xj], [yk, yj], color=st["color"], linestyle=st["ls"], linewidth=w, alpha=0.85, zorder=2)
                used_styles.add(et)
                if label_edges and np.isfinite(as_float(e.get("angle_deg"), np.nan)):
                    ax.text(xk, yk, f"{as_float(e.get('angle_deg')):.0f}°", fontsize=7, ha="center", va="bottom", zorder=5)
            if edge_is_direct(et):
                # If both direct and bridged, show direct contact too, but without angle label.
                direct_style = EDGE_STYLES["metallic_direct"]
                ax.plot([xi, xj], [yi, yj], color=direct_style["color"], linestyle="-", linewidth=max(1.0, w*0.65), alpha=0.60, zorder=2)
                used_styles.add("metallic_direct")
        else:
            # Direct/generic edge or mediated fallback where bridge site is unavailable.
            ax.plot([xi, xj], [yi, yj], color=st["color"], linestyle=st["ls"], linewidth=w, alpha=0.82, zorder=2)
            used_styles.add(et)
            if label_edges:
                if edge_is_ligand_mediated(et) and np.isfinite(as_float(e.get("angle_deg"), np.nan)):
                    xm, ym = (xi + xj) / 2, (yi + yj) / 2
                    ax.text(xm, ym, f"{as_float(e.get('angle_deg')):.0f}°", fontsize=7, ha="center", va="center", zorder=5)
                elif edge_is_direct(et) and np.isfinite(as_float(e.get("distance_mm"), np.nan)):
                    xm, ym = (xi + xj) / 2, (yi + yj) / 2
                    ax.text(xm, ym, f"{as_float(e.get('distance_mm')):.2f} Å", fontsize=7, ha="center", va="center", zorder=5)

    # Nodes.
    for role, marker in [("bridge_ligand", "s"), ("bridge_site", "s"), ("magnetic_center", "o")]:
        sub = plot_nodes[plot_nodes["node_role"] == role] if "node_role" in plot_nodes.columns else plot_nodes
        if sub.empty:
            continue
        xs, ys, sizes, colors = [], [], [], []
        for _, n in sub.iterrows():
            idx = int(n["site_index"])
            if idx not in idx_to_xy:
                continue
            x, y = idx_to_xy[idx]
            xs.append(x); ys.append(y)
            sizes.append(80 if role != "magnetic_center" else node_size(n.get("node_score", 0.0)))
            colors.append(NODE_COLORS.get(str(n.get("family", "other")), NODE_COLORS["other"]))
            if label_nodes:
                ax.text(x, y, f" {n.get('label', idx)}", fontsize=7, ha="left", va="center", zorder=5)
        if xs:
            ax.scatter(xs, ys, s=sizes, c=colors, marker=marker, edgecolors="black", linewidths=0.7, alpha=0.95, zorder=4)

    # Legends.
    node_handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=NODE_COLORS["3d"], markeredgecolor="black", label="3d center", markersize=8),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=NODE_COLORS["rare_earth"], markeredgecolor="black", label="rare-earth center", markersize=8),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=NODE_COLORS["bridge_ligand"], markeredgecolor="black", label="shown bridge ligand", markersize=7),
    ]
    edge_handles = [Line2D([0], [0], color=EDGE_STYLES[k]["color"], ls=EDGE_STYLES[k]["ls"], lw=2.5, label=EDGE_STYLES[k]["label"])
                    for k in sorted(used_styles) if k in EDGE_STYLES]
    leg1 = ax.legend(handles=node_handles, loc="upper right", fontsize=7, title="Nodes", frameon=True)
    ax.add_artist(leg1)
    if edge_handles:
        ax.legend(handles=edge_handles, loc="lower right", fontsize=7, title="Descriptor motif", frameon=True)

    ax.set_title(title, fontsize=10)
    ax.set_xlabel(f"Projection axis 1 ({projection})", fontsize=8)
    ax.set_ylabel(f"Projection axis 2 ({projection})", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.15)
    ax.set_aspect("equal", adjustable="box")
    ensure_dir(path.parent)
    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def draw_abstract(nodes: pd.DataFrame, edges: pd.DataFrame, path: Path, label_nodes: bool, title: str, layout: str) -> None:
    if not NETWORKX_AVAILABLE:
        print("[warn] networkx not available; skipping abstract graph")
        return
    G = nx.Graph()
    for _, n in nodes.iterrows():
        G.add_node(int(n["site_index"]), **n.to_dict())
    for _, e in edges.iterrows():
        i, j = int(e["site_i"]), int(e["site_j"])
        if i in G and j in G:
            G.add_edge(i, j, **e.to_dict())
    if len(G) == 0:
        return
    if layout == "kamada":
        pos = nx.kamada_kawai_layout(G)
    elif layout == "circular":
        pos = nx.circular_layout(G)
    else:
        pos = nx.spring_layout(G, seed=42, weight="pair_weight_v4")

    fig, ax = plt.subplots(figsize=(7.0, 6.0), dpi=250)
    for et, st in EDGE_STYLES.items():
        edgelist = [(u, v) for u, v, d in G.edges(data=True) if d.get("edge_type") == et]
        if edgelist:
            widths = [edge_width(G.edges[e].get("pair_weight_v4", 0.0)) for e in edgelist]
            nx.draw_networkx_edges(G, pos, edgelist=edgelist, width=widths, edge_color=st["color"], style=st["ls"], alpha=0.85, ax=ax)
    for fam, color in NODE_COLORS.items():
        nodelist = [n for n, d in G.nodes(data=True) if d.get("family") == fam]
        if nodelist:
            sizes = [node_size(G.nodes[n].get("node_score", 0.0)) for n in nodelist]
            nx.draw_networkx_nodes(G, pos, nodelist=nodelist, node_size=sizes, node_color=color, edgecolors="black", linewidths=0.8, ax=ax)
    if label_nodes:
        nx.draw_networkx_labels(G, pos, {n: G.nodes[n].get("label", str(n)) for n in G.nodes}, font_size=7, ax=ax)
    ax.set_title(title, fontsize=10)
    ax.set_axis_off()
    ensure_dir(path.parent)
    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Article-grade CIF magnetic site/pair graph visualization for one structure")
    p.add_argument("--dataset", required=True)
    p.add_argument("--structure-id", required=True)
    p.add_argument("--cif-root", required=True)
    p.add_argument("--cif-path", default=None, help="Explicit CIF path. Preferred for MP reference folders.")
    p.add_argument("--c3-site-table", required=True)
    p.add_argument("--pair-table", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--mode", choices=["overlay2d", "abstract2d", "both"], default="both")
    p.add_argument("--projection", choices=["pca", "xy", "xz", "yz", "ab", "ac", "bc", "a", "b", "c"], default="pca")
    p.add_argument("--layout", choices=["spring", "kamada", "circular"], default="kamada")
    p.add_argument("--min-pair-weight", type=float, default=0.05)
    p.add_argument("--top-n-edges", type=int, default=15)
    p.add_argument("--label-nodes", action="store_true")
    p.add_argument("--label-edges", action="store_true")
    p.add_argument("--show-all-atoms", action="store_true", help="Show non-graph atoms as faint background. Off by default for paper figures.")
    p.add_argument("--show-bridge-ligands", action="store_true", default=True, help="Show bridge ligands when bridge indices exist. Default on.")
    p.add_argument("--hide-bridge-ligands", action="store_true", help="Disable bridge ligand nodes and draw mediated fallback lines.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    dataset = str(args.dataset).lower()
    sid = str(args.structure_id)
    outdir = Path(args.output_dir)
    ensure_dir(outdir)

    cif_path = resolve_cif_path(Path(args.cif_root), dataset, sid, args.cif_path)
    structure = Structure.from_file(str(cif_path))
    c3 = read_csv(Path(args.c3_site_table))
    pair = read_csv(Path(args.pair_table))

    nodes = prepare_nodes(c3, structure, dataset, sid)
    edges = prepare_edges(pair, dataset, sid, min_weight=args.min_pair_weight, top_n=args.top_n_edges)

    show_bridge_ligands = bool(args.show_bridge_ligands and not args.hide_bridge_ligands)
    stem = f"{dataset}__{sid}"

    nodes_out = add_bridge_nodes(nodes, edges, structure) if show_bridge_ligands else nodes.copy()
    nodes_out.to_csv(outdir / f"{stem}__graph_nodes.csv", index=False)
    edges.to_csv(outdir / f"{stem}__graph_edges.csv", index=False)

    title = f"{dataset} / {sid} — magnetic descriptor graph"
    if args.mode in {"overlay2d", "both"}:
        draw_overlay(
            structure=structure,
            nodes=nodes,
            edges=edges,
            path=outdir / f"{stem}__graph_overlay_2d.png",
            projection=args.projection,
            label_nodes=args.label_nodes,
            label_edges=args.label_edges,
            show_all_atoms=args.show_all_atoms,
            show_bridge_ligands=show_bridge_ligands,
            title=title,
        )
    if args.mode in {"abstract2d", "both"}:
        draw_abstract(nodes=nodes, edges=edges, path=outdir / f"{stem}__graph_abstract_2d.png", label_nodes=args.label_nodes, title=title, layout=args.layout)

    summary = pd.DataFrame([{
        "dataset": dataset,
        "structure_id": sid,
        "cif_path": str(cif_path),
        "n_structure_sites": len(structure),
        "n_magnetic_center_nodes": len(nodes),
        "n_edges_after_filter": len(edges),
        "n_edges_ligand_mediated": int(edges["edge_type"].isin(["superexchange_180", "superexchange_90", "ligand_mediated", "direct_and_bridged"]).sum()) if not edges.empty else 0,
        "n_edges_direct_or_metallic": int(edges["edge_type"].isin(["metallic_direct", "direct_exchange", "direct_and_bridged"]).sum()) if not edges.empty else 0,
        "show_all_atoms": bool(args.show_all_atoms),
        "show_bridge_ligands": bool(show_bridge_ligands),
    }])
    summary.to_csv(outdir / f"{stem}__graph_summary.csv", index=False)
    print(f"Saved graph visualization outputs to {outdir}")


if __name__ == "__main__":
    main()
