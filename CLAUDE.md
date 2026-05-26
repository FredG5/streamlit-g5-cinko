# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Contexto del proyecto

Demo comercial del producto **"Diagnóstico de Inteligencia de Datos"** de Grupo Cinko Consultores ([www.gcinko.com](https://www.gcinko.com)). Su propósito es mostrarse a prospectos como muestra del producto. Todo el texto de UI, etiquetas, mensajes y comentarios debe estar en **español**.

## Comandos

```bash
# Instalar dependencias
pip install -r requirements.txt

# Correr la app (abre en http://localhost:8501)
streamlit run app.py
```

No hay pasos de build, lint ni tests configurados.

## Estructura del proyecto

```
Streamlit G5/
├── app.py                        # Entrada: page config, CSS, autenticación, orquestación de layout
├── utils/
│   ├── data.py                   # Carga de datos, MESES, funciones de cálculo financiero
│   ├── ui.py                     # CSS global, fmt(), render_kpi(), delta_pct()
│   └── ai_chat.py                # build_financial_context(), get_ai_response(), _SYSTEM_PROMPT
├── views/
│   ├── filtros.py                # Panel de filtros lateral + helpers de session state
│   ├── estado_resultados.py      # render_shared_header(), render_estado_resultados()
│   ├── ai_dialog.py              # open_ai_dialog() (@st.dialog), _chat_ui() (@st.fragment)
│   ├── flujo_efectivo.py         # render_flujo_efectivo()
│   ├── balance_general.py        # render_balance_general()
│   └── balance_analitico.py      # render_balance_analitico()
├── assets/
│   └── logo_cinko.jpg            # Logo embebido como base64 en el header
├── data/
│   ├── Tabla_Financieros_G5.xlsx # Datos financieros mensuales por cuenta (fuente original, aún usado en modo excel)
│   └── CatCuentas_G5.xlsx        # Catálogo jerárquico de cuentas
├── database/
│   ├── schema.sql                # DDL PostgreSQL: catalogo_cuentas + movimientos
│   ├── migrate.py                # Script de migración Excel → PostgreSQL (idempotente, UPSERT)
│   └── README.md                 # Instrucciones para Neon, esquema, migración y activación
├── credentials.yaml              # Usuarios y hashes para streamlit_authenticator
├── .streamlit/
│   └── secrets.toml              # ANTHROPIC_API_KEY + DATABASE_URL (gitignored, no commitear)
├── requirements.txt
└── CLAUDE.md
```

**Para agregar una nueva vista**: crear `views/nueva_vista.py` con una función `render_*`, importarla en `app.py` y añadirla al `st.tabs()`.

## Arquitectura

### Layout

Panel de filtros personalizado con `st.columns([1, 4], gap="large")` — no usa el sidebar nativo de Streamlit. `st.session_state.sidebar_open` controla visibilidad. La app usa **una sola rama de layout**: cuando el panel está cerrado, CSS oculta la columna de filtros (`display:none`) y expande la de contenido (`flex:1`) sin reconstruir el DOM.

`render_shared_header(data, año, meses_sel, authenticator=None)` renderiza el logo, menú de sesión, y los botones **Filtros** y **AI** en la misma fila (`st.columns([1.8, 1.8, 8.4], vertical_alignment="center")`). El botón AI abre `open_ai_dialog()` via `@st.dialog`.

### Tabs (orden actual)

1. 📊 Estado de Resultados
2. 💧 Flujo de Efectivo
3. 📋 Balance General
4. 📐 Balance Analítico

### Datos (`utils/data.py`)

`DATA_SOURCE = "postgres"` controla la fuente activa. Cambiar a `"excel"` para usar los archivos locales sin necesidad de base de datos.

| Función | Descripción |
|---|---|
| `load_data()` | Dispatcher: llama a `_excel_load_data()` o `_pg_load_data()` según `DATA_SOURCE` |
| `_excel_load_data()` | Lee y mergea los Excel, caché permanente |
| `_pg_load_data()` | Query JOIN en PostgreSQL, devuelve DataFrame con los **mismos nombres de columna** que Excel; caché TTL=3600s |
| `get_pl_month(data, year, month)` | P&L de un mes usando `Saldo Movimientos del Mes OK` |
| `get_pl_ytd(data, year, months)` | Acumulado P&L de una lista de meses |
| `get_balance_general(data, year, snapshot_month)` | Snapshot de balance al cierre del mes; YTD calculado internamente |
| `get_flujo_mes(data, year, month)` | Flujo de efectivo de un mes — método indirecto |

**Gotcha PostgreSQL**: psycopg2 devuelve `decimal.Decimal` para columnas `NUMERIC`. `_pg_load_data()` convierte los tres campos de saldo a `float` con `.astype(float)` al crear el DataFrame — sin esto, la aritmética falla con `TypeError`.

**Columnas del DataFrame** (idénticas en ambos modos):
`Año`, `Mes`, `N5 Cuenta`, `Saldo Movimientos del Mes OK`, `Saldo Final de Mes OK`, `Saldo Inicial de Mes OK`, `N1 Nombre Cuenta`, `N2 Cuenta`, `N2 Nombre Cuenta`, `N3 Cuenta`, `N3 Nombre Cuenta`, `N4 Cuenta`, `N4 Nombre Cuenta`, `Resultaods/Balance`

### Convenciones de signo — P&L

Ingresos vienen **negativos** en el Excel → se multiplican por `-1`. Gastos con signo positivo original. `Saldo Movimientos del Mes OK` es la columna de movimientos mensuales para resultados.

### Convenciones de signo — Balance General

- Activos: `+SUM(Saldo Final de Mes OK)` donde N1="Activos"
- Pasivos: `-SUM(Saldo Final de Mes OK)` donde N1="Pasivos"
- Capital Social: `-SUM(N3="310-100")`
- `resultados_acum` mostrado = `Saldo Utilidad Neta` = `-SUM(Resultaods/Balance="Resultados") - utilidad_ytd + (-SUM(N3="320-000"))` — reconcilia saldo de cuentas de resultados con la utilidad del ejercicio
- Cuadre exacto: Total Activos = Total Pasivos + Capital Contable (verificado en todos los meses)

### Convenciones de signo — Flujo de Efectivo

Traducción del modelo DAX de Power BI. La columna `Flujo` de la tabla calculada PBI se define como:

```
Flujo = IF(N3 = "110-000", Movimiento del Mes, -Movimiento del Mes)
```

En Python: `fs(mask) = -df.loc[mask, "Saldo Movimientos del Mes OK"].sum()` para todas las cuentas excepto N3=`110-000` (efectivo, que usa signo directo para saldo inicial/final).

Resultado: aumento en activos → negativo (usa efectivo); aumento en pasivos → positivo (genera efectivo).

**Cascada del flujo (método indirecto):**

```
Utilidad Neta  (de get_pl_month)
+ Depreciaciones  (N4: 183-200,183-300,184-300,185-300,186-300)
+ Amortizaciones  (N4: 192-200,192-210)
- Gasto Financiero  (N4: 720-002 Comisiones Bancarias)
= EBITDA / Cargos que no requieren recursos

+ Var. CXC  (N3: 120-000,130-000) − Impuestos
+ Var. Inventarios  (N3: 160-000)
+ Var. CXP  (N3: 210-000,230-000,236-000,240-000,250-000,256-000)
+ Pago de Dividendos  (N3: 320-000)
= Capital de Trabajo Neto

= Flujo Neto de Operación

+ Inversión Activo Fijo  (N2: 180-000) − Depreciaciones
+ Diferido  (N2: 190-000) − Amortizaciones
= Inversión Neta

= Flujo Disponible para Impuestos
+ Impuestos  (+SUM mov N5: 140-102)  ← doble negativo se cancela
= Flujo Disponible para Servicio de Deuda
+ Gasto Financiero  (negativo, reduce el flujo)
= Flujo Disponible para Pago de Deuda
+ Financiamiento LP  (= 0, hardcoded)
= SOBRANTE / FALTANTE
+ Aportación de Capital  (= 0, hardcoded)
= FLUJO DEL PERIODO
```

**Verificación**: `Saldo Inicial (N3=110-000) + Flujo del Periodo = Saldo Final` cuadra exactamente en todos los meses.

**Nota sobre Impuestos**: `Impuestos Flujo = -CALCULATE([Valor del Mes], N5="140-102")` donde `Valor del Mes = -SUM(mov)`. El doble negativo resulta en `+SUM(mov para N5=140-102)`. En el total de la columna: `saldo_ini` = primer mes, `saldo_fin` = último mes (no se suman).

### Catálogo de cuentas

`CatCuentas_G5.xlsx`: columna `Resultaods/Balance` (typo intencional en el Excel) con valores `Balance`, `Resultados`, `Otros`.

Jerarquía: N1 (4 categorías) → N2 → N3 → N4 → N5.

Códigos N2 clave: 100-000=Circulante, 180-000=Fijo, 190-000=Diferido (Activos); 200-000=Circulante (Pasivos); 300-000=Contable (Capital).

Gastos en N4: Nóminas, Logística, Gastos de Venta, Gastos Administrativos.

### Vistas

**`estado_resultados.py`** — tabla mensual con columnas por mes seleccionado + Total. Usa `Saldo Movimientos del Mes OK`. KPIs con comparativo vs año anterior.

**`flujo_efectivo.py`** — tabla mensual método indirecto. Columna Total suma los flujos mensuales; `saldo_ini` y `saldo_fin` usan primer/último mes respectivamente. KPIs: Flujo Neto de Operación, Flujo del Periodo, Saldo Inicial, Saldo Final.

**`balance_general.py`** — columnas = meses seleccionados (hasta 12). Pivota N3 dentro de N2 con `groupby` + `droplevel()`. Usa `Saldo Final de Mes OK`. KPIs al cierre del último mes seleccionado.

**`balance_analitico.py`** — selectbox propio para elegir un mes específico. Layout `display:flex` con Activos a la izquierda y Pasivos+Capital a la derecha (`margin-top:auto` en Capital para alinear inferiores). Tabla de 6 columnas: Concepto | Monto | % | Monto Año Ant. | % | DIF%. KPIs y gráficas de dona al final. Usa `pd.Series.xs()` con `except (KeyError, TypeError)` para manejar años sin datos anteriores.

### CSS y UI

- Clase `fin-table`: tabla financiera base.
- Clase `bal-table`: sobrescribe a tamaño compacto (0.71rem, padding reducido) — usada en todas las tablas de detalle.
- `block-container { padding-top: 0.75rem !important }` reduce el espacio en blanco superior.
- `header[data-testid="stHeader"] { height: 0 !important }` elimina la barra de Streamlit.
- Números en tablas: siempre `fmt(val, prefix="")` — sin signo de pesos en celdas; el símbolo `($ MXN)` se pone en el encabezado de sección.

### Plotly

Cada `st.plotly_chart()` debe llevar un `key=` único para evitar `StreamlitDuplicateElementId`. Convención: `"<vista>_<nombre>_<tipo>"` (ej. `"bg_activos_pie"`, `"fe_flujo_bar"`).

### Gotcha: HTML en `st.markdown()`

CommonMark cierra bloques HTML en líneas en blanco. Todo el HTML de tablas debe construirse como **una sola cadena sin líneas en blanco ni comentarios HTML** antes de pasarlo a `st.markdown(..., unsafe_allow_html=True)`. El patrón correcto es concatenación de f-strings en una sola expresión.

### Autenticación

`streamlit_authenticator` con `credentials.yaml`. Habilitada con `AUTH_ENABLED = True` en `app.py`. El archivo `.streamlit/secrets.toml` tiene tres claves raíz (antes de cualquier `[sección]`):
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
DATABASE_URL = "postgresql://...?sslmode=require"

[credentials.usernames.admin]
...
```

### PostgreSQL / Neon

Base de datos en [neon.tech](https://neon.tech). Dos tablas: `catalogo_cuentas` (PK: `n5_cuenta`) y `movimientos` (UNIQUE: `año, mes, n5_cuenta`). Ver `database/README.md` para instrucciones completas.

Para actualizar datos cuando hay nuevos Excel: correr `python database/migrate.py` (UPSERT idempotente). La caché de postgres se refresca cada hora; para forzar refresco inmediato, reiniciar la app.

### Chat AI (`utils/ai_chat.py` + `views/ai_dialog.py`)

- `build_financial_context(data, año, meses_sel)` — genera un bloque de texto con P&L mensual, P&L YTD, Balance General y Flujo de Efectivo. Se recalcula cuando cambian los filtros.
- `get_ai_response(question, financial_context, chat_history)` — llama a `claude-haiku-4-5` via Anthropic SDK. Devuelve `(texto, status)` donde status es `"ok"`, `"no_key"`, `"auth_error"` o `"error: <msg>"`.
- `_SYSTEM_PROMPT` — prohíbe el símbolo `$` en respuestas (usar "MXN"), limita a 120 palabras, sin headers ni emojis ni tablas markdown.
- El diálogo usa `@st.fragment` + `st.rerun(scope="fragment")` para actualizar el historial sin cerrar el modal.
- Historial aislado por usuario: se limpia cuando cambia `st.session_state["username"]`.
- Respuestas muestran con `.replace("$", r"\$")` para evitar renderizado LaTeX en `st.markdown()`.

## Próximos pasos (roadmap)

1. ~~**Chat AI conversacional**~~ ✅ Implementado con Claude Haiku via Anthropic SDK
2. ~~**Migración a PostgreSQL**~~ ✅ Neon.tech + psycopg2, modo dual excel/postgres
3. ~~**Autenticación de usuarios**~~ ✅ Implementado con streamlit_authenticator
4. **Vista trimestral** — para presentaciones a consejos directivos
5. **Deploy en producción** — actualmente en Streamlit Cloud (github.com/FredG5/streamlit-g5-cinko)
