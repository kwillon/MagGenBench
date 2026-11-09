"""The longest Figure 6 labels must fit inside the frame at publication size."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pytest

from mvpipeline.analysis.figure6_layout import (
    add_bar_value_labels, ensure_bar_label_clearance, MIN_FRAME_CLEARANCE_PT,
)
from mvpipeline.analysis.typography import apply_ebrima_typography


@pytest.mark.parametrize('width', [3.4, 5.7])
def test_label_gutter_survives_long_labels_and_narrow_axes(width):
    apply_ebrima_typography()
    fig, ax = plt.subplots(figsize=(width, 2), dpi=150)
    bars = ax.barh([0, 1], [98.8, 99.2], color=['#4F6745', '#61838F'])
    ax.set_xlim(0, 115)
    labels = add_bar_value_labels(ax, bars,
        ['98.8% (1842/1864)', '99.2% (1849/1864)'])
    original = [(b.get_width(), b.get_facecolor()) for b in bars]
    gap = ensure_bar_label_clearance(ax, labels)
    assert gap >= MIN_FRAME_CLEARANCE_PT
    assert [(b.get_width(), b.get_facecolor()) for b in bars] == original
    assert [label.get_text() for label in labels] == [
        '98.8% (1842/1864)', '99.2% (1849/1864)']
    assert all(label.get_position() == (4.0, 0) for label in labels)
    plt.close(fig)
