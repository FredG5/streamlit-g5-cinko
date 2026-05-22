import yaml
from pathlib import Path
from yaml.loader import SafeLoader
import streamlit as st
import streamlit_authenticator as stauth

from utils.data import load_data, MESES, get_logo_b64
from utils.ui import apply_css
from views.filtros import render_panel_filtros
from views.estado_resultados import render_shared_header, render_estado_resultados
from views.flujo_efectivo import render_flujo_efectivo
from views.balance_general import render_balance_general
from views.balance_analitico import render_balance_analitico

# ── Activar / desactivar autenticación ───────────────────────────────────────
AUTH_ENABLED = True

# ── Configuración de página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Grupo Cinko · Inteligencia Financiera",
    page_icon="📊",
    layout="wide",
)
apply_css()

# ── Datos ─────────────────────────────────────────────────────────────────────
data             = load_data()
años_disponibles = sorted([a for a in data["Año"].unique() if a >= 2025], reverse=True)

# ── Autenticador ──────────────────────────────────────────────────────────────
_CRED_PATH = Path(__file__).parent / "credentials.yaml"

def _build_authenticator():
    with open(_CRED_PATH) as f:
        cfg = yaml.load(f, Loader=SafeLoader)
    return stauth.Authenticate(
        cfg["credentials"],
        cfg["cookie"]["name"],
        cfg["cookie"]["key"],
        cfg["cookie"]["expiry_days"],
        auto_hash=False,
    )

# ── CSS exclusivo de la pantalla de login ────────────────────────────────────
_LOGIN_CSS = """
<style>
/* Oculta el bloque de color de Streamlit en la pantalla de login */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
    min-height: 100vh;
}
/* Tarjeta central del login */
.login-card {
    background: white;
    border-radius: 16px;
    padding: 36px 32px 28px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.35);
    text-align: center;
    margin-bottom: 0;
}
.login-logo {
    height: 72px;
    object-fit: contain;
    border-radius: 8px;
    margin-bottom: 14px;
}
.login-title {
    font-size: 1.55rem;
    font-weight: 800;
    color: #1a1a2e;
    margin: 0 0 4px;
    line-height: 1.15;
}
.login-subtitle {
    font-size: 0.85rem;
    color: #888;
    margin: 0 0 24px;
}
/* Formulario de login - mismo contenedor que la tarjeta */
div[data-testid="stForm"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    box-shadow: none !important;
}
/* Botón de ingresar */
div[data-testid="stForm"] button[kind="primaryFormSubmit"],
div[data-testid="stForm"] button[data-testid="baseButton-primaryFormSubmit"] {
    background-color: #1a1a2e !important;
    color: white !important;
    border-radius: 8px !important;
    width: 100% !important;
    font-weight: 600 !important;
    margin-top: 6px !important;
    border: none !important;
}
div[data-testid="stForm"] button:hover {
    background-color: #2d3561 !important;
}
</style>
"""

# ── Helper ────────────────────────────────────────────────────────────────────
def resolver_meses(año, meses_sel_nombres):
    meses_disp   = sorted(data[data["Año"] == año]["Mes"].unique())
    nombre_a_num = {MESES[m]: m for m in meses_disp}
    meses_sel    = sorted([nombre_a_num[n] for n in meses_sel_nombres if n in nombre_a_num])
    return meses_sel if meses_sel else list(meses_disp)

# ── Pantalla de login ─────────────────────────────────────────────────────────
def _show_login(authenticator):
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)

    _, col_c, _ = st.columns([1, 1.6, 1])
    with col_c:
        logo_b64 = get_logo_b64()
        st.markdown(
            f'<div class="login-card">'
            f'<img src="data:image/jpeg;base64,{logo_b64}" class="login-logo"><br>'
            f'<div class="login-title">Inteligencia Financiera</div>'
            f'<div class="login-subtitle">Grupo Cinko Consultores</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        authenticator.login(
            location="main",
            fields={
                "Form name": "",
                "Username":  "Usuario",
                "Password":  "Contraseña",
                "Login":     "Ingresar",
            },
            key="login_form",
        )
        if st.session_state.get("authentication_status") is False:
            st.error("Usuario o contraseña incorrectos. Intenta de nuevo.")

# ── Dashboard ─────────────────────────────────────────────────────────────────
def _show_dashboard(authenticator=None):
    if "sidebar_open" not in st.session_state:
        st.session_state.sidebar_open = True

    # Una sola rama de layout. Cuando el panel está cerrado, CSS oculta la columna
    # de filtros y expande la de contenido sin destruir ni reconstruir el DOM.
    if not st.session_state.sidebar_open:
        st.markdown(
            "<style>"
            "div[data-testid='stHorizontalBlock']:has(.filtros-header)"
            ">div[data-testid='stColumn']:first-child{display:none!important;}"
            "div[data-testid='stHorizontalBlock']:has(.filtros-header)"
            ">div[data-testid='stColumn']:last-child{flex:1!important;max-width:100%!important;}"
            "</style>",
            unsafe_allow_html=True,
        )

    col_sb, col_main = st.columns([1, 4], gap="large")

    with col_sb:
        año, meses_sel_nombres = render_panel_filtros(data, años_disponibles)

    with col_main:
        meses_sel = resolver_meses(año, meses_sel_nombres)
        render_shared_header(año, meses_sel, authenticator=authenticator)
        tab_er, tab_fe, tab_bg, tab_ba = st.tabs([
            "📊 Estado de Resultados",
            "💧 Flujo de Efectivo",
            "📋 Balance General",
            "📐 Balance Analítico",
        ])
        with tab_er:
            render_estado_resultados(data, año, meses_sel)
        with tab_fe:
            render_flujo_efectivo(data, año, meses_sel)
        with tab_bg:
            render_balance_general(data, año, meses_sel)
        with tab_ba:
            render_balance_analitico(data, año, meses_sel)

# ── Orquestación principal ────────────────────────────────────────────────────
if AUTH_ENABLED:
    authenticator = _build_authenticator()

    if st.session_state.get("authentication_status") is True:
        _show_dashboard(authenticator)
    else:
        _show_login(authenticator)
        if st.session_state.get("authentication_status") is True:
            st.rerun()
else:
    _show_dashboard()
