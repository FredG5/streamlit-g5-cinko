import streamlit as st

from utils.ai_chat import build_financial_context, get_ai_response, MAX_PREGUNTAS
from utils.data import MESES

_FLOAT_CSS = (
    "<style>"
    "div[data-testid='stMarkdownContainer']:has(#ai-float-anchor)"
    "+div[data-testid='stButton']{position:fixed;bottom:28px;right:28px;z-index:9999;}"
    "div[data-testid='stMarkdownContainer']:has(#ai-float-anchor)"
    "+div[data-testid='stButton'] button{"
    "border-radius:50%;width:60px;height:60px;padding:0;font-size:1.6rem;"
    "background:linear-gradient(135deg,#1a1a2e 0%,#2d3561 100%);"
    "color:white;border:none;box-shadow:0 4px 24px rgba(0,0,0,.5);"
    "transition:transform .15s,box-shadow .15s;}"
    "div[data-testid='stMarkdownContainer']:has(#ai-float-anchor)"
    "+div[data-testid='stButton'] button:hover{"
    "transform:scale(1.1);box-shadow:0 6px 30px rgba(0,0,0,.6);}"
    "</style>"
)


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
def _ai_dialog(data, año, meses_sel):
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

    # Input via form para que funcione dentro del dialog
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


def render_ai_button(data, año, meses_sel):
    """Botón flotante en esquina inferior derecha que abre el dialog de AI."""
    st.markdown(_FLOAT_CSS + '<span id="ai-float-anchor"></span>', unsafe_allow_html=True)
    if st.button("🤖", key="ai_float_btn"):
        _ai_dialog(data, año, meses_sel)
