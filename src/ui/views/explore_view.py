from __future__ import annotations

"""
Страница Explore: просмотр результатов одного запуска.

Задача:
- выбрать run из outputs
- показать report.json
- загрузить all_structures.csv
- дать фильтры
- показать 3D просмотр выбранной структуры
"""

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from pymatgen.core import Structure

from lib import (
    load_all_structures_csv,
    apply_basic_filters,
    apply_range_filters,
    safe_read_json,
    render_structure_3d,
)


def render_explore_page(*, runs_index: list[dict]) -> None:
    st.subheader("Explore — просмотр результатов запуска")

    if not runs_index:
        st.warning("Нет доступных запусков. Сначала сделай Run.")
        st.stop()

    run_name = st.selectbox("Выбери запуск", [r["name"] for r in runs_index])
    run = next(r for r in runs_index if r["name"] == run_name)

    # --- report.json ---
    report = safe_read_json(run["report"])
    st.markdown("### Итоговый отчёт")
    st.json(report)

    # --- all_structures.csv ---
    if run["csv"] is None:
        st.warning("В этом запуске нет all_structures.csv")
        st.stop()

    df = load_all_structures_csv(run["csv"], model_name=run_name)

    st.markdown("### Таблица структур (all_structures.csv)")

    # --- фильтры (простые) ---
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        status_filter = st.selectbox("Статус", ["all", "validated", "rejected"])
    with f2:
        only_magnetic = st.checkbox("Только magnetic", value=False)
    with f3:
        only_novel = st.checkbox("Только novel", value=False)
    with f4:
        max_rows = st.number_input(
            "Макс строк", min_value=100, max_value=20000, value=2000, step=100
        )

    filtered = apply_basic_filters(
        df,
        status=status_filter,
        only_magnetic=only_magnetic,
        only_novel=only_novel,
    )

    # --- фильтры по диапазонам ---
    with st.expander("Фильтры по диапазонам (density / vpa / d_min / n_atoms)"):
        r1, r2, r3, r4 = st.columns(4)

        ranges: dict[str, tuple[float, float]] = {}

        def add_slider(col: str, col_container):
            if col not in filtered.columns:
                col_container.write(f"{col}: нет в CSV")
                return
            vals = filtered[col].dropna()
            if len(vals) == 0:
                col_container.write(f"{col}: нет значений")
                return
            mn, mx = float(vals.min()), float(vals.max())
            lo, hi = col_container.slider(col, mn, mx, (mn, mx))
            ranges[col] = (lo, hi)

        add_slider("density", r1)
        add_slider("volume_per_atom", r2)
        add_slider("min_distance", r3)
        add_slider("n_atoms", r4)

        if ranges:
            filtered = apply_range_filters(filtered, ranges)

    st.dataframe(filtered.head(int(max_rows)), width="stretch", height=420)

    # --- просмотр одной структуры ---
    st.markdown("### Просмотр одной структуры (3D)")

    if len(filtered) == 0:
        st.info("По фильтрам ничего не найдено.")
        st.stop()

    sid = st.selectbox("structure_id", filtered["structure_id"].astype(str).head(5000))
    row = filtered[filtered["structure_id"].astype(str) == str(sid)].iloc[0]

    st.json(
        {
            "structure_id": row.get("structure_id"),
            "status": row.get("status"),
            "rejection_reason": row.get("rejection_reason", ""),
            "density": row.get("density"),
            "volume_per_atom": row.get("volume_per_atom"),
            "min_distance": row.get("min_distance"),
            "n_atoms": row.get("n_atoms"),
            "reduced_formula": row.get("reduced_formula"),
            "spacegroup": row.get("spacegroup"),
            "is_magnetic": bool(row.get("is_magnetic", False)),
            "is_novel": (
                None
                if pd.isna(row.get("is_novel", np.nan))
                else bool(row.get("is_novel"))
            ),
            "is_suspicious": bool(row.get("is_suspicious", False)),
            "input_path": row.get("input_path"),
        }
    )

    cif_path = Path(str(row.get("input_path", "")))
    if cif_path.exists():
        try:
            struct = Structure.from_file(str(cif_path))
            sphere_scale = st.slider(
                "Размер атомов (sphere scale)", 0.15, 0.8, 0.3, 0.05
            )
            render_structure_3d(struct, sphere_scale=sphere_scale)
        except Exception as e:
            st.error(f"Не смог прочитать CIF: {e}")
    else:
        st.warning(f"Файл CIF не найден: {cif_path}")

    # --- быстрые графики ---
    st.markdown("### Быстрые графики")

    gc1, gc2 = st.columns(2)

    with gc1:
        st.write("Причины rejected (top-20)")
        if "rejection_reason" in df.columns:
            rc = (
                df[df["is_rejected"]]["rejection_reason"]
                .replace("", "unknown")
                .value_counts()
                .head(20)
            )
            st.bar_chart(rc)

    with gc2:
        st.write("Распределение density (validated)")
        if "density" in df.columns:
            dv = df[df["is_valid"]]["density"].dropna()
            st.line_chart(pd.DataFrame({"density": dv.reset_index(drop=True)}))
