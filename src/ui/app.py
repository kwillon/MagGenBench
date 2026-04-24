from __future__ import annotations

from pathlib import Path

import streamlit as st

from lib import load_outputs_index
from views import render_run_page, render_explore_page, render_compare_page


# -----------------------------------------------------------------------------
# Page config + header
# -----------------------------------------------------------------------------

st.set_page_config(page_title="MVPipeline", layout="wide")

st.title("MVPipeline — Crystal Structure Validation")
st.caption("Запуск валидации CIF + просмотр отчётов + 3D-превью структур")


# -----------------------------------------------------------------------------
# Sidebar navigation + outputs index
# -----------------------------------------------------------------------------

with st.sidebar:
    st.header("Навигация")
    page = st.radio("Раздел", ["Run", "Explore", "Compare"], horizontal=False)

    st.divider()
    st.header("Runs index")

    # Где искать запуски
    outputs_root = Path(st.text_input("outputs dir", "outputs"))
    runs_index = load_outputs_index(outputs_root)

    if not runs_index:
        st.info("Пока нет запусков: outputs/*/validation_report.json")


# -----------------------------------------------------------------------------
# Router
# -----------------------------------------------------------------------------

if page == "Run":
    render_run_page()

elif page == "Explore":
    render_explore_page(runs_index=runs_index)

else:
    render_compare_page(runs_index=runs_index)
