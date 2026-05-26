import streamlit as st
import pandas as pd

APP_CSS = """
<style>
    #MainMenu {visibility: hidden;}
    footer    {visibility: hidden;}
    [data-testid="stToolbar"]      { visibility: hidden; }
    [data-testid="stDecoration"]   { display: none; }
    header[data-testid="stHeader"] { background: transparent !important; height: 0 !important; }

    .block-container { padding-top: 0.75rem !important; }

    html, body, [class*="css"] {
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }

    .kpi-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 16px 20px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        min-height: 130px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .kpi-card .label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        opacity: 0.75;
        margin-bottom: 6px;
    }
    .kpi-card .value {
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 4px;
        white-space: nowrap;
    }
    .kpi-card .delta { font-size: 0.80rem; font-weight: 600; }
    .delta-pos { color: #00e676; }
    .delta-neg { color: #ff5252; }
    .delta-neu { color: #90a4ae; }

    .fin-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
    .fin-table th {
        background: #1a1a2e; color: white;
        padding: 10px 12px; text-align: center;
        font-weight: 600; font-size: 0.78rem;
    }
    .fin-table th:first-child { text-align: left; border-radius: 8px 0 0 0; }
    .fin-table th:last-child  { border-radius: 0 8px 0 0; }
    .fin-table td { padding: 7px 12px; text-align: right; border-bottom: 1px solid #e8e8e8; }
    .fin-table td:first-child { text-align: left; font-weight: 500; }
    .fin-table tr:hover  { background: #f5f7ff; }
    .fin-table .subtotal td { font-weight: 700; border-top: 2px solid #1a1a2e; }
    .fin-table .separator td { border-bottom: 2px dashed #ccc; }
    .fin-table .pct      { color: #666; font-size: 0.75rem; }
    .fin-table .negative { color: #d32f2f; }
    .fin-table .positive { color: #2e7d32; }

    /* Balance General — tabla compacta para 12 meses */
    .bal-table { font-size: 0.71rem; }
    .bal-table th { padding: 4px 4px; font-size: 0.69rem; }
    .bal-table td { padding: 2px 4px; }
    .bal-table .subtotal td { border-top: 1px solid #1a1a2e; }
    .bal-table .separator td { border-bottom: 1px dashed #ccc; }

    .section-header {
        background: linear-gradient(90deg, #1a1a2e 0%, #2d3561 100%);
        color: white; padding: 12px 20px; border-radius: 8px;
        margin: 20px 0 16px 0; font-size: 1.1rem; font-weight: 600;
    }

    /* ── Splash screen de transición login → dashboard ───────────────────── */
    @keyframes splashFadeOut {
        0%, 35% { opacity: 1; }
        100%    { opacity: 0; }
    }
    .login-splash {
        position: fixed;
        inset: 0;
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
        z-index: 9999;
        animation: splashFadeOut 0.8s ease-out forwards;
        pointer-events: none;
    }

    /* ── Animaciones ──────────────────────────────────────────────────────── */
    @keyframes fadeIn {
        from { opacity: 0; }
        to   { opacity: 1; }
    }
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* Suaviza cada rerun completo (cambio de filtros, toggle panel) */
    .main .block-container {
        animation: fadeIn 0.22s ease-out;
    }

    /* Suaviza el cambio de tab */
    .stTabs [data-baseweb="tab-panel"] {
        animation: fadeIn 0.18s ease-out;
    }

    /* Suaviza la aparición de gráficas Plotly */
    .js-plotly-plot {
        animation: fadeIn 0.3s ease-out;
    }

    /* KPI cards — aparición escalonada en cascada */
    div[data-testid="stColumn"]:nth-child(1) .kpi-card { animation: fadeInUp 0.3s ease-out 0.00s both; }
    div[data-testid="stColumn"]:nth-child(2) .kpi-card { animation: fadeInUp 0.3s ease-out 0.07s both; }
    div[data-testid="stColumn"]:nth-child(3) .kpi-card { animation: fadeInUp 0.3s ease-out 0.14s both; }
    div[data-testid="stColumn"]:nth-child(4) .kpi-card { animation: fadeInUp 0.3s ease-out 0.21s both; }
    div[data-testid="stColumn"]:nth-child(5) .kpi-card { animation: fadeInUp 0.3s ease-out 0.28s both; }

    /* Hover suave en botones */
    .stButton button {
        transition: opacity 0.18s ease, box-shadow 0.18s ease, background-color 0.18s ease !important;
    }

    /* Hover suave en tabs */
    .stTabs [data-baseweb="tab"] {
        transition: color 0.18s ease, border-color 0.18s ease;
    }

    /* Prevenir salto de scroll en reruns */
    .main { overflow-anchor: auto; }

    /* Columnas sin animación propia — el fade lo hereda del block-container padre */
    [data-testid="stColumn"],
    [data-testid="stHorizontalBlock"] {
        transition: none !important;
        animation: none !important;
    }

    /* Header card — aplica al bloque [11,1] en ambos estados del sidebar */
    div[data-testid="stHorizontalBlock"]:has(.cinko-header-logo) {
        background: white;
        border: 1px solid #e8e8e8;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        padding: 18px 24px;
        align-items: center;
    }
    /* Cuando el sidebar está abierto, el bloque externo [1,4] también contiene el logo
       como descendiente — se le revierten los estilos de tarjeta */
    div[data-testid="stHorizontalBlock"]:has(.cinko-header-logo):has(div[data-testid="stHorizontalBlock"] .cinko-header-logo) {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        padding: 0 !important;
        align-items: flex-start !important;
    }

    /* Panel de filtros */
    .filtros-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 10px;
        padding: 16px;
        color: white;
        margin-bottom: 12px;
    }
</style>
"""


def apply_css():
    st.markdown(APP_CSS, unsafe_allow_html=True)


def fmt(val, decimals=0, prefix="$"):
    if pd.isna(val) or val == 0:
        return f"{prefix}0" if prefix else "0"
    sign    = "-" if val < 0 else ""
    fmt_str = f"{abs(val):,.{decimals}f}"
    return f"{sign}{prefix}{fmt_str}"


def fmt_pct(val):
    if pd.isna(val):
        return "0.0%"
    return f"{val:.1f}%"


def delta_pct(curr, prev):
    if prev and prev != 0:
        return (curr - prev) / abs(prev) * 100
    return None


def render_kpi(label, value, delta=None, prefix="$", delta_fmt="pct"):
    if delta is not None:
        css    = "delta-pos" if delta >= 0 else "delta-neg"
        arrow  = "▲" if delta >= 0 else "▼"
        sufijo = "pp" if delta_fmt == "pp" else "%"
        delta_html = f'<div class="delta {css}">{arrow} {abs(delta):.1f} {sufijo} vs año ant.</div>'
    else:
        delta_html = '<div class="delta delta-neu">— sin dato año ant.</div>'
    return f"""
    <div class="kpi-card">
        <div class="label">{label}</div>
        <div class="value">{fmt(value, prefix=prefix)}</div>
        {delta_html}
    </div>"""
