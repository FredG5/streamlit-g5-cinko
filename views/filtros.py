import streamlit as st
from utils.data import MESES


def get_año(años_disponibles):
    return st.session_state.get("año_sel", años_disponibles[0])


def get_meses_nombres(nombres_disp):
    guardados = st.session_state.get("meses_nombres_sel", nombres_disp)
    validos   = [n for n in guardados if n in nombres_disp]
    return validos if validos else nombres_disp


def render_panel_filtros(data, años_disponibles):
    st.markdown("""
    <div class="filtros-header">
        <div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:1px;
                    opacity:0.7; margin-bottom:4px;">Grupo Cinko Consultores</div>
        <div style="font-size:1rem; font-weight:700;">Panel de Filtros</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("##### 📊 Periodo")

    año_actual = get_año(años_disponibles)
    año_idx    = años_disponibles.index(año_actual) if año_actual in años_disponibles else 0
    año        = st.selectbox("Año", años_disponibles, index=año_idx, key="año_sel")

    meses_disponibles = sorted(data[data["Año"] == año]["Mes"].unique())
    nombres_disp      = [MESES[m] for m in meses_disponibles]

    # Resetear meses si cambió el año
    if st.session_state.get("_prev_año") != año:
        st.session_state["meses_nombres_sel"] = nombres_disp
        st.session_state["_prev_año"]         = año

    meses_sel_nombres = st.multiselect(
        "Meses", nombres_disp,
        default=get_meses_nombres(nombres_disp),
        key="meses_nombres_sel",
    )

    st.divider()
    st.caption("Última actualización: 31/12/2025")
    st.caption("Powered by Grupo Cinko Consultores")

    return año, meses_sel_nombres
