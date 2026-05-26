import os
import re
import streamlit as st
import anthropic

from utils.data import MESES

MAX_PREGUNTAS = 20

# ── Esquema de BD + reglas financieras (inyectado en el prompt de SQL) ────────
SCHEMA_CONTEXT = """
ESQUEMA DE BASE DE DATOS:

Tabla catalogo_cuentas:
- n5_cuenta (PK, varchar) — código de cuenta más granular, ej: "110-001"
- n1_nombre (varchar) — categoría principal: "Ingresos", "Costo de Ventas", "Gastos",
  "Activos", "Pasivos", "Capital Contable", "Financieros", "Otros Ingresos y Egresos"
- n2_cuenta, n2_nombre — subcategoría. Claves: 100-000=Circulante, 180-000=Fijo,
  190-000=Diferido (Activos); 200-000=Circulante (Pasivos); 300-000=Contable (Capital)
- n3_cuenta, n3_nombre — grupo. Claves: 110-000=Efectivo, 120-000=CxC,
  160-000=Inventarios, 210-000=Proveedores, 310-100=Capital Social,
  320-000=Resultados Acumulados
- n4_cuenta, n4_nombre — subgrupo. Gastos se dividen en: Nóminas, Logística,
  Gastos de Venta, Gastos Administrativos.
  Depreciaciones: 183-200,183-300,184-300,185-300,186-300
  Amortizaciones: 192-200,192-210
- tipo_cuenta (varchar) — "Balance", "Resultados" o "Otros"

Tabla movimientos:
- año (int), mes (int)
- n5_cuenta (FK a catalogo_cuentas)
- saldo_movimientos_mes (numeric) — movimientos del mes (P&L usa esta columna)
- saldo_final_mes (numeric) — saldo al cierre del mes (Balance usa esta columna)

JOIN: movimientos m JOIN catalogo_cuentas c ON m.n5_cuenta = c.n5_cuenta

REGLAS FINANCIERAS CRÍTICAS (SIEMPRE APLICAR):
- Ingresos (n1_nombre='Ingresos'): el saldo viene NEGATIVO en la BD.
  Para mostrar ventas como positivo usar: -SUM(saldo_movimientos_mes)
- Costo de Ventas: saldo positivo, usar SUM(saldo_movimientos_mes) directamente
- Gastos: saldo positivo, usar SUM(saldo_movimientos_mes) directamente
- Contribución Marginal = -SUM(Ingresos) - SUM(Costo de Ventas)
- EBITDA = Contribución Marginal - SUM(Gastos donde n1_nombre='Gastos')
- Utilidad Neta = EBITDA - Financieros - Otros Ingresos y Egresos
- Balance — Activos: +SUM(saldo_final_mes) donde n1_nombre='Activos'
- Balance — Pasivos: -SUM(saldo_final_mes) donde n1_nombre='Pasivos'
- Balance — Capital: -SUM(saldo_final_mes) donde n1_nombre='Capital Contable'

EJEMPLOS DE QUERIES:

-- Ventas netas de un mes
SELECT -SUM(m.saldo_movimientos_mes) AS ventas_netas
FROM movimientos m JOIN catalogo_cuentas c ON m.n5_cuenta = c.n5_cuenta
WHERE c.n1_nombre = 'Ingresos' AND m.año = 2025 AND m.mes = 3;

-- EBITDA mensual acumulado
SELECT m.mes,
  -SUM(CASE WHEN c.n1_nombre = 'Ingresos' THEN m.saldo_movimientos_mes ELSE 0 END)
  - SUM(CASE WHEN c.n1_nombre = 'Costo de Ventas' THEN m.saldo_movimientos_mes ELSE 0 END)
  - SUM(CASE WHEN c.n1_nombre = 'Gastos' THEN m.saldo_movimientos_mes ELSE 0 END) AS ebitda
FROM movimientos m JOIN catalogo_cuentas c ON m.n5_cuenta = c.n5_cuenta
WHERE m.año = 2025
GROUP BY m.mes ORDER BY m.mes;

-- Desglose de gastos por categoría
SELECT c.n4_nombre, SUM(m.saldo_movimientos_mes) AS total
FROM movimientos m JOIN catalogo_cuentas c ON m.n5_cuenta = c.n5_cuenta
WHERE c.n1_nombre = 'Gastos' AND m.año = 2025
GROUP BY c.n4_nombre ORDER BY total DESC;

-- Balance general al cierre de un mes
SELECT c.n1_nombre, c.n3_nombre,
  CASE WHEN c.n1_nombre = 'Activos' THEN SUM(m.saldo_final_mes)
       ELSE -SUM(m.saldo_final_mes) END AS saldo
FROM movimientos m JOIN catalogo_cuentas c ON m.n5_cuenta = c.n5_cuenta
WHERE c.tipo_cuenta = 'Balance' AND m.año = 2025 AND m.mes = 1
GROUP BY c.n1_nombre, c.n3_nombre;

-- Comparativo de ventas por mes: año actual vs año anterior
SELECT m.mes,
  -SUM(CASE WHEN m.año = 2025 THEN m.saldo_movimientos_mes ELSE 0 END) AS ventas_2025,
  -SUM(CASE WHEN m.año = 2024 THEN m.saldo_movimientos_mes ELSE 0 END) AS ventas_2024,
  ROUND(
    (-SUM(CASE WHEN m.año = 2025 THEN m.saldo_movimientos_mes ELSE 0 END)
     - (-SUM(CASE WHEN m.año = 2024 THEN m.saldo_movimientos_mes ELSE 0 END)))
    / NULLIF(-SUM(CASE WHEN m.año = 2024 THEN m.saldo_movimientos_mes ELSE 0 END), 0) * 100
  , 1) AS var_pct
FROM movimientos m JOIN catalogo_cuentas c ON m.n5_cuenta = c.n5_cuenta
WHERE c.n1_nombre = 'Ingresos' AND m.mes IN (1, 2, 3)
GROUP BY m.mes ORDER BY m.mes;

-- Comparativo de EBITDA acumulado: año actual vs año anterior
SELECT
  -SUM(CASE WHEN m.año = 2025 AND c.n1_nombre = 'Ingresos' THEN m.saldo_movimientos_mes ELSE 0 END)
  - SUM(CASE WHEN m.año = 2025 AND c.n1_nombre = 'Costo de Ventas' THEN m.saldo_movimientos_mes ELSE 0 END)
  - SUM(CASE WHEN m.año = 2025 AND c.n1_nombre = 'Gastos' THEN m.saldo_movimientos_mes ELSE 0 END) AS ebitda_actual,
  -SUM(CASE WHEN m.año = 2024 AND c.n1_nombre = 'Ingresos' THEN m.saldo_movimientos_mes ELSE 0 END)
  - SUM(CASE WHEN m.año = 2024 AND c.n1_nombre = 'Costo de Ventas' THEN m.saldo_movimientos_mes ELSE 0 END)
  - SUM(CASE WHEN m.año = 2024 AND c.n1_nombre = 'Gastos' THEN m.saldo_movimientos_mes ELSE 0 END) AS ebitda_anterior
FROM movimientos m JOIN catalogo_cuentas c ON m.n5_cuenta = c.n5_cuenta
WHERE m.mes IN (1, 2, 3);
"""

_SQL_SYSTEM = (
    "Eres un experto en SQL y finanzas. "
    "Genera ÚNICAMENTE una query SQL SELECT válida para PostgreSQL. "
    "No incluyas explicaciones, bloques markdown ni backticks — solo el SQL puro. "
    "Si la pregunta no se puede responder con los datos disponibles, "
    "responde exactamente: NO_SQL"
)

_INTERPRET_SYSTEM = (
    "Eres un analista financiero experto. Interpreta los resultados de la consulta SQL "
    "y responde en español de forma clara y concisa. "
    "Usa formato con separador de miles para montos (ej: 1,234,567 MXN). "
    "NUNCA uses el símbolo $ — el sistema lo interpreta como fórmula matemática. "
    "Máximo 150 palabras. No uses encabezados (#, ##), emojis, ni tablas markdown. "
    "No uses negritas ni cursivas. Ve directo al dato."
)

_FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "truncate",
    "create", "grant", "revoke", "execute", "exec", "copy",
}


# ── Helpers de conexión ───────────────────────────────────────────────────────
def _get_api_key():
    try:
        return st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        return os.environ.get("ANTHROPIC_API_KEY", "")


def _get_db_url():
    url = os.environ.get("DATABASE_URL")
    if not url:
        try:
            url = st.secrets.get("DATABASE_URL", "")
        except Exception:
            pass
    return url or ""


# ── Pipeline: Generar SQL ─────────────────────────────────────────────────────
def generate_sql(question, año, meses_sel):
    """Llamada 1 al LLM: genera una query SQL SELECT para responder la pregunta.
    Retorna el SQL como string, o 'NO_SQL' si la pregunta no aplica.
    Lanza RuntimeError('no_key') si la API key no está configurada."""
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("no_key")

    meses_str = ", ".join(str(m) for m in meses_sel)
    user_msg = (
        f"El usuario está viendo: año actual={año}, año anterior={año - 1}, meses=[{meses_str}]\n\n"
        f"Pregunta: {question}"
    )

    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        system=_SQL_SYSTEM + "\n\n" + SCHEMA_CONTEXT,
        messages=[{"role": "user", "content": user_msg}],
    )
    sql = resp.content[0].text.strip()

    # Limpiar bloques markdown si el modelo los incluye
    if "```" in sql:
        sql = "\n".join(
            line for line in sql.split("\n")
            if not line.strip().startswith("```")
        ).strip()

    return sql


# ── Pipeline: Ejecutar SQL ────────────────────────────────────────────────────
def execute_safe_query(sql_query):
    """Valida que sea SELECT y ejecuta contra PostgreSQL con timeout de 5s.
    Retorna (rows, columns, error_msg). Si hay error, rows y columns son None."""
    import psycopg2

    sql_clean = sql_query.strip()

    # Debe empezar con SELECT
    first_word = sql_clean.split()[0].upper() if sql_clean else ""
    if first_word != "SELECT":
        return None, None, "La query generada no es un SELECT."

    # Rechazar múltiples sentencias (salvo punto y coma final)
    if ";" in sql_clean.rstrip(";"):
        return None, None, "No se permiten múltiples sentencias SQL."

    # Rechazar keywords de escritura/DDL
    normalized = sql_clean.lower()
    for kw in _FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", normalized):
            return None, None, f"Keyword no permitido: '{kw}'."

    db_url = _get_db_url()
    if not db_url:
        return None, None, "DATABASE_URL no configurada."

    try:
        conn = psycopg2.connect(db_url)
        try:
            cur = conn.cursor()
            cur.execute("SET statement_timeout = 5000")  # 5 segundos
            cur.execute(sql_query)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []
        finally:
            conn.close()
        return rows, columns, None
    except Exception as e:
        return None, None, str(e)


# ── Pipeline: Interpretar resultados ─────────────────────────────────────────
def interpret_results(question, sql_query, columns, rows):
    """Llamada 2 al LLM: interpreta los resultados SQL en lenguaje natural."""
    api_key = _get_api_key()
    if not api_key:
        return "El asistente AI no está configurado."

    if not rows:
        results_text = "La consulta no devolvió resultados."
    else:
        header = " | ".join(str(c) for c in columns)
        data_rows = "\n".join(
            " | ".join(str(v) for v in row) for row in rows[:50]
        )
        results_text = f"{header}\n{'-' * len(header)}\n{data_rows}"
        if len(rows) > 50:
            results_text += f"\n... ({len(rows)} filas totales, mostrando 50)"

    user_msg = (
        f"Pregunta: {question}\n\n"
        f"Resultados:\n{results_text}"
    )

    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=600,
        system=_INTERPRET_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )
    return resp.content[0].text.strip()


# ── Función pública principal ─────────────────────────────────────────────────
def get_ai_response(question, año, meses_sel, chat_history):
    """Pipeline de 2 llamadas: genera SQL → ejecuta → interpreta.
    Retorna (texto, status) — misma interfaz de retorno que antes."""
    try:
        # Paso 1: generar SQL
        sql = generate_sql(question, año, meses_sel)
        print(f"[AI] SQL generado: {sql[:150]}")

        if sql.strip().upper() == "NO_SQL":
            return "No puedo responder esa pregunta con los datos financieros disponibles.", "ok"

        # Paso 2: ejecutar
        rows, columns, error = execute_safe_query(sql)
        if error:
            print(f"[AI] Error en query: {error}")
            return "Hubo un error al consultar los datos. Intenta reformular tu pregunta.", "ok"

        # Paso 3: interpretar
        respuesta = interpret_results(question, sql, columns, rows)
        return respuesta, "ok"

    except RuntimeError as e:
        if "no_key" in str(e):
            return None, "no_key"
        return None, f"error: {e}"
    except anthropic.AuthenticationError:
        return None, "auth_error"
    except Exception as e:
        return None, f"error: {e}"


# ── Legacy — approach anterior con contexto de texto ─────────────────────────
# Conservado para revertir si es necesario.
# Para activar: reemplazar get_ai_response por _legacy_get_ai_response en ai_dialog.py
# y restaurar build_financial_context en _init_chat_state.

from utils.data import get_pl_month, get_pl_ytd, get_balance_general, get_flujo_mes  # noqa: E402


def _legacy_fmt(val):
    if not val:
        return "$0"
    return f"${val:,.0f}"


def _legacy_pct(val):
    return f"{val:.1f}%"


_LEGACY_SYSTEM_PROMPT = (
    "Eres un analista financiero experto de Grupo Cinko Consultores. "
    "Respondes preguntas sobre los datos financieros de la empresa en español, "
    "de forma clara y concisa.\n\n"
    "Definiciones clave:\n"
    "- Contribución Marginal = Ventas - Costo de Ventas\n"
    "- EBITDA = Contribución Marginal - Gastos Operativos "
    "(Nóminas + Logística + Gastos de Venta + Gastos Administrativos)\n"
    "- Utilidad Neta = EBITDA - Producto Financiero - Impuestos\n\n"
    "Reglas de contenido:\n"
    "- Formatea montos con separador de miles SIN signo de pesos (ej: 1,234,567 MXN). "
    "NUNCA uses el símbolo $ — el sistema lo interpreta como fórmula matemática.\n"
    "- Máximo 120 palabras por respuesta.\n\n"
    "Reglas de formato:\n"
    "- No uses encabezados, emojis, tablas markdown, negritas ni cursivas."
)


def _legacy_build_financial_context(data, año, meses_sel):
    """Genera resumen de texto con los datos financieros del periodo seleccionado."""
    año_ant = año - 1
    partes  = []
    nombres = [MESES[m] for m in meses_sel]
    partes.append(f"Periodo: {año} | Meses: {', '.join(nombres)}\n")

    partes.append("=== ESTADO DE RESULTADOS MENSUAL ===")
    for mes in meses_sel:
        try:
            pl  = get_pl_month(data, año,     mes)
            pla = get_pl_month(data, año_ant, mes)
            nm  = MESES[mes]
            partes.append(f"\n{nm} {año}:")
            partes.append(f"  Ventas:                {_legacy_fmt(pl['ventas'])}")
            partes.append(f"  Contribución Marginal: {_legacy_fmt(pl['contribucion'])} ({_legacy_pct(pl['pct_contrib'])})")
            partes.append(f"  EBITDA:                {_legacy_fmt(pl['ebitda'])} ({_legacy_pct(pl['pct_ebitda'])})")
            partes.append(f"  Utilidad Neta:         {_legacy_fmt(pl['utilidad_neta'])} ({_legacy_pct(pl['pct_utilidad'])})")
            if pla and pla.get("ventas"):
                var_v = (pl["ventas"] - pla["ventas"]) / abs(pla["ventas"]) * 100
                partes.append(f"  Var vs {año_ant}: Ventas {var_v:+.1f}%")
        except Exception as e:
            print(f"[AI-legacy] Error mes {mes}: {e}")

    try:
        ytd = get_pl_ytd(data, año, meses_sel)
        if ytd:
            partes.append(f"\n=== P&L ACUMULADO ===")
            partes.append(f"  Ventas YTD:      {_legacy_fmt(ytd['ventas'])}")
            partes.append(f"  EBITDA YTD:      {_legacy_fmt(ytd['ebitda'])} ({_legacy_pct(ytd['pct_ebitda'])})")
            partes.append(f"  Utilidad Neta:   {_legacy_fmt(ytd['utilidad_neta'])}")
    except Exception:
        pass

    if meses_sel:
        try:
            bg = get_balance_general(data, año, max(meses_sel))
            partes.append(f"\n=== BALANCE GENERAL ===")
            partes.append(f"  Total Activos:    {_legacy_fmt(bg['total_activos'])}")
            partes.append(f"  Total Pasivos:    {_legacy_fmt(bg['total_pasivos'])}")
            partes.append(f"  Capital Contable: {_legacy_fmt(bg['capital_contable'])}")
        except Exception:
            pass

    partes.append("\n=== FLUJO DE EFECTIVO ===")
    for mes in meses_sel:
        try:
            fe = get_flujo_mes(data, año, mes)
            partes.append(f"\n{MESES[mes]} {año}: FNO={_legacy_fmt(fe['fno'])} | Flujo={_legacy_fmt(fe['f_periodo'])}")
        except Exception:
            pass

    return "\n".join(partes)


def _legacy_get_ai_response(question, financial_context, chat_history):
    """Approach anterior: manda todo el contexto como texto al LLM."""
    api_key = _get_api_key()
    if not api_key:
        return None, "no_key"
    try:
        client = anthropic.Anthropic(api_key=api_key)
        system = _LEGACY_SYSTEM_PROMPT + f"\n\n=== DATOS FINANCIEROS ===\n{financial_context}"
        mensajes = [{"role": m["role"], "content": m["content"]} for m in chat_history[-10:]]
        mensajes.append({"role": "user", "content": question})
        resp = client.messages.create(
            model="claude-haiku-4-5", max_tokens=1024,
            system=system, messages=mensajes,
        )
        return resp.content[0].text, "ok"
    except anthropic.AuthenticationError:
        return None, "auth_error"
    except Exception as e:
        return None, f"error: {e}"
