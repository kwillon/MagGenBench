from __future__ import annotations

from mvpipeline.analysis.energy_magnetism_v2 import (
    ADAPTATION_PAIRS,
    ENERGY_MAGNETISM_BASENAMES,
)
from mvpipeline.analysis.manuscript_figure5_v2 import (
    FIGURE_BASENAME,
)
from mvpipeline.analysis.plotting_v2 import (
    ANALYSIS_V2_MAGNETIC_COHORT_ORDER,
)


def test_manuscript_figure5_basename():
    assert (
        FIGURE_BASENAME
        == "manuscript_figure5_energy_magnetism_v2_preview"
    )


def test_manuscript_figure5_has_three_adaptation_pairs():
    assert len(
        ADAPTATION_PAIRS
    ) == 3


def test_manuscript_figure5_adaptation_cohorts_exist():
    cohorts = set(
        ANALYSIS_V2_MAGNETIC_COHORT_ORDER
    )

    for baseline, adapted, _ in ADAPTATION_PAIRS:
        assert baseline in cohorts
        assert adapted in cohorts


def test_energy_magnetism_standalone_outputs_remain_available():
    assert (
        ENERGY_MAGNETISM_BASENAMES
        == (
            "09_energy_moment_landscape_v2",
            "10_energy_moment_adaptation_v2",
        )
    )


def test_manuscript_figure5_does_not_replace_standalone_outputs():
    assert (
        FIGURE_BASENAME
        not in ENERGY_MAGNETISM_BASENAMES
    )
