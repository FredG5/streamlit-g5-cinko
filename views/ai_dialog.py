import streamlit as st

from utils.ai_chat import build_financial_context, get_ai_response, MAX_PREGUNTAS
from utils.data import MESES


def _init_chat_state(año, meses_sel, data):
    defaults = {
        "chat_history": [], "chat_preguntas": 0,
        "chat_context_key": "", "chat_context": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Aislar historial por usuario
    current_user = st.session_state.get("username", "")
    if st.session_state.get("_chat_user") != current_user:
        for k in defaults:
            st.session_state[k] = defaults[k]
        st.session_state["_chat_user"] = current_user

    # Regenerar contexto si cambian los filtros
    ctx_key = f"{año}_" + "_".join(str(m) for m in meses_sel)
    if ctx_key != st.session_state.chat_context_key:
        ctx = build_financial_context(data, año, meses_sel)
        print(f"[AI] Contexto: año={año}, meses={meses_sel}, len={len(ctx)}")
        st.session_state.chat_context_key = ctx_key
        st.session_state.chat_context = ctx


@st.dialog("Asistente IA — Grupo Cinko", width="large")
def open_ai_dialog(data, año, meses_sel):
    _init_chat_state(año, meses_sel, data)

    nombres = [MESES[m] for m in meses_sel if m in MESES]
    st.caption(f"Analizando {año} — {', '.join(nombres)}")

    # Historial
    chat_container = st.container(height=380, border=False)
    with chat_container:
        for msg in st.session_state.chat_history[-10:]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"].replace("$", r"\$"))

    st.caption(f"Consultas: {st.session_state.chat_preguntas}/{MAX_PREGUNTAS}")

    restantes = MAX_PREGUNTAS - st.session_state.chat_preguntas
    if restantes > 0:
        with st.form("ai_chat_form", clear_on_submit=True):
            col_inp, col_btn = st.columns([5, 1])
            with col_inp:
                pregunta = st.text_input(
                    "", placeholder="¿Cuál fue el EBITDA de marzo?",
                    label_visibility="collapsed",
                )
            with col_btn:
                submitted = st.form_submit_button("Enviar", use_container_width=True)
    else:
        st.info("Has alcanzado el límite de consultas para esta sesión.")
        submitted, pregunta = False, ""

    if submitted and pregunta.strip():
        st.session_state.chat_history.append({"role": "user", "content": pregunta})
        st.session_state.chat_preguntas += 1

        respuesta, status = get_ai_response(
            pregunta,
            st.session_state.chat_context,
            st.session_state.chat_history[:-1],
        )

        if status == "ok":
            content = respuesta
        elif status == "no_key":
            content = "El asistente AI no está configurado. Contacta al administrador."
        elif status == "auth_error":
            content = "Error de autenticación con el servicio AI."
        else:
            content = "No se pudo obtener respuesta. Intenta de nuevo."

        st.session_state.chat_history.append({"role": "assistant", "content": content})
        st.rerun()
