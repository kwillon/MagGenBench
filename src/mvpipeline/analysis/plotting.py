from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .cohorts import (
    CORE_BASELINE_FAMILIES,
    EXPECTED_PRODUCTION_ROWS,
    PRODUCTION_ANALYSIS_COHORTS,
)


UNIFIED_ANALYSIS_V1_RELATIVE_PATH = Path(
    "runs/analysis_v1/unified_analysis_v1.csv"
)
UNIFIED_ANALYSIS_FIGURE_DIR_RELATIVE_PATH = Path(
    "figures/unified_analysis_v1"
)

DEFAULT_FIGURE_DPI = 300
DEFAULT_FIGURE_BBOX = "tight"

CRYSTAL_SYSTEM_ORDER = (
    "triclinic",
    "monoclinic",
    "orthorhombic",
    "tetragonal",
    "trigonal",
    "hexagonal",
    "cubic",
)

UNIFIED_ANALYSIS_ID_COLUMNS = (
    "sample_uid",
    "analysis_cohort",
    "analysis_family",
)


@dataclass(frozen=True)
class PlotGroup:
    label: str
    analysis_cohort: str
    analysis_family: str | None = None


_PRODUCTION_COHORTS_BY_KEY = {
    cohort.analysis_cohort: cohort
    for cohort in PRODUCTION_ANALYSIS_COHORTS
}


def _production_plot_group(label: str, analysis_cohort: str) -> PlotGroup:
    cohort = _PRODUCTION_COHORTS_BY_KEY[analysis_cohort]
    if cohort.analysis_family is None:
        raise RuntimeError(
            f"Production plot group {label!r} requires a concrete "
            "analysis_family."
        )
    return PlotGroup(
        label=label,
        analysis_cohort=cohort.analysis_cohort,
        analysis_family=cohort.analysis_family,
    )


BASELINE_PLOT_GROUPS = tuple(
    PlotGroup(
        label=f"{family} baseline",
        analysis_cohort="baseline_master",
        analysis_family=family,
    )
    for family in CORE_BASELINE_FAMILIES
)

FINETUNING_COMPARISON_GROUPS = (
    PlotGroup("MatterGen baseline", "baseline_master", "MatterGen"),
    _production_plot_group("MatterGen fine-tuned", "mattergen_finetuned"),
    PlotGroup("Con-CDVAE baseline", "baseline_master", "Con-CDVAE"),
    _production_plot_group("Con-CDVAE fine-tuned", "concdvae_finetuned"),
)

CRYSJEPA_COMPARISON_GROUPS = (
    _production_plot_group("Crys-JEPA Base", "crysjepa_base"),
    _production_plot_group("Crys-JEPA Refined", "crysjepa_refined"),
)

STANDARD_PLOT_GROUPS = (
    FINETUNING_COMPARISON_GROUPS[0],
    FINETUNING_COMPARISON_GROUPS[1],
    FINETUNING_COMPARISON_GROUPS[2],
    FINETUNING_COMPARISON_GROUPS[3],
    BASELINE_PLOT_GROUPS[2],
    BASELINE_PLOT_GROUPS[3],
    CRYSJEPA_COMPARISON_GROUPS[0],
    CRYSJEPA_COMPARISON_GROUPS[1],
)

_NON_BASELINE_GROUPS_BY_COHORT = {
    group.analysis_cohort: group
    for group in STANDARD_PLOT_GROUPS
    if group.analysis_cohort != "baseline_master"
}


def apply_unified_plot_style() -> None:
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "figure.figsize": (10, 6),
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "savefig.bbox": DEFAULT_FIGURE_BBOX,
            "savefig.dpi": DEFAULT_FIGURE_DPI,
            "font.size": 11,
        }
    )


def repository_root_from_script(script_path: str | Path) -> Path:
    return Path(script_path).resolve().parents[2]


def unified_analysis_v1_path(repo_root: str | Path) -> Path:
    return Path(repo_root) / UNIFIED_ANALYSIS_V1_RELATIVE_PATH


def unified_analysis_figure_dir(repo_root: str | Path) -> Path:
    return Path(repo_root) / UNIFIED_ANALYSIS_FIGURE_DIR_RELATIVE_PATH


def load_unified_analysis_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def materialize_record_rows(
    rows: object,
) -> list[dict[str, object]]:
    if hasattr(rows, "to_dict"):
        records = rows.to_dict("records")
        return [dict(row) for row in records]
    return [dict(row) for row in rows]  # type: ignore[arg-type]


def require_columns(
    rows: Sequence[Mapping[str, object]],
    required_columns: Iterable[str],
    *,
    label: str = "unified analysis rows",
) -> None:
    required = tuple(required_columns)
    if not rows:
        raise RuntimeError(f"{label} is empty.")
    missing = sorted(set(required) - set(rows[0]))
    if missing:
        raise RuntimeError(f"{label} missing required columns: {missing}")


def require_expected_row_count(
    rows: Sequence[Mapping[str, object]],
    *,
    expected_count: int = EXPECTED_PRODUCTION_ROWS,
    label: str = "unified analysis rows",
) -> None:
    if len(rows) != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} {label}, got {len(rows)}"
        )


def validate_unified_analysis_rows(
    rows: object,
    *,
    required_columns: Iterable[str] = (),
    expected_count: int | None = EXPECTED_PRODUCTION_ROWS,
) -> None:
    materialized = materialize_record_rows(rows)
    require_columns(
        materialized,
        (*UNIFIED_ANALYSIS_ID_COLUMNS, *tuple(required_columns)),
    )
    if expected_count is not None:
        require_expected_row_count(
            materialized,
            expected_count=expected_count,
        )


def plot_group_for_row(row: Mapping[str, object]) -> PlotGroup:
    cohort = str(row.get("analysis_cohort") or "").strip()
    family = str(row.get("analysis_family") or "").strip()

    if cohort == "baseline_master":
        for group in BASELINE_PLOT_GROUPS:
            if family == group.analysis_family:
                return group
        raise RuntimeError(
            "Unknown baseline analysis_family for baseline_master: "
            f"{family!r}"
        )

    group = _NON_BASELINE_GROUPS_BY_COHORT.get(cohort)
    if group is not None:
        if family != group.analysis_family:
            raise RuntimeError(
                "Unexpected analysis_family for analysis_cohort: "
                f"cohort={cohort!r}, expected={group.analysis_family!r}, "
                f"actual={family!r}"
            )
        return group

    raise RuntimeError(
        "Unknown analysis_cohort/analysis_family combination: "
        f"cohort={cohort!r}, family={family!r}"
    )


def subset_rows_for_group(
    rows: Sequence[Mapping[str, object]],
    group: PlotGroup,
) -> list[Mapping[str, object]]:
    selected: list[Mapping[str, object]] = []
    for row in rows:
        if str(row.get("analysis_cohort") or "").strip() != group.analysis_cohort:
            continue
        if group.analysis_family is not None:
            family = str(row.get("analysis_family") or "").strip()
            if family != group.analysis_family:
                continue
        selected.append(row)

    if not selected:
        raise RuntimeError(f"Empty plot group: {group.label}")

    return selected


def build_plot_groups(
    rows: object,
    *,
    groups: Sequence[PlotGroup] = STANDARD_PLOT_GROUPS,
) -> list[tuple[PlotGroup, list[Mapping[str, object]]]]:
    materialized = materialize_record_rows(rows)
    validate_unified_analysis_rows(materialized, expected_count=None)

    assigned_count = 0
    output: list[tuple[PlotGroup, list[Mapping[str, object]]]] = []
    group_by_key = {
        (group.analysis_cohort, group.analysis_family): group
        for group in groups
    }

    for row in materialized:
        group = plot_group_for_row(row)
        key = (group.analysis_cohort, group.analysis_family)
        if key not in group_by_key:
            raise RuntimeError(
                "Unified analysis row belongs to a known plot group "
                "outside the requested group set: "
                f"{group.label}"
            )

    for group in groups:
        selected = subset_rows_for_group(materialized, group)
        assigned_count += len(selected)
        output.append((group, selected))

    if assigned_count != len(materialized):
        raise RuntimeError(
            "Plot group construction changed row count: "
            f"{len(materialized)} input rows, {assigned_count} grouped rows"
        )

    return output


def bool_series_values(values: Iterable[object]) -> list[bool]:
    return [
        str(value).strip().lower() in {"true", "1"}
        for value in values
    ]


def numeric_values(values: Iterable[object]) -> list[float]:
    output: list[float] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        output.append(float(text))
    return output


def save_figure(fig: object, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        path,
        dpi=DEFAULT_FIGURE_DPI,
        bbox_inches=DEFAULT_FIGURE_BBOX,
    )
