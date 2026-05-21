import streamlit as st
import plotly.graph_objects as go

from utils.data import MESES, get_flujo_mes
from utils.ui import fmt, delta_pct, render_kpi


def render_flujo_efectivo(data, año, meses_sel):
    meses_data = [get_flujo_mes(data, año, m) for m in meses_sel]

    if not meses_data:
        st.warning("No hay datos para el periodo seleccionado.")
        return

    # ── Totales (suma mensual, excepto saldos que usan primero/último) ────────
    sum_keys = ["cargos","cxc","inv_ctw","cxp","pago_div","ctw","fno",
                "inv_fijo","diferido","inv_neta","f_imp","impuestos",
                "f_serv","gasto_fin","f_deuda","sobrante","f_periodo"]
    total = {k: sum(m[k] for m in meses_data) for k in sum_keys}
    total["saldo_ini"] = meses_data[0]["saldo_ini"]
    total["saldo_fin"] = meses_data[-1]["saldo_fin"]

    # ── KPIs ─────────────────────────────────────────────────────────────────
    meses_ant = sorted(set(data[data["Año"] == año - 1]["Mes"].unique()) & set(meses_sel))
    if meses_ant:
        data_ant   = [get_flujo_mes(data, año - 1, m) for m in meses_ant]
        total_ant  = {k: sum(m[k] for m in data_ant) for k in sum_keys}
        total_ant["saldo_ini"] = data_ant[0]["saldo_ini"]
        total_ant["saldo_fin"] = data_ant[-1]["saldo_fin"]
    else:
        total_ant = None

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        d = delta_pct(total["fno"], total_ant["fno"]) if total_ant else None
        st.markdown(render_kpi("Flujo Neto de Operación", total["fno"], d), unsafe_allow_html=True)
    with k2:
        d = delta_pct(total["f_periodo"], total_ant["f_periodo"]) if total_ant else None
        st.markdown(render_kpi("Flujo del Periodo", total["f_periodo"], d), unsafe_allow_html=True)
    with k3:
        d = delta_pct(total["saldo_ini"], total_ant["saldo_ini"]) if total_ant else None
        st.markdown(render_kpi("Saldo Inicial Efectivo", total["saldo_ini"], d), unsafe_allow_html=True)
    with k4:
        d = delta_pct(total["saldo_fin"], total_ant["saldo_fin"]) if total_ant else None
        st.markdown(render_kpi("Saldo Final Efectivo", total["saldo_fin"], d), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="section-header">Flujo de Efectivo — Método Indirecto'
        ' <small style="font-weight:400;font-size:0.72em;opacity:0.8;">($ MXN)</small></div>',
        unsafe_allow_html=True,
    )

    # ── Helpers de tabla ─────────────────────────────────────────────────────
    n_cols        = len(meses_sel) + 1
    months_header = "".join(f"<th>{MESES[m][:3]}</th>" for m in meses_sel)

    def cv(val):
        css = "negative" if val < 0 else ""
        return f'<td class="{css}">{fmt(val, prefix="")}</td>'

    def row_cells(key):
        return "".join(cv(m[key]) for m in meses_data) + cv(total[key])

    def row_cells_custom(vals, tot):
        return "".join(cv(v) for v in vals) + cv(tot)

    sep = f'<tr class="separator"><td></td>{"<td></td>" * n_cols}</tr>'
    ind = 'style="padding-left:18px;font-weight:normal;"'

    # ── Filas de saldo (no se suman en total) ─────────────────────────────────
    saldo_ini_cells = "".join(cv(m["saldo_ini"]) for m in meses_data) + cv(total["saldo_ini"])
    saldo_fin_cells = "".join(cv(m["saldo_fin"]) for m in meses_data) + cv(total["saldo_fin"])

    st.markdown(
        f'<div style="overflow-x:auto;"><table class="fin-table bal-table">'
        f'<thead><tr><th style="min-width:200px;">Concepto</th>{months_header}<th>Total</th></tr></thead>'
        f'<tbody>'
        f'<tr class="subtotal"><td>EBITDA Ut. Ant. (Imp – Dep – Amort)</td>{row_cells("cargos")}</tr>'
        f'{sep}'
        f'<tr><td {ind}>Variación CXC</td>{row_cells("cxc")}</tr>'
        f'<tr><td {ind}>Variación Inventarios</td>{row_cells("inv_ctw")}</tr>'
        f'<tr><td {ind}>Variación CXP</td>{row_cells("cxp")}</tr>'
        f'<tr><td {ind}>Pago de Dividendos</td>{row_cells("pago_div")}</tr>'
        f'<tr class="subtotal"><td>Capital de Trabajo Neto</td>{row_cells("ctw")}</tr>'
        f'{sep}'
        f'<tr class="subtotal"><td>Flujo Neto de Operación</td>{row_cells("fno")}</tr>'
        f'{sep}'
        f'<tr><td {ind}>Inversión Activo Fijo</td>{row_cells("inv_fijo")}</tr>'
        f'<tr><td {ind}>Diferido</td>{row_cells("diferido")}</tr>'
        f'<tr class="subtotal"><td>Inversión Neta</td>{row_cells("inv_neta")}</tr>'
        f'{sep}'
        f'<tr class="subtotal"><td>Flujo Disp. para Impuestos</td>{row_cells("f_imp")}</tr>'
        f'<tr><td {ind}>Impuestos</td>{row_cells("impuestos")}</tr>'
        f'<tr class="subtotal"><td>Flujo Disp. para Servicio de Deuda</td>{row_cells("f_serv")}</tr>'
        f'<tr><td {ind}>Gasto Financiero</td>{row_cells("gasto_fin")}</tr>'
        f'<tr class="subtotal"><td>Flujo Disp. para Pago de Deuda</td>{row_cells("f_deuda")}</tr>'
        f'{sep}'
        f'<tr class="subtotal"><td>SOBRANTE / FALTANTE</td>{row_cells("sobrante")}</tr>'
        f'{sep}'
        f'<tr class="subtotal"><td style="font-size:0.74rem;letter-spacing:0.3px;">FLUJO DEL PERIODO</td>{row_cells("f_periodo")}</tr>'
        f'{sep}'
        f'<tr><td style="color:#555;">Saldo Inicial Efectivo</td>{saldo_ini_cells}</tr>'
        f'<tr><td style="color:#555;">Saldo Final Efectivo</td>{saldo_fin_cells}</tr>'
        f'</tbody></table></div>',
        unsafe_allow_html=True,
    )

    # ── Gráficas ──────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    labels = [MESES[m][:3] for m in meses_sel]

    with c1:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=labels, y=[m["fno"] for m in meses_data],
            name="Flujo Neto de Operación", marker_color="#1a1a2e", opacity=0.8,
        ))
        fig.add_trace(go.Scatter(
            x=labels, y=[m["f_periodo"] for m in meses_data],
            name="Flujo del Periodo", line=dict(color="#00e676", width=3),
            mode="lines+markers",
        ))
        fig.update_layout(
            title="Flujo Neto de Operación vs Flujo del Periodo",
            template="plotly_white", height=360,
            margin=dict(t=40, b=40),
            legend=dict(orientation="h", y=-0.18),
            yaxis_tickformat="$,.0f",
        )
        st.plotly_chart(fig, use_container_width=True, key="fe_flujo_bar")

    with c2:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=labels, y=[m["saldo_ini"] for m in meses_data],
            name="Saldo Inicial", line=dict(color="#90a4ae", width=2, dash="dot"),
            mode="lines+markers",
        ))
        fig2.add_trace(go.Scatter(
            x=labels, y=[m["saldo_fin"] for m in meses_data],
            name="Saldo Final", line=dict(color="#1a1a2e", width=3),
            mode="lines+markers", fill="tonexty",
            fillcolor="rgba(26,26,46,0.07)",
        ))
        fig2.update_layout(
            title="Evolución del Saldo de Efectivo",
            template="plotly_white", height=360,
            margin=dict(t=40, b=40),
            legend=dict(orientation="h", y=-0.18),
            yaxis_tickformat="$,.0f",
        )
        st.plotly_chart(fig2, use_container_width=True, key="fe_saldo_line")
