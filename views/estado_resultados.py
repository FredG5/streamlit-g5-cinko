import streamlit as st
import plotly.graph_objects as go

from utils.data import MESES, get_logo_b64, get_pl_month, get_pl_ytd
from utils.ui import fmt, fmt_pct, delta_pct, render_kpi


def render_shared_header(año, meses_sel, authenticator=None):
    logo_b64 = get_logo_b64()

    col_card, col_menu = st.columns([11, 1], vertical_alignment="center")
    with col_card:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:20px;">'
            f'<img src="data:image/jpeg;base64,{logo_b64}" class="cinko-header-logo"'
            f' style="height:56px;object-fit:contain;border-radius:5px;flex-shrink:0;">'
            f'<div>'
            f'<div style="font-size:1.8rem;font-weight:800;color:#000;line-height:1.1;">Estados Financieros</div>'
            f'<div style="font-size:0.9rem;color:#555;margin-top:4px;font-weight:500;">Grupo Cinko Consultores</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    with col_menu:
        with st.popover("☰", use_container_width=True):
            st.markdown(
                '<p style="font-size:0.72rem;text-transform:uppercase;letter-spacing:1px;'
                'color:#888;font-weight:600;margin:0 0 8px;">Menú</p>',
                unsafe_allow_html=True,
            )
            if authenticator:
                authenticator.logout(
                    "⏻  Cerrar sesión", location="main",
                    key="logout_menu", use_container_width=True,
                )

    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
    icon = "◀ Filtros" if st.session_state.sidebar_open else "☰ Filtros"
    if st.button(icon, key="toggle_btn"):
        st.session_state.sidebar_open = not st.session_state.sidebar_open
        st.rerun()

    if len(meses_sel) == 1:
        periodo_str = f"{MESES[meses_sel[0]]} {año}"
    else:
        periodo_str = f"{MESES[meses_sel[0]]} – {MESES[meses_sel[-1]]} {año}"

    st.markdown(f"""
    <div style="margin: 6px 0 8px 0;">
        <span style="font-size:1.1rem; font-weight:600; color:#1a1a2e;">
            Inteligencia Financiera
        </span>
        <span style="color:#888; font-size:0.9rem; margin-left:10px;">
            Grupo Cinko · {periodo_str}
        </span>
    </div>
    """, unsafe_allow_html=True)


def render_estado_resultados(data, año, meses_sel):
    # ── KPIs ──────────────────────────────────────────────────────────────────
    pl_ytd     = get_pl_ytd(data, año,     meses_sel)
    pl_ytd_ant = get_pl_ytd(data, año - 1, meses_sel)

    if not pl_ytd:
        st.warning("No hay datos para el periodo seleccionado.")
        return

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        d = delta_pct(pl_ytd["ventas"], pl_ytd_ant["ventas"]) if pl_ytd_ant else None
        st.markdown(render_kpi("Ventas Netas", pl_ytd["ventas"], d), unsafe_allow_html=True)
    with k2:
        d = delta_pct(pl_ytd["contribucion"], pl_ytd_ant["contribucion"]) if pl_ytd_ant else None
        st.markdown(render_kpi("Contribución Marginal", pl_ytd["contribucion"], d), unsafe_allow_html=True)
    with k3:
        d = delta_pct(pl_ytd["ebitda"], pl_ytd_ant["ebitda"]) if pl_ytd_ant else None
        st.markdown(render_kpi("EBITDA", pl_ytd["ebitda"], d), unsafe_allow_html=True)
    with k4:
        d = (pl_ytd["pct_ebitda"] - pl_ytd_ant["pct_ebitda"]) if pl_ytd_ant else None
        st.markdown(render_kpi("% EBITDA", pl_ytd["pct_ebitda"], d,
                               prefix="", delta_fmt="pp"), unsafe_allow_html=True)
    with k5:
        d = delta_pct(pl_ytd["utilidad_neta"], pl_ytd_ant["utilidad_neta"]) if pl_ytd_ant else None
        st.markdown(render_kpi("Utilidad Neta", pl_ytd["utilidad_neta"], d), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabla mensual ─────────────────────────────────────────────────────────
    st.markdown(
        '<div class="section-header">Estado de Resultados — Detalle Mensual'
        ' <small style="font-weight:400;font-size:0.72em;opacity:0.8;">($ MXN)</small></div>',
        unsafe_allow_html=True,
    )

    meses_data = [get_pl_month(data, año, m) for m in meses_sel]

    keys_suma = ["ventas", "costo", "contribucion", "nominas", "logistica",
                 "gtos_venta", "gtos_admin", "total_gastos", "ebitda",
                 "financieros", "impuestos", "utilidad_neta"]
    total = {k: sum(m[k] for m in meses_data) for k in keys_suma}
    v = total["ventas"] if total["ventas"] else 1
    total.update({
        "pct_costo":    total["costo"]         / v * 100,
        "pct_contrib":  total["contribucion"]  / v * 100,
        "pct_gastos":   total["total_gastos"]  / v * 100,
        "pct_ebitda":   total["ebitda"]        / v * 100,
        "pct_utilidad": total["utilidad_neta"] / v * 100,
    })

    def cell(val, is_pct=False):
        if is_pct:
            return f'<td class="pct">{fmt_pct(val)}</td>'
        css = "negative" if val < 0 else ""
        return f'<td class="{css}">{fmt(val, prefix="")}</td>'

    def row_cells(key, is_pct=False):
        return "".join(cell(m[key], is_pct) for m in meses_data) + cell(total[key], is_pct)

    n_cols        = len(meses_sel) + 1
    sep           = f'<tr class="separator"><td></td>{"<td></td>" * n_cols}</tr>'
    months_header = "".join(f"<th>{MESES[m][:3]}</th>" for m in meses_sel)

    ind = 'style="padding-left:16px;"'
    st.markdown(
        f'<div style="overflow-x:auto;"><table class="fin-table bal-table">'
        f'<thead><tr><th style="min-width:130px;">Concepto</th>{months_header}<th>Total</th></tr></thead>'
        f'<tbody>'
        f'<tr><td>Ventas Netas</td>{row_cells("ventas")}</tr>'
        f'<tr><td>Costo de Ventas</td>{row_cells("costo")}</tr>'
        f'<tr><td class="pct">% Costo de Ventas</td>{row_cells("pct_costo", True)}</tr>'
        f'{sep}'
        f'<tr class="subtotal"><td>Contribución Marginal</td>{row_cells("contribucion")}</tr>'
        f'<tr><td class="pct">% Contribución Marginal</td>{row_cells("pct_contrib", True)}</tr>'
        f'{sep}'
        f'<tr><td {ind}>Nóminas</td>{row_cells("nominas")}</tr>'
        f'<tr><td {ind}>Logística</td>{row_cells("logistica")}</tr>'
        f'<tr><td {ind}>Gastos de Venta</td>{row_cells("gtos_venta")}</tr>'
        f'<tr><td {ind}>Gastos Administrativos</td>{row_cells("gtos_admin")}</tr>'
        f'<tr class="subtotal"><td>Total Gastos</td>{row_cells("total_gastos")}</tr>'
        f'<tr><td class="pct">% Gastos / Ventas</td>{row_cells("pct_gastos", True)}</tr>'
        f'{sep}'
        f'<tr class="subtotal"><td>EBITDA</td>{row_cells("ebitda")}</tr>'
        f'<tr><td class="pct">% EBITDA</td>{row_cells("pct_ebitda", True)}</tr>'
        f'{sep}'
        f'<tr><td {ind}>Producto Financiero</td>{row_cells("financieros")}</tr>'
        f'<tr><td {ind}>Impuestos y Otros</td>{row_cells("impuestos")}</tr>'
        f'{sep}'
        f'<tr class="subtotal"><td>Utilidad Neta</td>{row_cells("utilidad_neta")}</tr>'
        f'<tr><td class="pct">% Utilidad Neta</td>{row_cells("pct_utilidad", True)}</tr>'
        f'</tbody></table></div>',
        unsafe_allow_html=True,
    )

    # ── Gráficas ──────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    months_labels = [MESES[m][:3] for m in meses_sel]
    ventas_vals   = [m["ventas"]        for m in meses_data]
    ebitda_vals   = [m["ebitda"]        for m in meses_data]
    utilidad_vals = [m["utilidad_neta"] for m in meses_data]

    with c1:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=months_labels, y=ventas_vals, name="Ventas",
                             marker_color="#1a1a2e", opacity=0.7))
        fig.add_trace(go.Scatter(x=months_labels, y=ebitda_vals, name="EBITDA",
                                 line=dict(color="#00e676", width=3), mode="lines+markers"))
        fig.add_trace(go.Scatter(x=months_labels, y=utilidad_vals, name="Utilidad Neta",
                                 line=dict(color="#ff9800", width=3), mode="lines+markers"))
        fig.update_layout(title="Ventas, EBITDA y Utilidad Neta", template="plotly_white",
                          height=380, margin=dict(t=40, b=40),
                          legend=dict(orientation="h", y=-0.15), yaxis_tickformat="$,.0f")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=months_labels, y=[m["pct_ebitda"] for m in meses_data],
                                  name="% EBITDA", line=dict(color="#1a1a2e", width=3),
                                  mode="lines+markers", fill="tozeroy",
                                  fillcolor="rgba(26,26,46,0.1)"))
        fig2.add_trace(go.Scatter(x=months_labels, y=[m["pct_utilidad"] for m in meses_data],
                                  name="% Utilidad Neta", line=dict(color="#ff9800", width=3),
                                  mode="lines+markers"))
        fig2.add_trace(go.Scatter(x=months_labels, y=[m["pct_costo"] for m in meses_data],
                                  name="% Costo de Ventas",
                                  line=dict(color="#d32f2f", width=2, dash="dash"), mode="lines"))
        fig2.update_layout(title="Márgenes Mensuales (%)", template="plotly_white",
                           height=380, margin=dict(t=40, b=40),
                           legend=dict(orientation="h", y=-0.15), yaxis_ticksuffix="%")
        st.plotly_chart(fig2, use_container_width=True)
