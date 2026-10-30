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


def test_ten_cohort_density_counts_points_and_median_arrows(monkeypatch):
    import numpy as np
    import mvpipeline.analysis.manuscript_figure5_v2 as figure5
    from mvpipeline.analysis.manuscript_figure3_v2 import COHORT_ORDER

    df, paired = figure5.load_paired_predictions()
    assert len(df) == 12281
    assert len(paired) == 12277

    def inspect(fig, output_dir, basename):
        fig.canvas.draw()
        axes = fig.axes[:6]
        assert int(axes[0].collections[0].get_array().sum()) == len(paired)
        expected_limits = axes[0].get_xlim(), axes[0].get_ylim()
        for i, ax in enumerate(axes[1:]):
            assert (ax.get_xlim(), ax.get_ylim()) == expected_limits
            medians = []
            for j, cohort in enumerate(COHORT_ORDER[2*i:2*i+2]):
                subset = paired.loc[paired.analysis_cohort.eq(cohort)]
                points = subset[[figure5.ENERGY, figure5.MOMENT]].to_numpy()
                np.testing.assert_array_equal(ax.collections[2*j].get_offsets(), points)
                median = np.median(points, axis=0)
                medians.append(median)
                np.testing.assert_allclose(ax.collections[2*j+1].get_offsets()[0], median)
                assert ax.get_xlim()[0] < points[:, 0].min() <= points[:, 0].max() < ax.get_xlim()[1]
                assert ax.get_ylim()[0] < points[:, 1].min() <= points[:, 1].max() < ax.get_ylim()[1]
            arrow = ax.texts[0]
            np.testing.assert_allclose(arrow.xy, medians[1])
            np.testing.assert_allclose(arrow.get_position(), medians[0])
        assert len(fig.legends) == 1
        return "checked"

    monkeypatch.setattr(figure5, "save_analysis_v2_figure_bundle", inspect)
    assert figure5.save_manuscript_figure5(paired) == "checked"
