import streamlit as st
import json
import openai

# ── utilidades Google Drive ─────────────────────────────────────────
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    subir_json_a_drive,
    obtener_o_crear_subcarpeta,
)

# ── utilidades MongoDB ── (🆕 solo para cargar) ───────────────────────
from modules.utils.mongo_utils import (
    obtener_documentos_mongodb,
    obtener_documento_mongodb,
)

# conexión Mongo (ajusta si cambias credenciales/colección)
MONGO_URI  = st.secrets["mongodb"]["uri"]
MONGO_DB   = st.secrets["mongodb"]["db"]
MONGO_COLL = "hoteles"


def get_openai_client():
    return openai.Client(api_key=st.secrets["openai"]["api_key"])

def obtener_rango_legible(rango):
    partes = rango.split(" - ")
    if len(partes) == 2:
        return f"entre {partes[0]} y {partes[1]} palabras"
    return rango

def generar_prompt_esquema(palabra_clave, idioma, tipo_articulo, incluir_texto):
    return f"""
Eres un experto en redacción SEO y estructura de contenidos para posicionamiento en Google.

A continuación tienes un resumen estructurado de los resultados más relevantes en Google España (idioma {idioma.lower()}) para la palabra clave: "{palabra_clave}".

Tu tarea es:
- Analizar la estructura de encabezados de los competidores (H1, H2, H3).
- Identificar patrones comunes y temas recurrentes.
- Crear un esquema jerárquico SEO ideal con H1, H2, H3 para superar el contenido existente.
- {"Además, escribe un texto bajo cada encabezado con contenido original SEO optimizado." if incluir_texto else "No redactes contenido, solo muestra los encabezados como árbol JSON."}

Formato de respuesta: estructura JSON con nodos anidados.
""".strip()

def estimar_coste(modelo, tokens_entrada, tokens_salida):
    precios = {
        "gpt-4.1-mini-2025-04-14": (0.0004, 0.0016),
        "gpt-4.1-2025-04-14":      (0.0020, 0.0080),
        "chatgpt-4o-latest":       (0.00375, 0.0150),
        "o3-2025-04-16":           (0.0100, 0.0400),
        "o3-mini-2025-04-16":      (0.0011, 0.0044),
    }
    ent, sal = precios.get(modelo, (0, 0))
    return tokens_entrada / 1000 * ent, tokens_salida / 1000 * sal

def render_generador_articulos():
    st.session_state.setdefault("contenido_json", None)
    st.session_state.setdefault("palabra_clave", "")

    st.title("📚 Generador de Artículos y Esquemas SEO")

    fuente = st.radio("Fuente del JSON:", ["Ninguno", "Desde Drive", "Desde MongoDB"], horizontal=True, index=1)

    if fuente == "Desde Drive":
        if "proyecto_id" not in st.session_state:
            st.warning("Selecciona un proyecto en la barra lateral.")
            return
        carpeta_id = obtener_o_crear_subcarpeta("scraper etiquetas google", st.session_state.proyecto_id)
        archivos = listar_archivos_en_carpeta(carpeta_id)
        if archivos:
            elegido = st.selectbox("Selecciona archivo:", list(archivos.keys()))
            if st.button("📂 Cargar JSON"):
                st.session_state.contenido_json = obtener_contenido_archivo_drive(archivos[elegido])
                try:
                    data = json.loads(st.session_state.contenido_json.decode("utf-8"))
                    st.session_state.palabra_clave = data.get("busqueda", "")
                except: st.warning("JSON inválido")
                st.rerun()

    elif fuente == "Desde MongoDB":
        docs = obtener_documentos_mongodb(MONGO_URI, MONGO_DB, MONGO_COLL, campo_nombre="busqueda")
        if docs:
            sel = st.selectbox("Selecciona documento:", docs)
            if st.button("📂 Cargar JSON"):
                doc = obtener_documento_mongodb(MONGO_URI, MONGO_DB, MONGO_COLL, sel, campo_nombre="busqueda")
                if doc:
                    st.session_state.contenido_json = json.dumps(doc, ensure_ascii=False).encode()
                    st.session_state.palabra_clave = doc.get("busqueda", "")
                    st.rerun()

    st.markdown("---")
    st.subheader("⚙️ Parámetros del esquema")

    palabra_clave = st.text_input("Palabra clave", value=st.session_state.palabra_clave)
    idioma = st.selectbox("Idioma", ["Español", "Inglés", "Francés", "Alemán"], index=0)
    tipo = st.selectbox("Tipo de artículo", ["Informativo", "Transaccional", "Ficha de producto"], index=0)
    modelo = st.selectbox("Modelo", [
        "gpt-4.1-mini-2025-04-14",
        "gpt-4.1-2025-04-14",
        "chatgpt-4o-latest",
        "o3-2025-04-16",
        "o3-mini-2025-04-16"
    ], index=0)

    col1, col2 = st.columns(2)
    with col1:
        generar_esquema = st.checkbox("📑 Generar esquema SEO", value=True)
    with col2:
        redactar_contenido = st.checkbox("✍️ Rellenar contenido debajo de Hn", value=False)

    temperature = st.slider("Creatividad (temperature)", 0.0, 1.5, 1.0, 0.1)

    if st.button("🧠 Generar con IA"):
        if not generar_esquema:
            st.warning("Debes seleccionar al menos 'Generar esquema SEO'")
            return

        prompt = generar_prompt_esquema(palabra_clave, idioma, tipo, redactar_contenido)

        contexto = ""
        if st.session_state.contenido_json:
            try:
                data = json.loads(st.session_state.contenido_json.decode("utf-8"))
                contexto = "\n\nResumen estructurado:\n" + json.dumps(data, ensure_ascii=False, indent=2)
            except: st.warning("Error leyendo JSON")

        prompt_final = prompt + contexto
        client = get_openai_client()

        with st.spinner("Esperando respuesta de OpenAI..."):
            try:
                tokens_entrada = len(prompt_final) // 4
                tokens_salida = 3000 if redactar_contenido else 1200
                resp = client.chat.completions.create(
                    model=modelo,
                    messages=[
                        {"role": "system", "content": "Eres un experto en SEO y estructura web."},
                        {"role": "user", "content": prompt_final.strip()}
                    ],
                    temperature=temperature,
                    max_tokens=tokens_salida,
                )
                st.success("✅ Generado con éxito")
                st.markdown("### Resultado:")
                st.code(resp.choices[0].message.content.strip(), language="json")
            except Exception as e:
                st.error(f"❌ Error al generar: {e}")
