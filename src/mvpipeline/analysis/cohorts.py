from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .unified import AnalysisCohortSpec


CORE_BASELINE_FAMILIES = (
    "MatterGen",
    "Con-CDVAE",
    "CrystalFormer",
    "CrystaLLM",
)

COMPARATOR_ANALYSIS_COHORTS = (
    "crysjepa_base",
    "crysjepa_refined",
)

PRODUCTION_ANALYSIS_COHORT_ORDER = (
    "baseline_master",
    "mattergen_finetuned",
    "concdvae_finetuned",
    "crysjepa_base",
    "crysjepa_refined",
)

EXPECTED_PRODUCTION_ROWS = 10684

EXPECTED_PRODUCTION_COHORT_COUNTS: Mapping[str, int] = {
    "baseline_master": 4702,
    "mattergen_finetuned": 1376,
    "concdvae_finetuned": 1299,
    "crysjepa_base": 1764,
    "crysjepa_refined": 1543,
}

EXPECTED_PRODUCTION_DESCRIPTOR_STATUS_COUNTS: Mapping[str, int] = {
    "ok": 10681,
    "partial": 3,
}

EXPECTED_PRODUCTION_ENERGY_STATUS_COUNTS: Mapping[str, int] = {
    "ok": 10680,
    "error": 4,
}

EXPECTED_PRODUCTION_MAGNETISM_STATUS_COUNTS: Mapping[str, int] = {
    "ok": 10684,
}


@dataclass(frozen=True)
class ProductionAnalysisCohort:
    analysis_cohort: str
    analysis_family: str | None
    analysis_state: str
    descriptor_path: Path
    joined_path: Path | None

    def to_analysis_spec(
        self,
        *,
        baseline_joined_path: Path,
    ) -> AnalysisCohortSpec:
        joined_path = (
            baseline_joined_path
            if self.joined_path is None
            else self.joined_path
        )
        return AnalysisCohortSpec(
            self.analysis_cohort,
            self.analysis_family,
            self.analysis_state,
            self.descriptor_path,
            joined_path,
        )


PRODUCTION_ANALYSIS_COHORTS = (
    ProductionAnalysisCohort(
        analysis_cohort="baseline_master",
        analysis_family=None,
        analysis_state="baseline",
        descriptor_path=Path(
            "descriptor_v1/"
            "baseline_master_descriptors_v1.csv"
        ),
        joined_path=None,
    ),
    ProductionAnalysisCohort(
        analysis_cohort="mattergen_finetuned",
        analysis_family="MatterGen",
        analysis_state="fine_tuned",
        descriptor_path=Path(
            "descriptor_v1/"
            "mattergen_finetuned_descriptors_v1.csv"
        ),
        joined_path=Path(
            "tables/04_magnetic_screening/"
            "phase5b_mattergen_finetuned_joined.csv"
        ),
    ),
    ProductionAnalysisCohort(
        analysis_cohort="concdvae_finetuned",
        analysis_family="Con-CDVAE",
        analysis_state="fine_tuned",
        descriptor_path=Path(
            "descriptor_v1/"
            "concdvae_finetuned_descriptors_v1.csv"
        ),
        joined_path=Path(
            "tables/04_magnetic_screening/"
            "phase5b_concdvae_finetuned_joined.csv"
        ),
    ),
    ProductionAnalysisCohort(
        analysis_cohort="crysjepa_base",
        analysis_family="Crys-JEPA",
        analysis_state="base",
        descriptor_path=Path(
            "descriptor_v1/"
            "crysjepa_base_descriptors_v1.csv"
        ),
        joined_path=Path(
            "tables/04_magnetic_screening/"
            "crysjepa_base_joined.csv"
        ),
    ),
    ProductionAnalysisCohort(
        analysis_cohort="crysjepa_refined",
        analysis_family="Crys-JEPA",
        analysis_state="refined",
        descriptor_path=Path(
            "descriptor_v1/"
            "crysjepa_refined_descriptors_v1.csv"
        ),
        joined_path=Path(
            "tables/04_magnetic_screening/"
            "crysjepa_refined_joined.csv"
        ),
    ),
)


def production_analysis_cohort_specs(
    *,
    baseline_joined_path: Path,
) -> list[AnalysisCohortSpec]:
    return [
        cohort.to_analysis_spec(
            baseline_joined_path=baseline_joined_path,
        )
        for cohort in PRODUCTION_ANALYSIS_COHORTS
    ]

