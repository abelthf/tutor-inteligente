# tutor.py — Tutor Inteligente con NLP
#
# Basado en el diseño pedagógico de: diapositiva_tutores_inteligentes.pdf
#
# Componentes implementados:
#   · Modelo del estudiante      — perfil con fortalezas y dificultades
#   · Arranque en frío           — diagnóstico inicial antes del chat
#   · Ingeniería de contexto     — preamble compuesto de 4 fuentes
#   · Retroalimentación pedagóg. — reconocer · localizar · guiar
#   · Memoria a largo plazo      — perfil JSON persistente en disco
#   · Contenido del curso        — PDF fragmentado para RAG (Cohere)

import json
import os

import cohere
import fitz  # PyMuPDF
import streamlit as st


# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO A · CARGA DE CONTENIDO
# Convierte un PDF en fragmentos para Retrieval-Augmented Generation (RAG).
# ══════════════════════════════════════════════════════════════════════════════

def pdf_a_documentos(pdf_bytes: bytes, nombre: str, chunk: int = 1000) -> list:
    """Fragmenta un PDF en documentos de tamaño `chunk` para ser usados por Cohere."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    fragmentos = []
    for n_pag in range(len(doc)):
        texto = doc.load_page(n_pag).get_text()
        parte = 1
        for i in range(0, len(texto), chunk):
            fragmentos.append({
                "title": f"{nombre} · p.{n_pag + 1}/{parte}",
                "snippet": texto[i: i + chunk],
            })
            parte += 1
    return fragmentos


# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO B · MODELO DEL ESTUDIANTE
# Representación del estado del aprendiz: conocimientos, avance y dificultades.
# Implementa memoria a largo plazo mediante persistencia en archivo JSON local.
# ══════════════════════════════════════════════════════════════════════════════

_PERFILES_PATH = os.path.join("data", "perfiles.json")


def cargar_perfil(nombre: str) -> dict:
    """Carga el perfil persistente del estudiante o crea uno inicial."""
    if os.path.exists(_PERFILES_PATH):
        with open(_PERFILES_PATH, encoding="utf-8") as f:
            perfiles = json.load(f)
        if nombre in perfiles:
            return perfiles[nombre]
    return {
        "nombre": nombre,
        "nivel": "por estimar",
        "fortalezas": [],
        "dificultades": [],
        "sesiones": 0,
        "diagnostico_completado": False,
        "notas_diagnostico": "",
    }


def guardar_perfil(perfil: dict) -> None:
    """Persiste el perfil del estudiante en disco (memoria a largo plazo)."""
    os.makedirs("data", exist_ok=True)
    perfiles: dict = {}
    if os.path.exists(_PERFILES_PATH):
        with open(_PERFILES_PATH, encoding="utf-8") as f:
            perfiles = json.load(f)
    perfiles[perfil["nombre"]] = perfil
    with open(_PERFILES_PATH, "w", encoding="utf-8") as f:
        json.dump(perfiles, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO C · INGENIERÍA DE CONTEXTO
# Construye el preámbulo del tutor combinando cuatro fuentes:
#   mensaje actual + historial reciente + perfil del estudiante + contenido
# ══════════════════════════════════════════════════════════════════════════════

def construir_preamble(perfil: dict, tema: str) -> str:
    fort = ", ".join(perfil["fortalezas"]) or "aún no identificadas"
    difi = ", ".join(perfil["dificultades"]) or "aún no identificadas"
    return f"""\
Eres un tutor inteligente especializado en: {tema}.

═══ PERFIL DEL ESTUDIANTE ═══
  Nombre       : {perfil['nombre']}
  Nivel        : {perfil['nivel']}
  Fortalezas   : {fort}
  Dificultades : {difi}
  Diagnóstico  : {perfil['notas_diagnostico'] or 'No disponible aún.'}

═══ ESTRATEGIA DE RETROALIMENTACIÓN PEDAGÓGICA (obligatoria) ═══
Aplica SIEMPRE esta secuencia al responder:
  1. RECONOCER → Identifica primero los elementos correctos en la respuesta.
  2. LOCALIZAR → Señala el error o la confusión sin revelar la solución completa.
  3. GUIAR     → Formula una pregunta o pista que active la reflexión del estudiante.

═══ REGLAS DEL TUTOR ═══
  · No respondas directamente lo que el estudiante puede razonar por sí mismo.
  · Adapta la complejidad al nivel estimado del estudiante.
  · Si detectas un error conceptual, nómbralo explícitamente y ofrece una analogía.
  · Usa preguntas socráticas: "¿Qué pasaría si…?", "¿Cómo lo explicarías con tus palabras?"
  · Si el estudiante lleva 2 o más intentos sin avanzar, ofrece una pista más concreta.
  · Cuando el estudiante demuestre comprensión, reconócelo y propón un desafío mayor.
  · Basa tus respuestas en el documento proporcionado; si algo está fuera del material, indícalo.
  · Mantén un tono amable, alentador y profesional.

═══ LÍMITES ÉTICOS ═══
  · No hagas el trabajo del estudiante en su lugar.
  · Usa el perfil solo para personalizar la tutoría, no para otros fines.
"""


# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO D · DIAGNÓSTICO INICIAL (problema de arranque en frío)
# Antes de la primera sesión se recopilan conocimientos previos del estudiante
# para construir un perfil inicial y adaptar la ruta de aprendizaje.
# ══════════════════════════════════════════════════════════════════════════════

PREGUNTAS_DIAG = [
    "¿Qué sabes sobre el tema que vamos a estudiar? "
    "(palabras clave, ideas previas, experiencias relacionadas…)",

    "¿Qué aspectos del tema encuentras más difíciles o confusos?",

    "¿Qué esperas lograr o mejorar en esta sesión de tutoría?",
]


# ══════════════════════════════════════════════════════════════════════════════
# INTERFAZ STREAMLIT
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Tutor Inteligente",
    page_icon="🎓",
    layout="wide",
)

# Detectar clave API almacenada en .streamlit/secrets.toml
_clave_en_secrets = (
    hasattr(st, "secrets")
    and "COHERE_API_KEY" in st.secrets
    and st.secrets["COHERE_API_KEY"] not in ("", "PEGA_AQUI_TU_CLAVE_API")
)

# ─── BARRA LATERAL ────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎓 Tutor Inteligente")
    st.caption("Procesamiento de Lenguaje Natural · Sesión 2")
    st.divider()

    # Clave API de Cohere
    if _clave_en_secrets:
        cohere_api_key = st.secrets["COHERE_API_KEY"]
    else:
        cohere_api_key = st.text_input("🔑 Cohere API Key", type="password")
        st.markdown("[Obtener clave gratuita →](https://dashboard.cohere.ai/api-keys)")

    st.divider()

    # Identificación del estudiante
    nombre_input = st.text_input("👤 Tu nombre", placeholder="Escribe tu nombre…")

    # Material del curso
    st.markdown("**📄 Material del curso**")
    pdf_subido = st.file_uploader("Sube un PDF", type="pdf")
    tema_input = st.text_input(
        "📚 Tema del curso",
        placeholder="Ej: Comprensión lectora, Álgebra lineal…",
    )

    st.divider()

    # Panel del modelo del estudiante (visible una vez completado el diagnóstico)
    perfil_actual = st.session_state.get("perfil", {})
    if perfil_actual.get("diagnostico_completado"):
        p = perfil_actual
        st.subheader("📊 Modelo del estudiante")
        col1, col2 = st.columns(2)
        col1.metric("Nivel", p["nivel"])
        col2.metric("Sesiones", p["sesiones"])

        if p["fortalezas"]:
            st.markdown("✅ **Fortalezas detectadas**")
            for item in p["fortalezas"]:
                st.markdown(f"  • {item}")

        if p["dificultades"]:
            st.markdown("⚠️ **Áreas de mejora**")
            for item in p["dificultades"]:
                st.markdown(f"  • {item}")

        # Actualización manual del perfil
        with st.expander("✏️ Actualizar perfil"):
            nueva_fort = st.text_input("Nueva fortaleza", key="nueva_fort")
            if st.button("+ Añadir fortaleza") and nueva_fort.strip():
                p["fortalezas"].append(nueva_fort.strip())
                guardar_perfil(p)
                st.rerun()

            nueva_difi = st.text_input("Nueva dificultad", key="nueva_difi")
            if st.button("+ Añadir dificultad") and nueva_difi.strip():
                p["dificultades"].append(nueva_difi.strip())
                guardar_perfil(p)
                st.rerun()

            opciones_nivel = ["por estimar", "principiante", "intermedio", "avanzado"]
            nivel_actual = p.get("nivel", "por estimar")
            idx = opciones_nivel.index(nivel_actual) if nivel_actual in opciones_nivel else 0
            nivel_nuevo = st.selectbox("Actualizar nivel", opciones_nivel, index=idx)
            if st.button("Guardar nivel") and nivel_nuevo != p["nivel"]:
                p["nivel"] = nivel_nuevo
                guardar_perfil(p)
                st.rerun()

        if st.button("🔄 Nueva sesión (reiniciar chat)"):
            st.session_state.pop("messages", None)
            st.rerun()


# ─── CONTENIDO PRINCIPAL ──────────────────────────────────────────────────────
st.title("🎓 Tutor Inteligente")
st.markdown(
    "_Sistema de tutoría inteligente basado en NLP · "
    "Diseño pedagógico inspirado en ITS (Intelligent Tutoring Systems)_"
)

# Validaciones previas
if not nombre_input:
    st.info("👋 Escribe tu nombre en la barra lateral para comenzar.")
    st.stop()

if not cohere_api_key:
    st.warning("🔑 Agrega tu Cohere API Key en la barra lateral para continuar.")
    st.stop()

tema = (
    tema_input.strip()
    or (pdf_subido.name.rsplit(".", 1)[0].replace("_", " ") if pdf_subido else "Tema no definido")
)
nombre = nombre_input.strip()

st.caption(f"Estudiante: **{nombre}** · Tema: **{tema}**")

# Procesar PDF (con caché por nombre de archivo para no recargarlo en cada rerun)
if pdf_subido:
    if st.session_state.get("_pdf_nombre") != pdf_subido.name:
        with st.spinner("Procesando material del curso…"):
            st.session_state["documentos"] = pdf_a_documentos(
                pdf_subido.read(), pdf_subido.name
            )
            st.session_state["_pdf_nombre"] = pdf_subido.name
    documentos = st.session_state["documentos"]
else:
    documentos = []
    if st.session_state.get("perfil", {}).get("diagnostico_completado"):
        st.info(
            "💡 **Tip:** Sube un PDF en la barra lateral para que el tutor pueda "
            "referenciar el material del curso en sus respuestas."
        )

# Cargar perfil del estudiante (detectar cambio de nombre → reinicio de estado)
if st.session_state.get("_nombre_actual") != nombre:
    perfil = cargar_perfil(nombre)
    perfil["sesiones"] = perfil.get("sesiones", 0) + 1
    guardar_perfil(perfil)
    st.session_state["perfil"] = perfil
    st.session_state["_nombre_actual"] = nombre
    for key in ("messages", "diag_paso", "diag_respuestas"):
        st.session_state.pop(key, None)

perfil = st.session_state["perfil"]

# ══════════════════════════════════════════════════════════════════════════════
# FASE 1 · DIAGNÓSTICO INICIAL
# ══════════════════════════════════════════════════════════════════════════════
if not perfil["diagnostico_completado"]:
    st.subheader("📋 Diagnóstico inicial")
    st.info(
        "Antes de comenzar la tutoría, responde estas preguntas breves. "
        "Permitirán al tutor personalizar tu experiencia de aprendizaje."
    )
    st.caption("_(Esto solo ocurre en tu primera sesión)_")

    paso = st.session_state.get("diag_paso", 0)
    respuestas = st.session_state.get("diag_respuestas", [])

    if paso < len(PREGUNTAS_DIAG):
        st.progress(paso / len(PREGUNTAS_DIAG))
        st.markdown(f"**Pregunta {paso + 1} de {len(PREGUNTAS_DIAG)}:**")
        st.markdown(PREGUNTAS_DIAG[paso])
        r = st.text_area("Tu respuesta:", key=f"diag_{paso}", height=120)
        if st.button("Continuar →", type="primary"):
            if r.strip():
                respuestas.append(r.strip())
                st.session_state["diag_respuestas"] = respuestas
                st.session_state["diag_paso"] = paso + 1
                st.rerun()
            else:
                st.warning("Por favor escribe una respuesta antes de continuar.")
    else:
        perfil["diagnostico_completado"] = True
        perfil["notas_diagnostico"] = " | ".join(respuestas)
        guardar_perfil(perfil)
        st.session_state["perfil"] = perfil
        st.success("✅ Diagnóstico registrado. ¡Comenzamos la tutoría!")
        st.rerun()

    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# FASE 2 · CHAT DE TUTORÍA
# ══════════════════════════════════════════════════════════════════════════════
if "messages" not in st.session_state:
    s = perfil["sesiones"]
    bienvenida = (
        f"¡Hola, **{nombre}**! Soy tu tutor de **{tema}**. "
        + (
            "Basándome en tu diagnóstico inicial, estoy listo para acompañarte. "
            "¿Con qué concepto o pregunta quieres empezar?"
            if s <= 1
            else f"Esta es tu sesión n.º **{s}**. ¿En qué avanzamos hoy?"
        )
    )
    st.session_state["messages"] = [{"role": "Chatbot", "text": bienvenida}]

for msg in st.session_state.messages:
    rol_display = "assistant" if msg["role"] == "Chatbot" else "user"
    st.chat_message(rol_display).write(msg["text"])

if entrada := st.chat_input("Escribe tu pregunta, duda o respuesta…"):
    st.chat_message("user").write(entrada)

    client = cohere.Client(api_key=cohere_api_key)
    preamble = construir_preamble(perfil, tema)

    with st.spinner("El tutor está elaborando su respuesta…"):
        respuesta_obj = client.chat(
            chat_history=st.session_state.messages,
            message=entrada,
            documents=documentos,
            prompt_truncation="AUTO",
            preamble=preamble,
        )

    respuesta_texto = respuesta_obj.text
    st.session_state.messages.append({"role": "User", "text": entrada})
    st.session_state.messages.append({"role": "Chatbot", "text": respuesta_texto})
    st.chat_message("assistant").write(respuesta_texto)
