import streamlit as st
import json
import openai
from datetime import datetime

# ---------- utilidades Drive ----------
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    subir_json_a_drive,
    obtener_o_crear_subcarpeta,
)

# ---------- utilidades MongoDB ----------
from modules.utils.mongo_utils import (
    obtener_documentos_mongodb,
    obtener_documento_mongodb,
    subir_a_mongodb,
)

# ═══════════════════════════════════════
# 🔧  CONFIGURACIÓN GENERAL
# ═══════════════════════════════════════
MONGO_URI = "mongodb://serpy:esperanza85@serpy_mongodb:27017/?authSource=admin"
MONGO_DB = "serpy"
MONGO_COLL_SCRAPED = "hoteles"          # documentos de entrada
MONGO_COLL_ARTICLES = "articulos_seo"    # backup de artículos generados

OPENAI_MODELS = [
    "gpt-3.5-turbo",
    "gpt-4o-mini",
    "gpt-4.1-nano",
    "gpt-4.1-mini",
    "gpt-4o",
    "gpt-4-turbo",
]

PRECIOS = {
    "gpt-3.5-turbo":  (0.0005, 0.0015),
    "gpt-4o-mini":    (0.0005, 0.0015),
    "gpt-4.1-nano":   (0.0010, 0.0030),
    "gpt-4.1-mini":   (0.0015, 0.0045),
    "gpt-4o":         (0.0050, 0.0150),
    "gpt-4-turbo":    (0.0100, 0.0300),
}

# ═══════════════════════════════════════
# 🛠️  HELPERS
# ═══════════════════════════════════════

def get_openai_client():
    return openai.Client(api_key=st.secrets["openai"]["api_key"])

def obtener_rango_legible(rango: str) -> str:
    try:
        ini, fin = rango.split(" - ")
        return f"entre {ini} y {fin} palabras"
    except ValueError:
        return rango

def generar_prompt_extra(palabra_clave: str, idioma: str, tipo_articulo: str, rango: str, tono: str) -> str:
    """Prompt base que se mostrará (y puede editar el usuario)"""
    return f"""
Eres un experto en redacción SEO, copywriting y posicionamiento en Google.

A continuación tienes un resumen estructurado de las páginas mejor posicionadas en Google España (idioma {idioma.lower()}) para la palabra clave: \"{palabra_clave}\".

Este resumen se basa en la recopilación de las etiquetas HTML y contenido visible de los artículos mejor posicionados para dicha búsqueda.

Tu tarea es:
- Analizar el contenido de referencia.
- Detectar las intenciones de búsqueda del usuario.
- Identificar los temas más recurrentes y relevantes.
- Reconocer la estructura común de encabezados (H1, H2, H3).
- Estudiar el enfoque editorial de los competidores.

Luego, redacta un artículo original, más útil, más completo y mejor optimizado para SEO que los que ya existen. No repitas información innecesaria ni uses frases genéricas.

Tono sugerido: {tono}

Detalles de redacción:
Longitud: {obtener_rango_legible(rango)}
Idioma: {idioma}
Tipo de artículo: {tipo_articulo}
Formato: Utiliza subtítulos claros (H2 y H3), listas, introducción persuasiva y conclusión útil.
Objetivo: Posicionarse en Google para la keyword \"{palabra_clave}\".
No menciones que eres una IA ni expliques que estás generando un texto.
Hazlo como si fueras un redactor profesional experto en turismo y SEO.
El 30% del contenido debe ser cogido del propio JSON y parafraseado para que no se detecte como contenido duplicado.
El 85% de los párrafos deben tener más de 150 palabras.
"""

def estimar_coste(modelo: str, tokens_in: int, tokens_out: int):
    precio_in, precio_out = PRECIOS.get(modelo, (0, 0))
    return tokens_in / 1000 * precio_in, tokens_out / 1000 * precio_out

# ═══════════════════════════════════════
# 🎛️  UI PRINCIPAL
# ═══════════════════════════════════════

def render_generador_articulos():
    st.session_state.setdefault("contenido_json", None)
    st.session_state.setdefault("nombre_base", None)
    st.session_state.setdefault("palabra_clave", "")

    # ---------- Título ----------
    st.title("🧠 Generador Maestro de Artículos SEO")
    st.markdown("Crea artículos SEO potentes con o sin contexto JSON. Tú tienes el control.")

    # ---------- Fuente JSON ----------
    fuente = st.radio(
        "Fuente del archivo JSON (opcional):",
        ["Ninguno", "Desde ordenador", "Desde Drive", "Desde MongoDB"],
        horizontal=True,
        index=0,
    )

    # === Desde ordenador ===
    if fuente == "Desde ordenador":
        archivo_local = st.file_uploader("Sube un archivo JSON", type="json")
        if archivo_local:
            st.session_state.contenido_json = archivo_local.read()
            st.session_state.nombre_base = archivo_local.name
            st.rerun()

    # === Desde Drive ===
    elif fuente == "Desde Drive":
        if "proyecto_id" not in st.session_state:
            st.error("❌ Selecciona un proyecto en la barra lateral.")
            st.stop()
        carpeta_id = obtener_o_crear_subcarpeta("scraper etiquetas google", st.session_state.proyecto_id)
        archivos_drive = listar_archivos_en_carpeta(carpeta_id)
        if not archivos_drive:
            st.warning("⚠️ No se encontraron JSONs en Drive para este proyecto.")
        else:
            elegido = st.selectbox("Selecciona JSON de Drive", list(archivos_drive.keys()))
            if st.button("📂 Cargar desde Drive"):
                st.session_state.contenido_json = obtener_contenido_archivo_drive(archivos_drive[elegido])
                st.session_state.nombre_base = elegido
                st.rerun()

    # === Desde MongoDB ===
    elif fuente == "Desde MongoDB":
        try:
            nombres_docs = obtener_documentos_mongodb(MONGO_URI, MONGO_DB, MONGO_COLL_SCRAPED, campo_nombre="busqueda")
            if nombres_docs:
                elegido_mongo = st.selectbox("Selecciona documento", nombres_docs)
                if st.button("🔄 Cargar desde MongoDB"):
                    doc = obtener_documento_mongodb(MONGO_URI, MONGO_DB, MONGO_COLL_SCRAPED, elegido_mongo, campo_nombre="busqueda")
                    if doc:
                        st.session_state.contenido_json = json.dumps(doc, ensure_ascii=False).encode()
                        st.session_state.nombre_base = elegido_mongo
                        st.rerun()
            else:
                st.warning("⚠️ La colección está vacía.")
        except Exception as e:
            st.error(f"❌ Error accediendo a MongoDB: {e}")

    # ---------- Si tenemos JSON cargado, parseamos campos clave ----------
    if st.session_state.contenido_json and "palabra_clave_parseada" not in st.session_state:
        try:
            crudo = st.session_state.contenido_json.decode() if isinstance(st.session_state.contenido_json, bytes) else st.session_state.contenido_json
            datos = json.loads(crudo)
            st.session_state.palabra_clave = datos.get("busqueda", "")
            st.session_state.idioma_detectado = datos.get("idioma", "Español")
            st.session_state.tipo_detectado = datos.get("tipo_articulo", "Informativo")
            st.session_state.palabra_clave_parseada = True
        except Exception as e:
            st.warning(f"⚠️ JSON inválido: {e}")

    # ---------- Parámetros básicos ----------
    st.markdown("---")
    tipos = ["Informativo", "Ficha de producto", "Transaccional"]
    idiomas = ["Español", "Inglés", "Francés", "Alemán"]
    rangos = ["1000 - 2000", "2000 - 3000", "3000 - 4000", "4000 - 5000", "5000 - 6000"]

    col1, col2, col3 = st.columns(3)
    with col1:
        tipo_articulo = st.selectbox("Tipo", tipos, index=tipos.index(st.session_state.get("tipo_detectado", "Informativo")))
    with col2:
                # --- idioma con fallback seguro ---
        idioma_detectado = st.session_state.get("idioma_detectado", "Español")
        if idioma_detectado not in idiomas:
            # mapeos rápidos "es", "en", etc.
            mapa_idiomas = {"es": "Español", "en": "Inglés", "fr": "Francés", "de": "Alemán"}
            idioma_detectado = mapa_idiomas.get(idioma_detectado.lower(), "Español")
        idioma = st.selectbox("Idioma", idiomas, index=idiomas.index(idioma_detectado))))
    with col3:
        rango_palabras = st.selectbox("Rango palabras", rangos, index=0)

    tono = st.selectbox("Tono", ["Neutro profesional", "Persuasivo", "Inspirador", "Narrativo"], index=1)
    modelo = st.selectbox("Modelo GPT", OPENAI_MODELS, index=0)

    st.session_state.update({
        "tipo_detectado": tipo_articulo,
        "idioma_detectado": idioma,
        "rango_palabras": rango_palabras,
        "tono_articulo": tono,
        "modelo": modelo,
    })

    # ---------- Parámetros avanzados ----------
    st.markdown("### Parámetros avanzados")
    colA, colB = st.columns(2)
    with colA:
        temperature = st.slider("Temperature", 0.0, 1.5, 1.0, 0.1)
        top_p = st.slider("Top-p", 0.0, 1.0, 0.9, 0.05)
    with colB:
        frequency_penalty = st.slider("Frecuencia", 0.0, 2.0, 0.7, 0.1)
        presence_penalty = st.slider("Presencia", 0.0, 2.0, 1.0, 0.1)

    # ---------- Estimación coste ----------
    caracteres_json = len(st.session_state.contenido_json or b"")
    tokens_in = caracteres_json // 4
    max_words = int(rango_palabras.split(" - ")[1])
    tokens_out = int(max_words * 1.4)
    c_in, c_out = estimar_coste(modelo, tokens_in, tokens_out)
    st.info(f"Coste estimado • Entrada: ${c_in:.3f} • Salida max.: ${c_out:.3f} • Total: ${c_in + c_out:.3f}")

    # ---------- Prompt manual ----------
    palabra_clave = st.text_input("Palabra clave", st.session_state.get("palabra_clave", ""))
    st.session_state.palabra_clave = palabra_clave

    prompt_base = generar_prompt_extra(palabra_clave, idioma, tipo_articulo, rango_palabras, tono)
    prompt_base = st.text_area("Prompt auto", prompt_base, height=300)
    prompt_extra_manual = st.text_area("Instrucciones adicionales", st.session_state.get("prompt_extra_manual", ""), height=120)
    st.session_state.prompt_extra_manual = prompt_extra_manual

    # ---------- Botón generar ----------
    if st.button("🚀 Generar artículo"):
        client = get_openai
