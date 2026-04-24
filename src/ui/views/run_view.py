from __future__ import annotations

"""
Страница Run: запуск pipeline.

Задача:
- собрать параметры
- валидировать пути
- вызвать run_validation(...)
- показать итоговый report + ссылки на артефакты
"""

from pathlib import Path
from typing import Optional

import streamlit as st

from mvpipeline import load_config, run_validation
from mvpipeline.utils import PipelineConfig


def _p(s: str) -> Path:
    return Path(s).expanduser()


def _exists_or_none(s: str) -> Optional[Path]:
    s = (s or "").strip()
    if not s:
        return None
    p = _p(s)
    return p if p.exists() else None


def render_run_page() -> None:
    st.subheader("Run — запуск валидации")

    c1, c2 = st.columns(2)
    with c1:
        input_dir_s = st.text_input("input-dir", "samples/mattergen_cifs")
        thresholds_s = st.text_input(
            "thresholds.yaml (опционально)", "config/thresholds.yaml"
        )
        train_ref_s = st.text_input("train_reference.csv (опционально)", "")
    with c2:
        out_dir_s = st.text_input("out-dir (опционально)", "")
        model_name_s = st.text_input("model-name (опционально)", "")
        pretty = st.checkbox("Печатать отчёт красиво", value=True)

    run_btn = st.button("🚀 Run validation", type="primary")

    if not run_btn:
        return

    # --- input dir обязателен ---
    inp = _p(input_dir_s)
    if not inp.exists() or not inp.is_dir():
        st.error(f"input-dir не существует или не директория: {inp}")
        st.stop()

    # --- out_dir по умолчанию: outputs/<model_name> ---
    model_name = model_name_s.strip() or inp.name
    out_dir = _p(out_dir_s) if out_dir_s.strip() else Path("outputs") / model_name

    # --- thresholds (опционально) ---
    thr_path = _exists_or_none(thresholds_s)
    if thr_path is None and thresholds_s.strip():
        st.warning(f"thresholds не найден: {thresholds_s}. Использую дефолты.")
    cfg = load_config(thr_path) if thr_path else PipelineConfig()

    # --- train_reference (опционально) ---
    tr_path = _exists_or_none(train_ref_s)
    if tr_path is None and train_ref_s.strip():
        st.warning(
            f"train_reference не найден: {train_ref_s}. novelty_ratio не посчитается."
        )
        tr_path = None

    st.info("Запуск pipeline...")
    with st.spinner("Работаю..."):
        report = run_validation(
            input_dir=inp,
            out_dir=out_dir,
            cfg=cfg,
            train_reference=tr_path,
            model_name=model_name,
        )

    st.success("Готово ✅")

    if pretty:
        st.json(report)
    else:
        st.write(report)

    st.subheader("Артефакты")
    st.write("Report:", str(out_dir / "validation_report.json"))
    st.write("CSV:", str(out_dir / "all_structures.csv"))
    st.write("Validated:", str(out_dir / "validated_structures"))
    st.write("Rejected:", str(out_dir / "rejected_structures"))
