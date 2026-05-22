import streamlit as st
from utils.data import MESES
from utils.ai_chat import build_financial_context, get_ai_response, MAX_PREGUNTAS


def _init_chat():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "chat_preguntas" not in st.session_state:
        st.session_state.chat_preguntas = 0
    if "chat_context_key" not in st.session_state:
        st.session_state.chat_context_key = ""
    if "chat_context" not in st.session_state:
        st.session_state.chat_context = ""


def get_año(años_disponibles):
    return st.session_state.get("año_sel", años_disponibles[0])


def get_meses_nombres(nombres_disp):
    guardados = st.session_state.get("meses_nombres_sel", nombres_disp)
    validos   = [n for n in guardados if n in nombres_disp]
    return validos if validos else nombres_disp


def render_panel_filtros(data, años_disponibles):
    st.markdown("""
    <div class="filtros-header">
        <div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:1px;
                    opacity:0.7; margin-bottom:4px;">Grupo Cinko Consultores</div>
        <div style="font-size:1rem; font-weight:700;">Panel de Filtros</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("##### 📊 Periodo")

    año_actual = get_año(años_disponibles)
    año_idx    = años_disponibles.index(año_actual) if año_actual in años_disponibles else 0
    año        = st.selectbox("Año", años_disponibles, index=año_idx, key="año_sel")

    meses_disponibles = sorted(data[data["Año"] == año]["Mes"].unique())
    nombres_disp      = [MESES[m] for m in meses_disponibles]

    # Resetear meses si cambió el año
    if st.session_state.get("_prev_año") != año:
        st.session_state["meses_nombres_sel"] = nombres_disp
        st.session_state["_prev_año"]         = año

    meses_sel_nombres = st.multiselect(
        "Meses", nombres_disp,
        default=get_meses_nombres(nombres_disp),
        key="meses_nombres_sel",
    )

    st.divider()
    st.markdown("##### 🤖 Asistente AI")

    # Limpiar historial si cambió el usuario en sesión
    current_user = st.session_state.get("username", "")
    if st.session_state.get("_chat_user") != current_user:
        for key in ("chat_history", "chat_preguntas", "chat_context_key", "chat_context"):
            st.session_state.pop(key, None)
        st.session_state["_chat_user"] = current_user

    _init_chat()

    # Resolver meses numéricos para el contexto
    meses_disponibles_num = sorted(data[data["Año"] == año]["Mes"].unique())
    nombre_a_num = {MESES[m]: m for m in meses_disponibles_num}
    meses_num    = sorted([nombre_a_num[n] for n in meses_sel_nombres if n in nombre_a_num])
    if not meses_num:
        meses_num = meses_disponibles_num  # fallback: todos los meses disponibles

    # Regenerar contexto si cambian los filtros
    ctx_key = f"{año}_" + "_".join(str(m) for m in meses_num)
    if ctx_key != st.session_state.chat_context_key:
        ctx = build_financial_context(data, año, meses_num)
        print(f"[AI] Contexto generado: año={año}, meses={meses_num}, len={len(ctx)}")
        st.session_state.chat_context_key = ctx_key
        st.session_state.chat_context     = ctx

    # Contenedor de chat con altura dinámica (llena el viewport disponible)
    st.markdown(
        "<style>"
        "div[data-testid='stHorizontalBlock']:has(.filtros-header) "
        "div[data-testid='stVerticalBlockBorderWrapper']>div{"
        "height:calc(100vh - 415px)!important;"
        "min-height:180px!important;"
        "}"
        "</style>",
        unsafe_allow_html=True,
    )
    chat_container = st.container(height=600, border=False)
    with chat_container:
        for msg in st.session_state.chat_history[-6:]:
            with st.chat_message(msg["role"]):
                # Escapar $ para evitar que Streamlit lo interprete como LaTeX
                st.markdown(msg["content"].replace("$", r"\$"))

    # Contador de consultas
    st.caption(f"Consultas: {st.session_state.chat_preguntas}/{MAX_PREGUNTAS}")

    # Input de chat
    restantes = MAX_PREGUNTAS - st.session_state.chat_preguntas
    if restantes > 0:
        pregunta = st.chat_input("¿Cuál fue el EBITDA de marzo?", key="chat_input")
    else:
        st.info("Has alcanzado el límite de consultas para esta sesión.")
        pregunta = None

    if pregunta:
        st.session_state.chat_history.append({"role": "user", "content": pregunta})
        st.session_state.chat_preguntas += 1

        with chat_container:
            with st.chat_message("user"):
                st.markdown(pregunta)

        respuesta, status = get_ai_response(
            pregunta,
            st.session_state.chat_context,
            st.session_state.chat_history[:-1],
        )

        if status == "ok":
            content = respuesta
        elif status == "no_key":
            content = "El asistente AI aún no está configurado. Contacta al administrador para activarlo."
        elif status == "auth_error":
            content = "Error de autenticación con el servicio AI. Verifica la configuración."
        else:
            content = "No se pudo obtener respuesta en este momento. Intenta de nuevo."

        st.session_state.chat_history.append({"role": "assistant", "content": content})

        with chat_container:
            with st.chat_message("assistant"):
                st.markdown(content.replace("$", r"\$"))

    st.divider()
    st.caption("Última actualización: 31/12/2025")
    st.caption("Powered by Grupo Cinko Consultores")

    return año, meses_sel_nombres
