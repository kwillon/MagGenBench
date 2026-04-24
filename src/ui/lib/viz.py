from __future__ import annotations

"""
Визуализации:
- 3D просмотр структуры (py3Dmol)
"""

import py3Dmol
import streamlit as st
from pymatgen.core import Structure


def render_structure_3d(
    struct: Structure,
    *,
    height: int = 520,
    sphere_scale: float = 0.30,
) -> None:
    """
    Рендер структуры в 3D.

    Важно:
    - py3Dmol возвращает HTML
    - Streamlit показывает его через st.components.v1.html
    """
    cif_str = struct.to(fmt="cif")

    view = py3Dmol.view(width=900, height=500)
    view.addModel(cif_str, "cif")
    view.setStyle({"sphere": {"scale": sphere_scale}, "stick": {"radius": 0.15}})
    view.addUnitCell()
    view.zoomTo()

    st.components.v1.html(view._make_html(), height=height, scrolling=False)
