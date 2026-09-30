from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from mvpipeline.annotations.compound_class import classify_formula
from mvpipeline.pipeline.enrichment_annotations import run_enrichment_annotations


FINETUNED_ANNOTATION_FIELDS = (
    "sample_uid",
    "model_name",
    "model_short",
    "run_uid",
    "source_sample_id",
    "cif_path",
    "cif_file_name",
    "formula_reduced",
    "formula_full",
    "status",
    "status_source",
    "rejection_reason",
    "compound_class",
    "cif_path_original",
    "cif_exists",
    "mvp_is_suspicious",
    "mvp_is_duplicate",
    "mvp_is_novel",
    "mvp_is_magnetic",
    "mvp_n_atoms",
    "mvp_density",
    "mvp_volume_per_atom",
    "mvp_spacegroup",
    "mvp_min_distance",
    "mvp_charge_solution_json",
    "mvp_details_json",
)


@dataclass(frozen=True)
class FinetunedAnnotationCohort:
    key: str
    input_path: Path
    adapted_output_path: Path
    enriched_output_path: Path
    sample_uid_prefix: str
    model_name: str
    model_short: str
    run_uid: str
    expected_total: int
    pass_label: str


MATTERGEN_FINETUNED = FinetunedAnnotationCohort(
    key="mattergen-finetuned",
    input_path=Path("outputs/mattergen_finetuned/all_structures.csv"),
    adapted_output_path=Path(
        "tables/03_features/phase5b_mattergen_finetuned_with_classes.csv"
    ),
    enriched_output_path=Path(
        "tables/04_magnetic_screening/"
        "phase5b_mattergen_finetuned_enrichment_annotations.csv"
    ),
    sample_uid_prefix="mattergen_ft__",
    model_name="MatterGen-finetuned",
    model_short="mg_ft",
    run_uid="mattergen_finetuned_mag016_seed17_bench2000_from_prod2016",
    expected_total=2000,
    pass_label="PHASE5B_MATTERGEN_ANNOTATIONS: PASSED",
)


CONCDVAE_FINETUNED = FinetunedAnnotationCohort(
    key="concdvae-finetuned",
    input_path=Path("outputs/concdvae_finetuned/all_structures.csv"),
    adapted_output_path=Path(
        "tables/03_features/phase5b_concdvae_finetuned_with_classes.csv"
    ),
    enriched_output_path=Path(
        "tables/04_magnetic_screening/"
        "phase5b_concdvae_finetuned_enrichment_annotations.csv"
    ),
    sample_uid_prefix="concdvae_ft__",
    model_name="Con-CDVAE-finetuned",
    model_short="cdvae_ft",
    run_uid="concdvae_finetuned_mag016_seed17_bench2000_from_prod2016",
    expected_total=2000,
    pass_label="PHASE5B_CONCDVAE_ANNOTATIONS: PASSED",
)


CRYSTALLM_FINETUNED = FinetunedAnnotationCohort(
    key="crystallm-finetuned",
    input_path=Path("outputs/crystallm_finetuned/all_structures.csv"),
    adapted_output_path=Path(
        "tables/03_features/"
        "phase5b_crystallm_finetuned_with_classes.csv"
    ),
    enriched_output_path=Path(
        "tables/04_magnetic_screening/"
        "phase5b_crystallm_finetuned_enrichment_annotations.csv"
    ),
    sample_uid_prefix="crystallm_ft__",
    model_name="CrystaLLM-finetuned",
    model_short="cllm_ft",
    run_uid="crystallm_finetuned_lr5e-4_step275_seed1337_20x100",
    expected_total=2000,
    pass_label="PHASE5B_CRYSTALLM_ANNOTATIONS: PASSED",
)



CRYSTALFORMER_FINETUNED = FinetunedAnnotationCohort(
    key="crystalformer-finetuned",
    input_path=Path("outputs/crystalformer_finetuned/all_structures.csv"),
    adapted_output_path=Path(
        "tables/03_features/phase5b_crystalformer_finetuned_with_classes.csv"
    ),
    enriched_output_path=Path(
        "tables/04_magnetic_screening/"
        "phase5b_crystalformer_finetuned_enrichment_annotations.csv"
    ),
    sample_uid_prefix="crystalformer_ft__",
    model_name="CrystalFormer-finetuned",
    model_short="cf_ft",
    run_uid="cf_repr_ft_v1",
    expected_total=2000,
    pass_label="PHASE5B_CRYSTALFORMER_ANNOTATIONS: PASSED",
)

FINETUNED_COHORTS = {
    CRYSTALFORMER_FINETUNED.key: CRYSTALFORMER_FINETUNED,

    MATTERGEN_FINETUNED.key: MATTERGEN_FINETUNED,
    CONCDVAE_FINETUNED.key: CONCDVAE_FINETUNED,
    CRYSTALLM_FINETUNED.key: CRYSTALLM_FINETUNED,
}


def get_finetuned_cohort(key: str) -> FinetunedAnnotationCohort:
    try:
        return FINETUNED_COHORTS[key]
    except KeyError as exc:
        choices = ", ".join(sorted(FINETUNED_COHORTS))
        raise ValueError(f"Unknown fine-tuned cohort {key!r}; choose one of: {choices}") from exc


def read_finetuned_input(path: Path) -> list[dict[str, str]]:
    with path.open(
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


def build_finetuned_annotation_rows(
    rows: Sequence[Mapping[str, str]],
    *,
    cohort: FinetunedAnnotationCohort,
    repo_root: Path,
    classifier: Callable[[str], str] = classify_formula,
) -> list[dict[str, object]]:
    if len(rows) != cohort.expected_total:
        raise RuntimeError(
            f"Expected {cohort.expected_total} MVP rows, got {len(rows)}"
        )

    adapted = []
    seen = set()

    for row in rows:
        source_id = row["structure_id"].strip()

        if not source_id:
            raise RuntimeError("Empty MVP structure_id")

        stem = Path(source_id).stem
        sample_uid = f"{cohort.sample_uid_prefix}{stem}"

        if sample_uid in seen:
            raise RuntimeError(f"Duplicate sample_uid: {sample_uid}")

        seen.add(sample_uid)

        cif_path = (repo_root / row["input_path"]).resolve()

        if not cif_path.is_file():
            raise FileNotFoundError(cif_path)

        formula = row.get("reduced_formula", "").strip()

        out = {
            "sample_uid": sample_uid,
            "model_name": cohort.model_name,
            "model_short": cohort.model_short,
            "run_uid": cohort.run_uid,
            "source_sample_id": source_id,
            "cif_path": str(cif_path),
            "cif_file_name": cif_path.name,
            "formula_reduced": formula,
            "formula_full": "",
            "status": row.get("status", ""),
            "status_source": "mvp_all_structures",
            "rejection_reason": row.get("rejection_reason", ""),
            "compound_class": classifier(formula),
            "cif_path_original": row["input_path"],
            "cif_exists": True,
            "mvp_is_suspicious": row.get("is_suspicious", ""),
            "mvp_is_duplicate": row.get("is_duplicate", ""),
            "mvp_is_novel": row.get("is_novel", ""),
            "mvp_is_magnetic": row.get("is_magnetic", ""),
            "mvp_n_atoms": row.get("n_atoms", ""),
            "mvp_density": row.get("density", ""),
            "mvp_volume_per_atom": row.get("volume_per_atom", ""),
            "mvp_spacegroup": row.get("spacegroup", ""),
            "mvp_min_distance": row.get("min_distance", ""),
            "mvp_charge_solution_json": row.get("charge_solution_json", ""),
            "mvp_details_json": row.get("details_json", ""),
        }

        adapted.append(out)

    return adapted


def write_finetuned_annotation_rows(
    rows: Sequence[Mapping[str, object]],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0]),
        )
        writer.writeheader()
        writer.writerows(rows)


def print_adapted_summary(
    rows: Sequence[Mapping[str, object]],
    *,
    unique_sample_uid_count: int,
    output_path: Path,
) -> None:
    status_counts = {}
    class_counts = {}

    for row in rows:
        status = row["status"]
        cls = row["compound_class"]

        status_counts[status] = status_counts.get(status, 0) + 1
        class_counts[cls] = class_counts.get(cls, 0) + 1

    print("===== adapted MVP manifest =====")
    print("rows:", len(rows))
    print("unique_sample_uid:", unique_sample_uid_count)
    print("status:", status_counts)
    print("output:", output_path)

    print()
    print("compound_class:")
    for key, value in sorted(
        class_counts.items(),
        key=lambda x: (-x[1], x[0]),
    ):
        print(f"  {key}: {value}")


def run_finetuned_annotation_preparation(
    *,
    cohort: FinetunedAnnotationCohort,
    repo_root: Path,
) -> None:
    input_path = repo_root / cohort.input_path
    adapted_output_path = repo_root / cohort.adapted_output_path
    enriched_output_path = repo_root / cohort.enriched_output_path

    rows = read_finetuned_input(input_path)
    adapted = build_finetuned_annotation_rows(
        rows,
        cohort=cohort,
        repo_root=repo_root,
    )

    write_finetuned_annotation_rows(adapted, adapted_output_path)
    print_adapted_summary(
        adapted,
        unique_sample_uid_count=len({row["sample_uid"] for row in adapted}),
        output_path=adapted_output_path,
    )

    report = run_enrichment_annotations(
        input_path=adapted_output_path,
        output_path=enriched_output_path,
        config_path=repo_root / "config/magnetism.yaml",
    )

    print()
    print("===== canonical Phase 5A-1 =====")
    print("input_count:", report.input_count)
    print("output_count:", report.output_count)
    print("output:", report.output_path)

    if report.input_count != cohort.expected_total:
        raise RuntimeError(
            f"Unexpected enrichment input count: {report.input_count}"
        )

    if report.output_count != cohort.expected_total:
        raise RuntimeError(
            f"Unexpected enrichment output count: {report.output_count}"
        )

    print()
    print(cohort.pass_label)

