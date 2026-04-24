from __future__ import annotations

"""
Страница Compare: сравнение нескольких запусков.

Берём метрики из validation_report.json и строим простые bar chart.
"""

import streamlit as st
import pandas as pd

from lib import safe_read_json


def render_compare_page(*, runs_index: list[dict]) -> None:
    st.subheader("Compare — сравнение запусков/моделей")

    if not runs_index:
        st.warning("Нет доступных запусков в outputs/.")
        st.stop()

    selected = st.multiselect(
        "Выбери модели для сравнения",
        [r["name"] for r in runs_index],
        default=[r["name"] for r in runs_index][:3],
    )

    if not selected:
        st.info("Выбери хотя бы одну модель.")
        st.stop()

    rows = []
    for name in selected:
        run = next(x for x in runs_index if x["name"] == name)
        rep = safe_read_json(run["report"])

        rows.append(
            {
                "model": name,
                "n_total": rep.get("n_total", 0),
                "n_validated": rep.get("n_validated", 0),
                "n_rejected": rep.get("n_rejected", 0),
                "validity_%": round(100 * rep.get("validity_ratio", 0.0), 2),
                "duplicate_%": round(100 * rep.get("duplicate_ratio", 0.0), 2),
                "magnetic_%": round(100 * rep.get("magnetic_ratio", 0.0), 2),
                "novelty_%": round(100 * rep.get("novelty_ratio", 0.0), 2),
                "avg_density": rep.get("avg_density", None),
                "avg_vpa": rep.get("avg_volume_per_atom", None),
            }
        )

    comp = pd.DataFrame(rows).sort_values("validity_%", ascending=False)
    st.dataframe(comp, width="stretch")

    st.markdown("### Validity (%)")
    st.bar_chart(comp.set_index("model")["validity_%"])

    st.markdown("### Duplicate (%)")
    st.bar_chart(comp.set_index("model")["duplicate_%"])

    st.markdown("### Magnetic (%) среди validated")
    st.bar_chart(comp.set_index("model")["magnetic_%"])

    st.markdown("### Novelty (%) среди validated")
    st.bar_chart(comp.set_index("model")["novelty_%"])
