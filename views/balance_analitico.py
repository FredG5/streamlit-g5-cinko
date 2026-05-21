import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from utils.data import MESES, get_balance_general
from utils.ui import fmt, delta_pct, render_kpi


def render_balance_analitico(data, año, meses_sel):
    saldo_col = "Saldo Final de Mes OK"
    grp_cols  = ["N2 Cuenta", "N2 Nombre Cuenta", "N3 Cuenta", "N3 Nombre Cuenta"]

    # ── Selector de mes (dentro del tab) ─────────────────────────────────────
    mes_disp = sorted(data[data["Año"] == año]["Mes"].unique())
    default  = max((m for m in meses_sel if m in mes_disp), default=mes_disp[-1])
    c_sel, _ = st.columns([1, 3])
    with c_sel:
        sel = st.selectbox(
            "Mes del balance", [MESES[m] for m in mes_disp],
            index=mes_disp.index(default),
            key="bal_analitico_mes",
        )
    mes = next(m for m in mes_disp if MESES[m] == sel)

    st.markdown(
        f'<div style="margin:2px 0 14px;color:#888;font-size:0.85rem;">'
        f'Al cierre de <strong>{MESES[mes]} {año}</strong> '
        f'vs. <strong>{MESES[mes]} {año - 1}</strong></div>',
        unsafe_allow_html=True,
    )

    # ── Datos ─────────────────────────────────────────────────────────────────
    d_c  = data[(data["Año"] == año)     & (data["Mes"] == mes)]
    has_a = mes in set(data[data["Año"] == año - 1]["Mes"].unique())
    d_a  = data[(data["Año"] == año - 1) & (data["Mes"] == mes)] if has_a else pd.DataFrame()

    bg_c = get_balance_general(data, año,     mes)
    bg_a = get_balance_general(data, año - 1, mes) if has_a else None

    ta_c = bg_c["total_activos"]
    ta_a = bg_a["total_activos"]     if bg_a else 0

    # Pasivos en su signo contable (negativo = crédito)
    tp_c = d_c[d_c["N1 Nombre Cuenta"] == "Pasivos"][saldo_col].sum()
    tp_a = (d_a[d_a["N1 Nombre Cuenta"] == "Pasivos"][saldo_col].sum()
            if not d_a.empty else 0)

    cc_c = bg_c["capital_contable"]
    cc_a = bg_a["capital_contable"]  if bg_a else 0
    pc_c = bg_c["total_pasivo_cap"]
    pc_a = bg_a["total_pasivo_cap"]  if bg_a else 0

    # ── KPIs ─────────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        d = delta_pct(ta_c, ta_a) if bg_a else None
        st.markdown(render_kpi("Total Activos", ta_c, d), unsafe_allow_html=True)
    with k2:
        d = delta_pct(bg_c["total_pasivos"], bg_a["total_pasivos"]) if bg_a else None
        st.markdown(render_kpi("Total Pasivos", bg_c["total_pasivos"], d), unsafe_allow_html=True)
    with k3:
        d = delta_pct(cc_c, cc_a) if bg_a else None
        st.markdown(render_kpi("Capital Contable", cc_c, d), unsafe_allow_html=True)
    with k4:
        d = delta_pct(pc_c, pc_a) if bg_a else None
        st.markdown(render_kpi("Total Pasivo + Capital", pc_c, d), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Estilos inline ────────────────────────────────────────────────────────
    TH   = 'style="background:#1a1a2e;color:white;padding:4px 5px;font-size:0.68rem;text-align:center;white-space:nowrap;"'
    TH1  = 'style="background:#1a1a2e;color:white;padding:4px 6px;font-size:0.68rem;text-align:left;min-width:175px;"'
    N2S  = 'style="padding:3px 6px;font-weight:700;font-size:0.71rem;color:#1a1a2e;background:#e8eaf6;"'
    N3S  = 'style="padding:2px 6px 2px 18px;font-size:0.69rem;color:#333;"'
    NUM  = 'style="padding:2px 5px;text-align:right;font-size:0.70rem;"'
    NEG  = 'style="padding:2px 5px;text-align:right;font-size:0.70rem;color:#c62828;"'
    PCT  = 'style="padding:2px 4px;text-align:right;font-size:0.67rem;color:#666;"'
    SUB  = 'style="padding:3px 6px;font-weight:700;font-size:0.71rem;background:#c5cae9;color:#1a1a2e;"'
    SUBN = 'style="padding:3px 5px;text-align:right;font-weight:700;font-size:0.71rem;background:#c5cae9;"'
    SUBP = 'style="padding:3px 4px;text-align:right;font-size:0.68rem;font-weight:600;background:#c5cae9;color:#555;"'
    GRT  = 'style="padding:4px 6px;font-weight:700;font-size:0.71rem;background:#1a1a2e;color:white;"'
    GRTN = 'style="padding:4px 5px;text-align:right;font-weight:700;font-size:0.71rem;background:#1a1a2e;color:white;"'
    GRTP = 'style="padding:4px 4px;text-align:right;font-size:0.68rem;background:#1a1a2e;color:#aaa;"'

    def n(val):
        return fmt(val, prefix="")

    def num_td(val):
        return f'<td {NEG if val < 0 else NUM}>{n(val)}</td>'

    def pct_td(val, total, dec=0):
        if total == 0:
            return f'<td {PCT}>—</td>'
        return f'<td {PCT}>{abs(val / total) * 100:.{dec}f}%</td>'

    def dif_td(curr, ant, dark=False):
        if not has_a or ant == 0:
            base = GRTP if dark else PCT
            return f'<td {base}>—</td>'
        d = (curr - ant) / abs(ant) * 100
        if dark:
            col = "#ff5252" if d < 0 else "#69f0ae"
            return (f'<td style="padding:4px 4px;text-align:right;font-size:0.68rem;'
                    f'background:#1a1a2e;color:{col};">{d:.1f}%</td>')
        bg = "background:#fff0f0;color:#c62828;" if d < 0 else ("color:#2e7d32;" if d > 0 else "")
        return f'<td style="padding:2px 4px;text-align:right;font-size:0.67rem;{bg}">{d:.1f}%</td>'

    def thead(title):
        return (f'<thead><tr><th {TH1}>{title}</th>'
                f'<th {TH}>Monto</th><th {TH}>%</th>'
                f'<th {TH}>Monto Año Ant.</th><th {TH}>%</th>'
                f'<th {TH}>DIF%</th></tr></thead>')

    # ── Filas de sección ──────────────────────────────────────────────────────
    def build_rows(n1, ref_c, ref_a):
        s_c = (d_c[d_c["N1 Nombre Cuenta"] == n1]
               .groupby(grp_cols)[saldo_col].sum())
        s_a = (d_a[d_a["N1 Nombre Cuenta"] == n1]
               .groupby(grp_cols)[saldo_col].sum()
               if not d_a.empty else pd.Series(dtype=float))

        html = ""
        for n2c, n2n in s_c.index.droplevel([2, 3]).unique():
            gc = s_c.xs((n2c, n2n), level=["N2 Cuenta", "N2 Nombre Cuenta"])
            try:
                ga = s_a.xs((n2c, n2n), level=["N2 Cuenta", "N2 Nombre Cuenta"])
            except (KeyError, TypeError):
                ga = pd.Series(dtype=float)

            n2c_val = float(gc.sum())
            n2a_val = float(ga.sum()) if not ga.empty else 0.0
            label   = f"{n2c[:2]} {n2n.title()}"

            html += (f'<tr><td {N2S}>{label}</td>'
                     f'{num_td(n2c_val)}{pct_td(n2c_val, ref_c)}'
                     f'{num_td(n2a_val)}{pct_td(n2a_val, ref_a, 1)}'
                     f'{dif_td(n2c_val, n2a_val)}</tr>')

            ga_dict = ga.to_dict()
            for (n3c, n3n), vc in gc.items():
                va = float(ga_dict.get((n3c, n3n), 0))
                if abs(vc) < 0.5 and abs(va) < 0.5:
                    continue
                html += (f'<tr><td {N3S}>{n3c} {n3n}</td>'
                         f'{num_td(vc)}{pct_td(vc, ref_c)}'
                         f'{num_td(va)}{pct_td(va, ref_a, 1)}'
                         f'{dif_td(vc, va)}</tr>')
        return html

    # ── Tabla Activos ─────────────────────────────────────────────────────────
    act_body  = build_rows("Activos", ta_c, ta_a)
    act_body += (f'<tr><td {GRT}>Total Activos</td>'
                 f'<td {GRTN}>{n(ta_c)}</td><td {GRTP}>100%</td>'
                 f'<td {GRTN}>{n(ta_a) if bg_a else "—"}</td>'
                 f'<td {GRTP}>{"100.0%" if bg_a else "—"}</td>'
                 f'{dif_td(ta_c, ta_a, dark=True)}</tr>')
    act_html = (f'<table class="fin-table bal-table" style="width:100%;">'
                f'{thead("Activo")}<tbody>{act_body}</tbody></table>')

    # ── Tabla Pasivos ─────────────────────────────────────────────────────────
    pas_body  = build_rows("Pasivos", tp_c, tp_a)
    pas_body += (f'<tr><td {GRT}>Total Pasivos</td>'
                 f'<td {GRTN}>{n(tp_c)}</td><td {GRTP}>100%</td>'
                 f'<td {GRTN}>{n(tp_a) if has_a else "—"}</td>'
                 f'<td {GRTP}>{"100.0%" if has_a else "—"}</td>'
                 f'{dif_td(tp_c, tp_a, dark=True)}</tr>')
    pas_html = (f'<table class="fin-table bal-table" style="width:100%;">'
                f'{thead("Pasivo")}<tbody>{pas_body}</tbody></table>')

    # ── Tabla Capital ─────────────────────────────────────────────────────────
    def cap_row(label, vc, va):
        return (f'<tr><td {N3S}>{label}</td>'
                f'{num_td(vc)}{pct_td(vc, cc_c)}'
                f'{num_td(va)}{pct_td(va, cc_a, 1)}'
                f'{dif_td(vc, va)}</tr>')

    cap_body  = cap_row("310-100 Capital Social",
                        bg_c["capital_social"],    bg_a["capital_social"]     if bg_a else 0)
    cap_body += cap_row("Resultados Acum. (Perd.)/Ut.",
                        bg_c["resultados_acum"],   bg_a["resultados_acum"]    if bg_a else 0)
    cap_body += cap_row("Resultado del Ejercicio",
                        bg_c["utilidad_ejercicio"],bg_a["utilidad_ejercicio"] if bg_a else 0)
    cap_body += (f'<tr><td {SUB}>Total Capital Contable</td>'
                 f'<td {SUBN}>{n(cc_c)}</td><td {SUBP}>100%</td>'
                 f'<td {SUBN}>{n(cc_a) if bg_a else "—"}</td>'
                 f'<td {SUBP}>{"100.0%" if bg_a else "—"}</td>'
                 f'{dif_td(cc_c, cc_a)}</tr>')
    cap_body += (f'<tr><td {GRT}>Total Pasivo + Capital</td>'
                 f'<td {GRTN}>{n(pc_c)}</td><td {GRTP}>100%</td>'
                 f'<td {GRTN}>{n(pc_a) if bg_a else "—"}</td>'
                 f'<td {GRTP}>{"100.0%" if bg_a else "—"}</td>'
                 f'{dif_td(pc_c, pc_a, dark=True)}</tr>')
    cap_html = (f'<table class="fin-table bal-table" style="width:100%;margin-top:10px;">'
                f'{thead("Capital")}<tbody>{cap_body}</tbody></table>')

    # ── Layout: Activos izquierda | Pasivos + Capital derecha ─────────────────
    st.markdown(
        f'<div style="display:flex;align-items:stretch;gap:16px;">'
        f'<div style="flex:1;overflow-x:auto;">{act_html}</div>'
        f'<div style="flex:1;overflow-x:auto;display:flex;flex-direction:column;">'
        f'{pas_html}'
        f'<div style="margin-top:auto;">{cap_html}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Gráficas ──────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        chart_labels, chart_values = [], []
        act_n2 = (d_c[d_c["N1 Nombre Cuenta"] == "Activos"]
                  .groupby("N2 Nombre Cuenta")[saldo_col].sum())
        for n2n, val in act_n2.items():
            if val > 0:
                chart_labels.append(n2n.title())
                chart_values.append(float(val))
        if chart_labels:
            colors = ["#1a1a2e", "#2d3561", "#4a5568"]
            fig = go.Figure(go.Pie(
                labels=chart_labels, values=chart_values,
                marker_colors=colors[:len(chart_labels)],
                hole=0.5, textinfo="label+percent", textfont_size=11,
            ))
            fig.update_layout(title="Composición de Activos", template="plotly_white",
                              height=320, margin=dict(t=40, b=10, l=10, r=10), showlegend=False)
            st.plotly_chart(fig, use_container_width=True, key="ba_activos_pie")

    with c2:
        labels_cap = ["Pasivos", "Capital Social", "Resultados Acum.", "Resultado Ejercicio"]
        values_cap = [
            max(bg_c["total_pasivos"],      0),
            max(bg_c["capital_social"],     0),
            max(bg_c["resultados_acum"],    0),
            max(bg_c["utilidad_ejercicio"], 0),
        ]
        colors_cap = ["#d32f2f", "#1a1a2e", "#2d3561", "#00897b"]
        fig2 = go.Figure(go.Pie(
            labels=labels_cap, values=values_cap,
            marker_colors=colors_cap,
            hole=0.5, textinfo="label+percent", textfont_size=11,
        ))
        fig2.update_layout(title="Estructura Financiera", template="plotly_white",
                           height=320, margin=dict(t=40, b=10, l=10, r=10), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True, key="ba_estructura_pie")
