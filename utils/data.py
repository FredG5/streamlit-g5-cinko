import base64

import pandas as pd
import streamlit as st
from pathlib import Path

_ROOT = Path(__file__).parent.parent

MESES = {
    1: "Enero",      2: "Febrero",   3: "Marzo",      4: "Abril",
    5: "Mayo",       6: "Junio",     7: "Julio",       8: "Agosto",
    9: "Septiembre", 10: "Octubre",  11: "Noviembre",  12: "Diciembre",
}


@st.cache_data
def load_data():
    df  = pd.read_excel(_ROOT / "data" / "Tabla_Financieros_G5.xlsx", sheet_name="Financieros")
    cat = pd.read_excel(_ROOT / "data" / "CatCuentas_G5.xlsx",        sheet_name="Cuentas")
    return df.merge(cat, on="N5 Cuenta", how="left")


@st.cache_data
def get_logo_b64():
    return base64.b64encode((_ROOT / "assets" / "logo_cinko.jpg").read_bytes()).decode()


# Hash rápido del DataFrame por forma — data nunca cambia en sesión
_dfhash = lambda df: df.shape


@st.cache_data(hash_funcs={pd.DataFrame: _dfhash})
def get_pl_month(data, year, month):
    d   = data[(data["Año"] == year) & (data["Mes"] == month)]
    mov = "Saldo Movimientos del Mes OK"

    ventas       = -d[d["N1 Nombre Cuenta"] == "Ingresos"][mov].sum()
    costo        =  d[d["N1 Nombre Cuenta"] == "Costo de Ventas"][mov].sum()
    contribucion = ventas - costo

    gastos_df    = d[d["N1 Nombre Cuenta"] == "Gastos"]
    nominas      = gastos_df[gastos_df["N4 Nombre Cuenta"] == "Nóminas"][mov].sum()
    logistica    = gastos_df[gastos_df["N4 Nombre Cuenta"] == "Logística"][mov].sum()
    gtos_venta   = gastos_df[gastos_df["N4 Nombre Cuenta"] == "Gastos de Venta"][mov].sum()
    gtos_admin   = gastos_df[gastos_df["N4 Nombre Cuenta"] == "Gastos Administrativos"][mov].sum()
    total_gastos = nominas + logistica + gtos_venta + gtos_admin
    ebitda       = contribucion - total_gastos

    financieros  =  d[d["N1 Nombre Cuenta"] == "Financieros"][mov].sum()
    otros_df     =  d[d["N1 Nombre Cuenta"] == "Otros Ingresos y Egresos"]
    impuestos    =  otros_df[otros_df["N4 Nombre Cuenta"].isin(["ISR PROVISION", "PTU PROVISION"])][mov].sum()
    otros_netos  =  otros_df[mov].sum() - impuestos
    utilidad_neta = ebitda - financieros - impuestos - otros_netos

    v = ventas if ventas else 1
    return {
        "ventas": ventas, "costo": costo, "pct_costo": costo / v * 100,
        "contribucion": contribucion, "pct_contrib": contribucion / v * 100,
        "nominas": nominas, "logistica": logistica,
        "gtos_venta": gtos_venta, "gtos_admin": gtos_admin,
        "total_gastos": total_gastos, "pct_gastos": total_gastos / v * 100,
        "ebitda": ebitda, "pct_ebitda": ebitda / v * 100,
        "financieros": -financieros, "impuestos": -(impuestos + otros_netos),
        "utilidad_neta": utilidad_neta, "pct_utilidad": utilidad_neta / v * 100,
    }


@st.cache_data(hash_funcs={pd.DataFrame: _dfhash})
def get_pl_ytd(data, year, months):
    disponibles = set(data[data["Año"] == year]["Mes"].unique())
    rows = [get_pl_month(data, year, m) for m in months if m in disponibles]
    if not rows:
        return None
    keys = ["ventas", "costo", "contribucion", "nominas", "logistica",
            "gtos_venta", "gtos_admin", "total_gastos", "ebitda",
            "financieros", "impuestos", "utilidad_neta"]
    t = {k: sum(r[k] for r in rows) for k in keys}
    v = t["ventas"] if t["ventas"] else 1
    t.update({
        "pct_costo":    t["costo"]         / v * 100,
        "pct_contrib":  t["contribucion"]  / v * 100,
        "pct_gastos":   t["total_gastos"]  / v * 100,
        "pct_ebitda":   t["ebitda"]        / v * 100,
        "pct_utilidad": t["utilidad_neta"] / v * 100,
    })
    return t


@st.cache_data(hash_funcs={pd.DataFrame: _dfhash})
def get_flujo_mes(data, year, month):
    """Cash flow for a single month — indirect method, replicating Power BI DAX logic.
    Flujo column sign convention: -movement for all accounts except N3=110-000 (cash)."""
    df  = data[(data["Año"] == year) & (data["Mes"] == month)]
    mov = "Saldo Movimientos del Mes OK"

    def fs(mask):
        return -float(df.loc[mask, mov].sum())

    # ── Utilidad Neta (P&L) ───────────────────────────────────────────────────
    utilidad_neta = get_pl_month(data, year, month)["utilidad_neta"]

    # ── No-cash charges ───────────────────────────────────────────────────────
    dep_n4   = {"183-200","183-300","184-300","185-300","186-300"}
    amort_n4 = {"192-200","192-210"}
    depreciaciones = fs(df["N4 Cuenta"].isin(dep_n4))
    amortizaciones = fs(df["N4 Cuenta"].isin(amort_n4))
    gasto_fin      = fs(df["N4 Cuenta"] == "720-002")
    cargos = utilidad_neta + depreciaciones + amortizaciones - gasto_fin

    # ── Capital de Trabajo ────────────────────────────────────────────────────
    # Impuestos: double-negative cancels → +SUM(movement for N5=140-102)
    impuestos = float(df[df["N5 Cuenta"] == "140-102"][mov].sum())
    cxc       = fs(df["N3 Cuenta"].isin({"120-000","130-000"})) - impuestos
    inv_ctw   = fs(df["N3 Cuenta"] == "160-000")
    cxp       = (fs(df["N3 Cuenta"].isin({"210-000","230-000","236-000","240-000","250-000"}))
                 + fs(df["N3 Cuenta"] == "256-000"))
    pago_div  = fs(df["N3 Cuenta"] == "320-000")
    ctw       = cxc + inv_ctw + cxp + pago_div
    fno       = cargos + ctw

    # ── Inversiones ───────────────────────────────────────────────────────────
    inv_fijo = fs(df["N2 Cuenta"] == "180-000") - depreciaciones
    diferido = fs(df["N2 Cuenta"] == "190-000") - amortizaciones
    inv_neta = inv_fijo + diferido

    # ── Cascada ───────────────────────────────────────────────────────────────
    f_imp   = fno + inv_neta
    f_serv  = f_imp  + impuestos
    f_deuda = f_serv + gasto_fin
    sobrante  = f_deuda          # + financiamiento LP (0)
    f_periodo = sobrante         # + aportación capital (0)

    # ── Saldos Efectivo (N3=110-000) ─────────────────────────────────────────
    cash      = df[df["N3 Cuenta"] == "110-000"]
    saldo_ini = float(cash["Saldo Inicial de Mes OK"].sum())
    saldo_fin = float(cash["Saldo Final de Mes OK"].sum())

    return {
        "cargos":     cargos,
        "cxc":        cxc,
        "inv_ctw":    inv_ctw,
        "cxp":        cxp,
        "pago_div":   pago_div,
        "ctw":        ctw,
        "fno":        fno,
        "inv_fijo":   inv_fijo,
        "diferido":   diferido,
        "inv_neta":   inv_neta,
        "f_imp":      f_imp,
        "impuestos":  impuestos,
        "f_serv":     f_serv,
        "gasto_fin":  gasto_fin,
        "f_deuda":    f_deuda,
        "sobrante":   sobrante,
        "f_periodo":  f_periodo,
        "saldo_ini":  saldo_ini,
        "saldo_fin":  saldo_fin,
    }


@st.cache_data(hash_funcs={pd.DataFrame: _dfhash})
def get_balance_general(data, year, snapshot_month):
    """Balance sheet snapshot at snapshot_month closing balance.
    YTD net income uses all available months from start of year to snapshot_month."""
    saldo  = "Saldo Final de Mes OK"
    rb_col = "Resultaods/Balance"

    d = data[(data["Año"] == year) & (data["Mes"] == snapshot_month)]

    disponibles  = sorted(data[data["Año"] == year]["Mes"].unique())
    ytd_months   = [m for m in disponibles if m <= snapshot_month]

    # ── Activos (+SUM) ────────────────────────────────────────────────────────
    act           = d[d["N1 Nombre Cuenta"] == "Activos"]
    total_activos = act[saldo].sum()

    # ── Pasivos (-SUM) ────────────────────────────────────────────────────────
    pas           = d[d["N1 Nombre Cuenta"] == "Pasivos"]
    total_pasivos = -pas[saldo].sum()

    # ── Capital Contable ──────────────────────────────────────────────────────
    cap             = d[d["N1 Nombre Cuenta"] == "Capital Contable"]
    capital_social  = -cap[cap["N3 Cuenta"] == "310-100"][saldo].sum()
    resultados_acum = -cap[cap["N3 Cuenta"] == "320-000"][saldo].sum()
    resultados_pl   = -d[d[rb_col] == "Resultados"][saldo].sum()
    pl_ytd          = get_pl_ytd(data, year, ytd_months)
    utilidad_ytd    = pl_ytd["utilidad_neta"] if pl_ytd else 0
    saldo_utilidad  = resultados_pl - utilidad_ytd + resultados_acum
    capital_contable = capital_social + saldo_utilidad + utilidad_ytd
    total_pasivo_cap = total_pasivos + capital_contable

    return {
        "total_activos":      total_activos,
        "total_pasivos":      total_pasivos,
        "capital_social":     capital_social,
        "resultados_acum":    saldo_utilidad,
        "utilidad_ejercicio": utilidad_ytd,
        "capital_contable":   capital_contable,
        "total_pasivo_cap":   total_pasivo_cap,
    }
