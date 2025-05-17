import streamlit as st
import json
import openai
from datetime import datetime
from typing import Dict, Any

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
    """Prompt base auto‑generado"""
    return f"""
Eres un experto en redacción SEO, copywriting y posicionamiento en Google.

A continuación tienes un resumen estructurado de las páginas mejor posicionadas en Google España (idioma {idioma.lower()}) para la palabra clave: \"{palabra_clave}\".

Tu tarea es:
- Analizar el contenido de referencia.
- Detectar las intenciones de búsqueda del usuario.
- Identificar los temas más recurrentes y relevantes.
- Reconocer la estructura común de encabezados (H1, H2, H3).
- Estudiar el enfoque editorial de los competidores.

Redacta un artículo original, más útil y mejor optimizado. No menciones que eres IA.

Tono sugerido: {tono}
Longitud: {obtener_rango_legible(rango)}
Idioma: {idioma}
Tipo: {tipo_articulo}
"""

def estimar_coste(modelo: str, tokens_in: int, tokens_out: int):
    p_in, p_out = PRECIOS.get(modelo, (0, 0))
    return tokens_in / 1000 * p_in, tokens_out / 1000 * p_out

# ═══════════════════════════════════════
# 🎛️  INTERFAZ PRINCIPAL
# ═══════════════════════════════════════

def render_generador_articulos():
    """Render de la interfaz Streamlit."""
    st.session_state.setdefault("contenido_json", None)

    st.title("🧠 Generador Maestro de Artículos SEO")
    fuente = st.radio("Fuente JSON", ["Ninguno", "Desde ordenador", "Desde Drive", "Desde MongoDB"], horizontal=True)

    # ----------- CARGA JSON -----------
    if fuente == "Desde ordenador":
        up = st.file_uploader("JSON", type="json")
        if up:
            st.session_state.contenido_json = up.read()
            st.session_state.nombre_base = up.name
            st.rerun()
    elif fuente == "Desde Drive":
        if "proyecto_id" not in st.session_state:
            st.error("Selecciona proyecto en barra lateral.")
            st.stop()
        carpeta = obtener_o_crear_subcarpeta("scraper etiquetas google", st.session_state.proyecto_id)
        archivos = listar_archivos_en_carpeta(carpeta)
        if archivos:
            elegido = st.selectbox("Archivo", list(archivos.keys()))
            if st.button("Cargar Drive"):
                st.session_state.contenido_json = obtener_contenido_archivo_drive(archivos[elegido])
                st.session_state.nombre_base = elegido
                st.rerun()
        else:
            st.warning("Sin JSONs en Drive.")
    elif fuente == "Desde MongoDB":
        docs = obtener_documentos_mongodb(MONGO_URI, MONGO_DB, MONGO_COLL_SCRAPED, campo_nombre="busqueda")
        if docs:
            sel = st.selectbox("Documento", docs)
            if st.button("Cargar MongoDB"):
                doc = obtener_documento_mongodb(MONGO_URI, MONGO_DB, MONGO_COLL_SCRAPED, sel, campo_nombre="busqueda")
                st.session_state.contenido_json = json.dumps(doc, ensure_ascii=False).encode()
                st.session_state.nombre_base = sel
                st.rerun()
        else:
            st.warning("Colección vacía.")

    # ----------- PARÁMETROS -----------
    tipos = ["Informativo", "Ficha de producto", "Transaccional"]
    idiomas = ["Español", "Inglés", "Francés", "Alemán"]
    rangos = ["1000 - 2000", "2000 - 3000", "3000 - 4000", "4000 - 5000"]

    tipo = st.selectbox("Tipo", tipos)
    idioma = st.selectbox("Idioma", idiomas)
    rango_palabras = st.selectbox("Rango palabras", rangos)
    tono = st.selectbox("Tono", ["Neutro profesional", "Persuasivo", "Narrativo"], index=1)
    modelo = st.selectbox("Modelo", OPENAI_MODELS, index=0)

    temperature = st.slider("Temperature", 0.0, 1.5, 1.0, 0.1)
    top_p = st.slider("Top‑p", 0.0, 1.0, 0.9, 0.05)

    palabra_clave = st.text_input("Palabra clave", st.session_state.get("palabra_clave", ""))
    st.session_state.palabra_clave = palabra_clave

    prompt_base = generar_prompt_extra(palabra_clave, idioma, tipo, rango_palabras, tono)
    prompt_extra = st.text_area("Prompt extra", prompt_base, height=300)

    # ----------- ESTIMACIÓN COSTE -----------
    chars_json = len(st.session_state.contenido_json or b"")
    tokens_in = chars_json // 4
    max_words = int(rango_palabras.split(" - ")[1])
    tokens_out = int(max_words * 1.4)
    c_in, c_out = estimar_coste(modelo, tokens_in, tokens_out)
    st.info(f"Coste estimado: ${(c_in+c_out):.3f} USD")

    # ----------- GENERAR ARTÍCULO -----------
    if st.button("Generar artículo") and palabra_clave:
        client = get_openai_client()
        contexto = ""
        if st.session_state.contenido_json:
            try:
                datos = json.loads(st.session_state.contenido_json.decode("utf-8"))
                contexto = "\n\nContexto JSON:\n" + json.dumps(datos, ensure_ascii=False, indent=2)
            except Exception:
                pass
        prompt_final = f"{prompt_extra}\n{contexto}"
        with st.spinner("Llamando a OpenAI …"):
            try:
                resp = client.chat.completions.create(
                    model=modelo,
                    messages=[{"role": "user", "content": prompt_final}],
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=tokens_out,
                )
                contenido = resp.choices[0].message.content.strip()
                st.session_state.articulo = {
                    "fecha": datetime.utcnow().isoformat(),
                    "modelo": modelo,
                    "tipo": tipo,
                    "idioma": idioma,
                    "tono": tono,
                    "rango": rango_palabras,
                    "keyword": palabra_clave,
                    "json_origen": st.session_state.get("nombre_base"),
                    "contenido": contenido,
                }
            except Exception as e:
                st.error(f"Error OpenAI: {e}")

    # ----------- MOSTRAR Y EXPORTAR -----------
    if st.session_state.get("articulo"):
        art = st.session_state.articulo
        st.markdown("## Artículo generado")
        st.write(art["contenido"])

        datos_bytes = json.dumps(art, ensure_ascii=False, indent=2).encode()

        col_dl, col_drive, col_mongo = st.columns(3)
        with col_dl:
            st.download_button("⬇️ Descargar JSON", data=datos_bytes, file_name="articulo_seo.json", mime="application/json")
        with col_drive:
            if st.button("☁️ Subir a Drive"):
                if "proyecto_id" not in st.session_state:
                    st.error("Selecciona proyecto en la barra lateral.")
                else:
                    carpeta_posts = obtener_o_crear_subcarpeta("posts automaticos", st.session_state.proyecto_id)
                    enlace = subir_json_a_drive("articulo_seo.json", datos_bytes, carpeta_posts)
                    if enlace:
                        st.success(f"Subido: [Ver en Drive]({enlace})")
                    else:
                        st.error("Error al subir a Drive.")
        with col_mongo:
            if st.button("💾 Guardar en MongoDB"):
                try:
                    _id = subir_a_mongodb(art, MONGO_DB, MONGO_COLL_ARTICLES, uri=MONGO_URI)
                    st.success(f"Guardado en MongoDB con id {_id}")
                except Exception as e:
                    st.error(f"Error MongoDB: {e}")
