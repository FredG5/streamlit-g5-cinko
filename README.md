# Inteligencia Financiera · Grupo Cinko

Dashboard financiero interactivo para Grupo Cinko Consultores. Muestra Estado de Resultados, Flujo de Efectivo, Balance General y Balance Analítico con datos mensuales y comparativos anuales.

## Setup local

### 1. Clonar el repositorio

```bash
git clone https://github.com/<tu-usuario>/<nombre-repo>.git
cd <nombre-repo>
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar credenciales locales

Crea el archivo `.streamlit/secrets.toml` (está en `.gitignore` — nunca subir al repo):

```toml
[credentials.usernames.admin]
email = "admin@gcinko.com"
name = "Administrador"
password = "$2b$12$At4rW6/gT6TB0R0gAVBSm.yNXrS4RrfLTVsUtTWJu0dyhKW4CMcQ."

[credentials.usernames.demo]
email = "demo@gcinko.com"
name = "Prospecto Demo"
password = "$2b$12$6k75qy1moi730VoBKtDR4uGAzT.SUgS.FMbrSrZMLg.naJnPYVClS"

[cookie]
expiry_days = 7
key = "g5_cinko_secret_2026"
name = "g5_auth"
```

### 4. Ejecutar

```bash
streamlit run app.py
```

Abre en `http://localhost:8501`.

**Usuarios:** `admin` / `cinko2026` · `demo` / `demo2026`

## Vistas incluidas

| Vista | Descripción |
|---|---|
| 📊 Estado de Resultados | P&L mensual completo con KPIs y gráficos |
| 💧 Flujo de Efectivo | Método indirecto con cascada completa |
| 📋 Balance General | Snapshot mensual con variación horizontal |
| 📐 Balance Analítico | Vista detallada con comparativo año anterior |

## Estructura del proyecto

```
├── app.py                   # Entry point — layout, auth, orquestación
├── utils/
│   ├── data.py              # Carga de datos (Excel) y funciones de cálculo
│   └── ui.py                # CSS global y helpers de formato
├── views/                   # Una función render_* por vista
├── data/                    # Archivos Excel con datos financieros
├── assets/                  # Logo Cinko
├── credentials.yaml         # Credenciales para autenticación local
└── .streamlit/
    ├── config.toml          # Tema y configuración del servidor
    └── secrets.toml         # Solo para uso local (en .gitignore)
```

## Deploy en Streamlit Community Cloud

Ver instrucciones en [share.streamlit.io](https://share.streamlit.io). El contenido de `secrets.toml` se pega en la sección **Secrets** de la app en Streamlit Cloud.

---
*Grupo Cinko Consultores · 2026*
