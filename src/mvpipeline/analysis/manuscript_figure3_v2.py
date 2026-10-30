from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..descriptors.figure3_ft import (
    FT_OUTPUT_DIR, FT_QC_INPUTS, STANDARDIZED_INPUT, mapped_retained_qc,
)
from .figures_v2_magnetic import ANALYSIS_V2_MAGNETIC_INPUT
from .publication_style import (
    ADAPTED_HATCH, GENERATOR_COLORS, apply_publication_style, cohort_color, is_adapted,
)
from .plotting_v2 import (
    ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    FigureExportPaths,
    save_analysis_v2_figure_bundle,
)

FIGURE_BASENAME = "manuscript_figure3_magnetic_domain_v2_preview"
TRANSITION_3D_VARIABLE = "transition_3d_fraction"
LANTHANIDE_VARIABLE = "configured_lanthanide_fraction"
MAGNETIC_NEIGHBOR_VARIABLE = "magnetic_site_magnetic_neighbor_fraction_mean"
VARIABLES = (TRANSITION_3D_VARIABLE, LANTHANIDE_VARIABLE, MAGNETIC_NEIGHBOR_VARIABLE)
COHORT_ORDER = (
    "mattergen_baseline", "mattergen_finetuned",
    "concdvae_baseline", "concdvae_finetuned",
    "crystalformer_baseline", "crystalformer_finetuned",
    "crystallm_baseline", "crystallm_finetuned",
    "crysjepa_base", "crysjepa_refined",
)
COHORT_LABELS = dict(zip(COHORT_ORDER, (
    "MatterGen\nBase", "MatterGen\nFT", "Con-CDVAE\nBase", "Con-CDVAE\nFT",
    "CrystalFormer\nBase", "CrystalFormer\nFT", "CrystaLLM\nBase", "CrystaLLM\nFT",
    "Crys-JEPA\nBase", "Crys-JEPA\nRef.",
)))
COHORT_COLORS = {key: cohort_color(key) for key in COHORT_ORDER}
BASE_MODELS = {
    "mattergen_baseline": "MatterGen", "concdvae_baseline": "Con-CDVAE",
    "crystalformer_baseline": "CrystalFormer", "crystallm_baseline": "CrystaLLM",
}
QC_INPUTS = {
    **{key: Path("tables/03_features/master_structures_with_classes.csv") for key in BASE_MODELS},
    "mattergen_finetuned": Path("tables/03_features/phase5b_mattergen_finetuned_with_classes.csv"),
    "concdvae_finetuned": Path("tables/03_features/phase5b_concdvae_finetuned_with_classes.csv"),
    **FT_QC_INPUTS,
    "crysjepa_base": Path("tables/03_features/crysjepa_base_with_classes.csv"),
    "crysjepa_refined": Path("tables/03_features/crysjepa_refined_with_classes.csv"),
}
# Expected supplemental paths; actual server locations can be passed through the CLI.
DESCRIPTOR_INPUTS = {
    key: FT_OUTPUT_DIR / f"{key}_descriptor_v2_magnetic.csv"
    for key in ("crystalformer_finetuned", "crystallm_finetuned")
}


@dataclass(frozen=True)
class ManuscriptFigure3Report:
    input_csv: Path
    audit: object
    missing_inputs: tuple[Path, ...]
    figure_paths: FigureExportPaths | None


def _read_csv(path):
    import pandas as pd

    return pd.read_csv(path, low_memory=False, dtype={"sample_uid": str, "structure_id": str})


def _identity(df, path):
    key = "sample_uid" if "sample_uid" in df else "structure_id"
    if key not in df:
        raise RuntimeError(f"{path}: requires sample_uid or structure_id aligned with descriptors")
    ids = df[key].fillna("").astype(str).str.strip()
    if ids.eq("").any() or ids.duplicated().any():
        raise RuntimeError(f"{path}: empty or duplicate identifiers")
    return ids


def _read_descriptor_table(path):
    import numpy as np
    import pandas as pd

    df = _read_csv(path)
    required = {"analysis_cohort", "magnetic_geometry_status", *VARIABLES}
    missing = required.difference(df.columns)
    if missing:
        raise RuntimeError(f"{path}: missing descriptor columns {sorted(missing)}")
    if not set(df["analysis_cohort"]).issubset(COHORT_ORDER):
        raise RuntimeError(f"{path}: unknown descriptor cohort")
    df["sample_uid"] = _identity(df, path)
    if "descriptor_v2_schema_version" in df and not df["descriptor_v2_schema_version"].eq("v2-magnetic").all():
        raise RuntimeError(f"{path}: incompatible descriptor schema")
    for variable in VARIABLES:
        original = df[variable]
        numeric = pd.to_numeric(original, errors="coerce")
        invalid = original.notna() & numeric.isna()
        if invalid.any():
            raise RuntimeError(f"{path}: nonnumeric {variable}")
        if ((numeric[np.isfinite(numeric)] < 0) | (numeric[np.isfinite(numeric)] > 1)).any():
            raise RuntimeError(f"{path}: {variable} outside [0, 1]")
        df[variable] = numeric.where(np.isfinite(numeric))
    status = df["magnetic_geometry_status"]
    if not status.dropna().isin(["ok", "not_applicable", "error", "not_computed"]).all():
        raise RuntimeError(f"{path}: unknown magnetic_geometry_status")
    if (status.ne("ok") & df[MAGNETIC_NEIGHBOR_VARIABLE].notna()).any():
        raise RuntimeError(f"{path}: finite geometry fraction with non-ok status")
    df["descriptor_source"] = str(path)
    return df[["analysis_cohort", "sample_uid", *VARIABLES, "magnetic_geometry_status", "descriptor_source"]]


def _read_retained_qc(path, cohort, standardized_input=STANDARDIZED_INPUT):
    df = _read_csv(path)
    if "status" not in df:
        raise RuntimeError(f"{path}: missing structural QC status")
    if "analysis_cohort" in df:
        df = df.loc[df["analysis_cohort"].eq(cohort)].copy()
    elif cohort in BASE_MODELS:
        if "model_name" not in df:
            raise RuntimeError(f"{path}: baseline QC table needs model_name")
        df = df.loc[df["model_name"].eq(BASE_MODELS[cohort])].copy()
    if len(df) != 2000:
        raise RuntimeError(f"{path} ({cohort}): expected 2000 harmonized QC rows, got {len(df)}")
    ids = _identity(df, path)
    status = df["status"].fillna("").astype(str).str.strip().str.lower()
    if not status.isin(["validated", "rejected"]).all():
        raise RuntimeError(f"{path}: unknown structural QC status")
    if cohort in FT_QC_INPUTS and "sample_uid" not in df:
        standardized = _read_csv(standardized_input)
        mapped = mapped_retained_qc(df, cohort, standardized)["sample_uid"]
        mapped.attrs["qc_identity_mapping"] = str(standardized_input)
        return mapped
    return ids.loc[status.eq("validated")]


def build_figure3_audit(aligned, qc_counts):
    import pandas as pd

    rows = []
    for cohort in COHORT_ORDER:
        row = {"analysis_cohort": cohort, "qc_count": qc_counts.get(cohort)}
        subset = aligned.loc[aligned["analysis_cohort"].eq(cohort)]
        if cohort not in qc_counts:
            rows.append(row)
            continue
        row["descriptor_records"] = int(subset["descriptor_source"].notna().sum())
        row["descriptor_missing_records"] = len(subset) - row["descriptor_records"]
        for panel, variable in zip(("A", "B"), VARIABLES[:2]):
            values = subset[variable].dropna()
            available = len(values)
            nonzero = int(values.gt(0).sum())
            row.update({
                f"{panel}_available": available, f"{panel}_nonzero": nonzero,
                f"{panel}_zero": int(values.eq(0).sum()),
                f"{panel}_missing": len(subset) - available,
                f"{panel}_prevalence_percent": 100 * nonzero / available if available else None,
            })
        status = subset["magnetic_geometry_status"]
        finite = subset[MAGNETIC_NEIGHBOR_VARIABLE].notna()
        ok = status.eq("ok")
        na = status.eq("not_applicable")
        row.update({
            "C_status_ok": int(ok.sum()),
            "C_applicable": int((ok & finite).sum()),
            "C_zero": int((ok & finite & subset[MAGNETIC_NEIGHBOR_VARIABLE].eq(0)).sum()),
            "C_not_applicable": int(na.sum()),
            "C_ok_missing": int((ok & ~finite).sum()),
            "C_error": int(status.eq("error").sum()),
            "C_not_computed": int(status.eq("not_computed").sum()),
            "C_status_missing": int(status.isna().sum()),
        })
        rows.append(row)
    audit = pd.DataFrame(rows).set_index("analysis_cohort")
    for column in audit.columns:
        if not column.endswith("_percent"):
            audit[column] = audit[column].astype("Int64")
    return audit


def load_figure3_inputs(input_csv=ANALYSIS_V2_MAGNETIC_INPUT, *, qc_inputs=None,
                       descriptor_inputs=None, standardized_input=STANDARDIZED_INPUT):
    import pandas as pd

    qc_paths = {**QC_INPUTS, **(qc_inputs or {})}
    descriptor_paths = {**DESCRIPTOR_INPUTS, **(descriptor_inputs or {})}
    if set(qc_paths).difference(COHORT_ORDER) or set(descriptor_paths).difference(COHORT_ORDER):
        raise ValueError("Unknown cohort in input overrides")
    frames = [_read_descriptor_table(input_csv)]
    observed = set(frames[0]["analysis_cohort"])
    missing = []
    for cohort, path in descriptor_paths.items():
        if cohort in observed:
            if descriptor_inputs and cohort in descriptor_inputs:
                raise RuntimeError(f"{cohort}: already present in --input; duplicate descriptor source")
            continue
        path = Path(path)
        if not path.is_file():
            missing.append(path)
            continue
        frame = _read_descriptor_table(path)
        if set(frame["analysis_cohort"]) != {cohort}:
            raise RuntimeError(f"{path}: expected only {cohort}")
        frames.append(frame)
    descriptors = pd.concat(frames, ignore_index=True)
    if descriptors.duplicated(["analysis_cohort", "sample_uid"]).any():
        raise RuntimeError("Duplicate descriptor identifiers")
    aligned_frames = []
    counts = {}
    qc_sources = {}
    qc_mappings = {}
    for cohort in COHORT_ORDER:
        path = Path(qc_paths[cohort])
        qc_sources[cohort] = str(path)
        if not path.is_file():
            missing.append(path)
            continue
        ids = _read_retained_qc(path, cohort, standardized_input)
        qc_mappings[cohort] = ids.attrs.get("qc_identity_mapping", "direct canonical IDs")
        counts[cohort] = len(ids)
        desc = descriptors.loc[descriptors["analysis_cohort"].eq(cohort)]
        extra = set(desc["sample_uid"]).difference(ids)
        if extra:
            raise RuntimeError(f"{cohort}: {len(extra)} descriptor IDs outside retained QC population")
        population = pd.DataFrame({"sample_uid": ids.to_numpy(), "analysis_cohort": cohort})
        aligned_frames.append(population.merge(
            desc, on=["sample_uid", "analysis_cohort"], how="left", validate="one_to_one",
        ))
    if not aligned_frames:
        raise RuntimeError("No QC populations available")
    aligned = pd.concat(aligned_frames, ignore_index=True)
    audit = build_figure3_audit(aligned, counts)
    audit["qc_source"] = [qc_sources[key] for key in audit.index]
    audit["qc_identity_mapping"] = [qc_mappings.get(key, "") for key in audit.index]
    audit["descriptor_source"] = [
        ";".join(descriptors.loc[descriptors["analysis_cohort"].eq(key), "descriptor_source"].unique())
        for key in audit.index
    ]
    return aligned, audit, tuple(dict.fromkeys(missing))


def _format_axis(ax, labels):
    ax.set_xlim(-0.65, len(COHORT_ORDER) - 0.35)
    ax.set_xticks(range(len(COHORT_ORDER)))
    if labels:
        ax.set_xticklabels(labels)
    ax.tick_params(axis="x", labelsize=10, pad=6)
    if labels:
        import matplotlib.pyplot as plt
        plt.setp(ax.get_xticklabels(), rotation=90, ha="center", va="top")
    ax.grid(axis="y", alpha=0.4, linewidth=0.45)
    ax.set_axisbelow(True)
    ax.axvline(7.5, color="#7C858C", linewidth=0.8, linestyle="--")


def _boxplot(ax, data):
    available = [(i, values) for i, values in enumerate(data) if len(values)]
    if not available:
        ax.set_ylim(0, 1.05)
        return
    box = ax.boxplot(
        [values for _, values in available],
        positions=[i for i, _ in available], widths=0.62, patch_artist=True, showfliers=False,
        medianprops={"color": "#23324F", "linewidth": 1},
    )
    for patch, (index, _) in zip(box["boxes"], available):
        cohort = COHORT_ORDER[index]
        patch.set_facecolor(COHORT_COLORS[cohort])
        patch.set_edgecolor("#23324F")
        patch.set_linewidth(0.7)
        if is_adapted(cohort):
            patch.set_hatch(ADAPTED_HATCH)
    ax.set_ylim(0, 1.05)


def save_manuscript_figure3(df, *, output_dir=ANALYSIS_V2_FIGURE_OUTPUT_DIR, audit=None):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    if set(df["analysis_cohort"]) != set(COHORT_ORDER):
        raise RuntimeError("Figure 3 requires all ten QC cohorts")
    if audit is None:
        audit = build_figure3_audit(df, df["analysis_cohort"].value_counts().to_dict())
    apply_publication_style()
    fig = plt.figure(figsize=(16, 9), constrained_layout=True)
    outer = fig.add_gridspec(3, 2, height_ratios=[0.22, 1.8, 1])
    legend_ax = fig.add_subplot(outer[0, :])
    legend_ax.axis("off")
    generator_legend = legend_ax.legend(handles=[
        Patch(facecolor=color, label=name) for name, color in GENERATOR_COLORS.items()
    ], title="Generator", loc="center left", ncol=5, frameon=False,
       columnspacing=1.0, handletextpad=0.5)
    legend_ax.add_artist(generator_legend)
    legend_ax.legend(handles=[
        Patch(facecolor="#DDDDDD", edgecolor="#23324F", label="Base"),
        Patch(facecolor="#DDDDDD", edgecolor="#23324F", hatch=ADAPTED_HATCH,
              label="Fine-tuned / Refined"),
    ], title="Version", loc="center right", frameon=False)
    for column, (panel, variable, title) in enumerate(zip(
        ("A", "B"), VARIABLES[:2], ("3d transition-metal fraction", "Configured lanthanide fraction"),
    )):
        grid = outer[1, column].subgridspec(2, 1, height_ratios=[1, 1.1], hspace=0.05)
        top = fig.add_subplot(grid[0])
        bottom = fig.add_subplot(grid[1], sharex=top)
        prevalence = audit[f"{panel}_prevalence_percent"]
        bars = top.bar(range(10), prevalence, color=[COHORT_COLORS[key] for key in COHORT_ORDER],
                       edgecolor="#23324F", linewidth=0.45)
        for index, (bar, value) in enumerate(zip(bars, prevalence)):
            if is_adapted(COHORT_ORDER[index]):
                bar.set_hatch(ADAPTED_HATCH)
            top.text(index, value + 2 if value == value else 2,
                     f"{value:.1f}" if value == value else "NA",
                     ha="center", va="bottom", fontsize=10)
        top.set_ylim(0, 125)
        top.set_yticks([0, 25, 50, 75, 100])
        top.set_ylabel("Prevalence (%)")
        top.set_title(f"{panel}   {title}", loc="left", fontweight="bold", pad=10)
        _format_axis(top, [])
        top.tick_params(axis="x", bottom=False, labelbottom=False)
        nonzero = []
        labels = []
        for cohort in COHORT_ORDER:
            values = df.loc[df["analysis_cohort"].eq(cohort), variable].dropna()
            nonzero.append(values.loc[values.gt(0)].to_numpy())
            labels.append(COHORT_LABELS[cohort].replace("\n", " ")
                          + f"\nn+={int(audit.loc[cohort, panel + '_nonzero'])}")
        _boxplot(bottom, nonzero)
        _format_axis(bottom, labels)
        bottom.set_ylabel("Atomic fraction\n(nonzero only)")
    ax = fig.add_subplot(outer[2, :])
    values = [
        df.loc[df["analysis_cohort"].eq(key) & df["magnetic_geometry_status"].eq("ok"),
               MAGNETIC_NEIGHBOR_VARIABLE].dropna().to_numpy()
        for key in COHORT_ORDER
    ]
    _boxplot(ax, values)
    _format_axis(ax, [COHORT_LABELS[key].replace("\n", " ")
                      + f"\nn={int(audit.loc[key, 'C_applicable'])}" for key in COHORT_ORDER])
    ax.set_ylabel("Magnetic-neighbor fraction")
    ax.set_title("C   Local magnetic-neighbor environment (applicable records)", loc="left",
                 fontweight="bold", pad=10)
    paths = save_analysis_v2_figure_bundle(fig, output_dir, FIGURE_BASENAME,
                                          preserve_canvas=True)
    plt.close(fig)
    return paths


def run_manuscript_figure3(input_csv=ANALYSIS_V2_MAGNETIC_INPUT,
                           figure_dir=ANALYSIS_V2_FIGURE_OUTPUT_DIR, *,
                           qc_inputs=None, descriptor_inputs=None, audit_only=False,
                           standardized_input=STANDARDIZED_INPUT, require_complete_descriptors=False):
    df, audit, missing = load_figure3_inputs(
        input_csv, qc_inputs=qc_inputs, descriptor_inputs=descriptor_inputs,
        standardized_input=standardized_input,
    )
    root = Path(figure_dir)
    root.mkdir(parents=True, exist_ok=True)
    audit.to_csv(root / "figure3_availability_audit.csv")
    if missing and not audit_only:
        raise FileNotFoundError("Missing Figure 3 sources:\n" + "\n".join(map(str, missing)))
    if require_complete_descriptors:
        complete = audit["qc_count"].notna() & audit["descriptor_records"].eq(audit["qc_count"])
        if not complete.fillna(False).all():
            raise RuntimeError("Incomplete descriptor ID coverage:\n" + audit.loc[~complete.fillna(False)].to_string())
    paths = None if audit_only else save_manuscript_figure3(df, output_dir=root, audit=audit)
    return ManuscriptFigure3Report(Path(input_csv), audit, missing, paths)
