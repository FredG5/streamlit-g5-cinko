import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from utils.data import MESES, get_balance_general
from utils.ui import fmt, delta_pct, render_kpi


def render_balance_general(data, año, meses_sel):
    last_month = max(meses_sel)

    # Balance snapshot for each selected month (columns) and KPI comparison
    bgs    = {m: get_balance_general(data, año, m) for m in meses_sel}
    bg_ult = bgs[last_month]

    ant_disp = set(data[data["Año"] == año - 1]["Mes"].unique())
    bg_ant   = get_balance_general(data, año - 1, last_month) if last_month in ant_disp else None

    # ── Subtítulo ──────────────────────────────────────────────────────────────
    fecha_str = f"Al cierre de {MESES[last_month]} {año}"
    st.markdown(
        f'<div style="margin:0 0 16px 0;">'
        f'<span style="font-size:1.1rem;font-weight:600;color:#1a1a2e;">Balance General</span>'
        f'<span style="color:#888;font-size:0.9rem;margin-left:10px;">Grupo Cinko · {fecha_str}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── KPIs ──────────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        d = delta_pct(bg_ult["total_activos"], bg_ant["total_activos"]) if bg_ant else None
        st.markdown(render_kpi("Total Activos", bg_ult["total_activos"], d), unsafe_allow_html=True)
    with k2:
        d = delta_pct(bg_ult["total_pasivos"], bg_ant["total_pasivos"]) if bg_ant else None
        st.markdown(render_kpi("Total Pasivos", bg_ult["total_pasivos"], d), unsafe_allow_html=True)
    with k3:
        d = delta_pct(bg_ult["capital_contable"], bg_ant["capital_contable"]) if bg_ant else None
        st.markdown(render_kpi("Capital Contable", bg_ult["capital_contable"], d), unsafe_allow_html=True)
    with k4:
        d = delta_pct(bg_ult["total_pasivo_cap"], bg_ant["total_pasivo_cap"]) if bg_ant else None
        st.markdown(render_kpi("Total Pasivo + Capital", bg_ult["total_pasivo_cap"], d), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="section-header">Balance General — Detalle'
        ' <small style="font-weight:400;font-size:0.72em;opacity:0.8;">($ MXN)</small></div>',
        unsafe_allow_html=True,
    )

    # ── Pivots N2/N3 por mes ──────────────────────────────────────────────────
    saldo_col  = "Saldo Final de Mes OK"
    d_sel      = data[(data["Año"] == año) & (data["Mes"].isin(meses_sel))]
    grp_cols   = ["N2 Cuenta", "N2 Nombre Cuenta", "N3 Cuenta", "N3 Nombre Cuenta", "Mes"]

    def pivot(n1, sign=1):
        df = d_sel[d_sel["N1 Nombre Cuenta"] == n1]
        if df.empty:
            return pd.DataFrame()
        return (
            df.groupby(grp_cols)[saldo_col]
            .sum()
            .mul(sign)
            .unstack("Mes")
            .reindex(columns=meses_sel, fill_value=0)
            .fillna(0)
        )

    act_piv = pivot("Activos",  sign=1)
    pas_piv = pivot("Pasivos",  sign=-1)

    # ── HTML helpers ──────────────────────────────────────────────────────────
    n_cols = len(meses_sel)

    def cv(val):
        css = "negative" if val < 0 else ""
        return f'<td class="{css}">{fmt(val, prefix="")}</td>'

    def cells(src):
        result = []
        for m in meses_sel:
            try:
                result.append(cv(float(src[m])))
            except (KeyError, IndexError, TypeError):
                result.append("<td>—</td>")
        return "".join(result)

    def cells_bg(key):
        return cells({m: bgs[m][key] for m in meses_sel})

    sec  = ('style="background:#f0f4ff;font-weight:700;color:#1a1a2e;'
            'padding:3px 6px;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.4px;"')
    n2s  = 'style="padding-left:10px;font-weight:600;font-size:0.73rem;color:#2d3561;background:#f8f9ff;"'
    n3s  = 'style="padding-left:22px;font-size:0.68rem;color:#555;padding-top:1px;padding-bottom:1px;"'
    caps = 'style="padding-left:10px;"'
    sep  = f'<tr class="separator"><td></td>{"<td></td>" * n_cols}</tr>'

    months_header = "".join(f"<th>{MESES[m][:3]}</th>" for m in meses_sel)

    def section_rows(piv, sec_label):
        html = f'<tr><td colspan="{n_cols + 1}" {sec}>{sec_label}</td></tr>'
        if piv.empty:
            return html
        for (n2, n2_nombre), grp_raw in piv.groupby(level=["N2 Cuenta", "N2 Nombre Cuenta"]):
            grp      = grp_raw.droplevel(["N2 Cuenta", "N2 Nombre Cuenta"])
            n2_total = grp.sum()
            html += f'<tr><td {n2s}>{n2_nombre.title()}</td>{cells(n2_total)}</tr>'
            for (n3, n3_nombre), row in grp.iterrows():
                if row.abs().sum() > 0.5:
                    html += f'<tr><td {n3s}>{n3_nombre}</td>{cells(row)}</tr>'
        return html

    rows  = section_rows(act_piv, "Activos")
    rows += f'<tr class="subtotal"><td>Total Activos</td>{cells_bg("total_activos")}</tr>'
    rows += sep
    rows += section_rows(pas_piv, "Pasivos")
    rows += f'<tr class="subtotal"><td>Total Pasivos</td>{cells_bg("total_pasivos")}</tr>'
    rows += sep
    rows += f'<tr><td colspan="{n_cols + 1}" {sec}>Capital Contable</td></tr>'
    rows += f'<tr><td {caps}>Capital Social</td>{cells_bg("capital_social")}</tr>'
    rows += f'<tr><td {caps}>Resultados Acumulados</td>{cells_bg("resultados_acum")}</tr>'
    rows += f'<tr><td {caps}>Resultado del Ejercicio</td>{cells_bg("utilidad_ejercicio")}</tr>'
    rows += f'<tr class="subtotal"><td>Total Capital Contable</td>{cells_bg("capital_contable")}</tr>'
    rows += sep
    rows += f'<tr class="subtotal"><td>Total Pasivo + Capital</td>{cells_bg("total_pasivo_cap")}</tr>'

    st.markdown(
        f'<div style="overflow-x:auto;"><table class="fin-table bal-table">'
        f'<thead><tr><th style="min-width:130px;">Concepto</th>{months_header}</tr></thead>'
        f'<tbody>{rows}</tbody></table></div>',
        unsafe_allow_html=True,
    )

    # ── Gráficas (último mes seleccionado) ────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        chart_labels, chart_values, chart_colors = [], [], ["#1a1a2e", "#2d3561", "#4a5568"]
        if not act_piv.empty:
            for i, ((n2, n2_nombre), grp_raw) in enumerate(
                act_piv.groupby(level=["N2 Cuenta", "N2 Nombre Cuenta"])
            ):
                val = float(grp_raw.droplevel(["N2 Cuenta", "N2 Nombre Cuenta"]).sum()[last_month])
                if val > 0:
                    chart_labels.append(n2_nombre.title())
                    chart_values.append(val)
        if chart_labels:
            fig = go.Figure(go.Pie(
                labels=chart_labels, values=chart_values,
                marker_colors=chart_colors[:len(chart_labels)],
                hole=0.5, textinfo="label+percent", textfont_size=11,
            ))
            fig.update_layout(title="Composición de Activos", template="plotly_white",
                              height=320, margin=dict(t=40, b=10, l=10, r=10), showlegend=False)
            st.plotly_chart(fig, use_container_width=True, key="bg_activos_pie")

    with c2:
        labels_cap = ["Pasivos", "Capital Social", "Resultados Acum.", "Resultado Ejercicio"]
        values_cap = [
            max(bg_ult["total_pasivos"],      0),
            max(bg_ult["capital_social"],     0),
            max(bg_ult["resultados_acum"],    0),
            max(bg_ult["utilidad_ejercicio"], 0),
        ]
        colors_cap = ["#d32f2f", "#1a1a2e", "#2d3561", "#00897b"]
        fig2 = go.Figure(go.Pie(
            labels=labels_cap, values=values_cap,
            marker_colors=colors_cap,
            hole=0.5, textinfo="label+percent", textfont_size=11,
        ))
        fig2.update_layout(title="Estructura Financiera", template="plotly_white",
                           height=320, margin=dict(t=40, b=10, l=10, r=10), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True, key="bg_estructura_pie")
