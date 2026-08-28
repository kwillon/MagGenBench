from __future__ import annotations

from mvpipeline.analysis.figures_v2_magnetic import (
    AUDIT_VARIABLES,
)
from mvpipeline.analysis.manuscript_figure3_v2 import (
    FIGURE_BASENAME,
    LANTHANIDE_VARIABLE,
    MAGNETIC_NEIGHBOR_VARIABLE,
    TRANSITION_3D_VARIABLE,
)


def test_manuscript_figure3_basename():
    assert (
        FIGURE_BASENAME
        == "manuscript_figure3_magnetic_domain_v2_preview"
    )


def test_transition_3d_variable_is_audited():
    assert TRANSITION_3D_VARIABLE in AUDIT_VARIABLES


def test_lanthanide_variable_is_audited():
    assert LANTHANIDE_VARIABLE in AUDIT_VARIABLES


def test_magnetic_neighbor_variable_is_audited():
    assert MAGNETIC_NEIGHBOR_VARIABLE in AUDIT_VARIABLES


def test_manuscript_figure3_variables_are_distinct():
    assert len(
        {
            TRANSITION_3D_VARIABLE,
            LANTHANIDE_VARIABLE,
            MAGNETIC_NEIGHBOR_VARIABLE,
        }
    ) == 3
