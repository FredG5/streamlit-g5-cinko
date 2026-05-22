import streamlit as st
import anthropic

from utils.data import get_pl_month, get_pl_ytd, get_balance_general, get_flujo_mes, MESES

MAX_PREGUNTAS = 20

_SYSTEM_PROMPT = (
    "Eres un analista financiero experto de Grupo Cinko Consultores. "
    "Respondes preguntas sobre los datos financieros de la empresa en español, "
    "de forma clara y concisa.\n\n"
    "Definiciones clave:\n"
    "- Contribución Marginal = Ventas - Costo de Ventas\n"
    "- EBITDA = Contribución Marginal - Gastos Operativos "
    "(Nóminas + Logística + Gastos de Venta + Gastos Administrativos)\n"
    "- Utilidad Neta = EBITDA - Producto Financiero - Impuestos\n\n"
    "Reglas:\n"
    "- Si no puedes responder con los datos disponibles, dilo honestamente.\n"
    "- Formatea montos en pesos mexicanos con separador de miles (ej: $1,234,567).\n"
    "- Cuando sea relevante, menciona variaciones porcentuales vs año anterior.\n"
    "- Responde siempre en español."
)


def _fmt(val):
    if not val:
        return "$0"
    return f"${val:,.0f}"


def _pct(val):
    return f"{val:.1f}%"


def build_financial_context(data, año, meses_sel):
    """Genera resumen de texto con los datos financieros del periodo seleccionado."""
    año_ant = año - 1
    partes  = []

    nombres = [MESES[m] for m in meses_sel]
    partes.append(f"Periodo: {año} | Meses: {', '.join(nombres)}\n")

    # ── Estado de Resultados mensual ──────────────────────────────────────────
    partes.append("=== ESTADO DE RESULTADOS MENSUAL ===")
    for mes in meses_sel:
        try:
            pl  = get_pl_month(data, año,     mes)
            pla = get_pl_month(data, año_ant, mes)
            nm  = MESES[mes]
            partes.append(f"\n{nm} {año}:")
            partes.append(f"  Ventas:                {_fmt(pl['ventas'])}")
            partes.append(f"  Costo de Ventas:       {_fmt(pl['costo'])} ({_pct(pl['pct_costo'])})")
            partes.append(f"  Contribución Marginal: {_fmt(pl['contribucion'])} ({_pct(pl['pct_contrib'])})")
            partes.append(f"  Nóminas:               {_fmt(pl['nominas'])}")
            partes.append(f"  Logística:             {_fmt(pl['logistica'])}")
            partes.append(f"  Gastos de Venta:       {_fmt(pl['gtos_venta'])}")
            partes.append(f"  Gastos Administrativos:{_fmt(pl['gtos_admin'])}")
            partes.append(f"  EBITDA:                {_fmt(pl['ebitda'])} ({_pct(pl['pct_ebitda'])})")
            partes.append(f"  Producto Financiero:   {_fmt(pl['financieros'])}")
            partes.append(f"  Impuestos:             {_fmt(pl['impuestos'])}")
            partes.append(f"  Utilidad Neta:         {_fmt(pl['utilidad_neta'])} ({_pct(pl['pct_utilidad'])})")
            if pla and pla.get("ventas"):
                var_v = (pl["ventas"] - pla["ventas"]) / abs(pla["ventas"]) * 100
                denom = abs(pla["utilidad_neta"]) or 1
                var_u = (pl["utilidad_neta"] - pla["utilidad_neta"]) / denom * 100
                partes.append(f"  Var vs {año_ant}: Ventas {var_v:+.1f}%, Utilidad {var_u:+.1f}%")
        except Exception:
            pass

    # ── P&L acumulado ─────────────────────────────────────────────────────────
    try:
        ytd  = get_pl_ytd(data, año,     meses_sel)
        ytda = get_pl_ytd(data, año_ant, meses_sel)
        if ytd:
            partes.append(f"\n=== P&L ACUMULADO ({', '.join(nombres)}) ===")
            partes.append(f"  Ventas YTD:               {_fmt(ytd['ventas'])}")
            partes.append(f"  Contribución Marginal YTD: {_fmt(ytd['contribucion'])} ({_pct(ytd['pct_contrib'])})")
            partes.append(f"  EBITDA YTD:               {_fmt(ytd['ebitda'])} ({_pct(ytd['pct_ebitda'])})")
            partes.append(f"  Utilidad Neta YTD:        {_fmt(ytd['utilidad_neta'])} ({_pct(ytd['pct_utilidad'])})")
            if ytda and ytda.get("ventas"):
                var = (ytd["ventas"] - ytda["ventas"]) / abs(ytda["ventas"]) * 100
                partes.append(f"  Var Ventas YTD vs {año_ant}: {var:+.1f}%")
    except Exception:
        pass

    # ── Balance general (último mes seleccionado) ─────────────────────────────
    if meses_sel:
        ultimo_mes = max(meses_sel)
        try:
            bg = get_balance_general(data, año, ultimo_mes)
            partes.append(f"\n=== BALANCE GENERAL (cierre {MESES[ultimo_mes]} {año}) ===")
            partes.append(f"  Total Activos:      {_fmt(bg['total_activos'])}")
            partes.append(f"  Total Pasivos:      {_fmt(bg['total_pasivos'])}")
            partes.append(f"  Capital Social:     {_fmt(bg['capital_social'])}")
            partes.append(f"  Utilidad Ejercicio: {_fmt(bg['utilidad_ejercicio'])}")
            partes.append(f"  Capital Contable:   {_fmt(bg['capital_contable'])}")
        except Exception:
            pass

    # ── Flujo de efectivo mensual ─────────────────────────────────────────────
    partes.append("\n=== FLUJO DE EFECTIVO ===")
    for mes in meses_sel:
        try:
            fe = get_flujo_mes(data, año, mes)
            partes.append(f"\n{MESES[mes]} {año}:")
            partes.append(f"  Saldo Inicial:         {_fmt(fe['saldo_ini'])}")
            partes.append(f"  Flujo Neto Operación:  {_fmt(fe['fno'])}")
            partes.append(f"  Inversión Neta:        {_fmt(fe['inv_neta'])}")
            partes.append(f"  Flujo del Periodo:     {_fmt(fe['f_periodo'])}")
            partes.append(f"  Saldo Final:           {_fmt(fe['saldo_fin'])}")
        except Exception:
            pass

    return "\n".join(partes)


def get_ai_response(question, financial_context, chat_history):
    """Llama a Claude Haiku y devuelve (respuesta_str, status_str).

    status puede ser: 'ok', 'no_key', 'auth_error', 'error: <msg>'
    """
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        api_key = ""

    if not api_key:
        return None, "no_key"

    try:
        client = anthropic.Anthropic(api_key=api_key)
        system = _SYSTEM_PROMPT + f"\n\n=== DATOS FINANCIEROS ===\n{financial_context}"

        # Historial limitado (máx 10 mensajes) + pregunta actual
        mensajes = []
        for m in chat_history[-10:]:
            mensajes.append({"role": m["role"], "content": m["content"]})
        mensajes.append({"role": "user", "content": question})

        resp = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=system,
            messages=mensajes,
        )
        return resp.content[0].text, "ok"

    except anthropic.AuthenticationError:
        return None, "auth_error"
    except Exception as e:
        return None, f"error: {e}"
