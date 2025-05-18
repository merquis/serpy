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

# ── utilidades MongoDB ─────────────────────────────────────────────
from modules.utils.mongo_utils import (
    obtener_documentos_mongodb,
    obtener_documento_mongodb,
)

# ═══════════════════════════════════════════════════════════════════
#  Configuración Mongo (usa secrets)
# ═══════════════════════════════════════════════════════════════════
MONGO_URI  = st.secrets["mongodb"]["uri"]
MONGO_DB   = st.secrets["mongodb"]["db"]
MONGO_COLL = "hoteles"   # colección por defecto

# ═══════════════════════════════════════════════════════════════════
#  Helpers OpenAI y cálculos
# ═══════════════════════════════════════════════════════════════════

def get_openai_client():
    return openai.Client(api_key=st.secrets["openai"]["api_key"])


def estimar_coste(modelo: str, tokens_in: int, tokens_out: int):
    """Devuelve una tupla (USD entrada, USD salida)"""
    precios = {
        "gpt-4.1-mini-2025-04-14": (0.0004, 0.0016),
        "gpt-4.1-2025-04-14":      (0.0020, 0.0080),
        "chatgpt-4o-latest":       (0.00375, 0.0150),
        "o3-2025-04-16":           (0.0100, 0.0400),
        "o3-mini-2025-04-16":      (0.0011, 0.0044),
    }
    precio_in, precio_out = precios.get(modelo, (0, 0))
    return (tokens_in / 1000) * precio_in, (tokens_out / 1000) * precio_out


def prompt_esquema(palabra_clave: str, idioma: str, tipo_articulo: str, rellenar: bool):
    accion = (
        "Solo genera el árbol de encabezados (H1, H2, H3) en JSON." if not rellenar
        else "Genera el árbol H1→H2→H3 y añade contenido optimizado SEO debajo de cada encabezado."
    )
    return f"""
Eres un experto en SEO técnico y redacción.

Debes crear la ESTRUCTURA ideal para posicionar la palabra clave «{palabra_clave}» en Google España (idioma {idioma.lower()}).
Tipo de artículo: {tipo_articulo}.

Tareas:
- Analiza los competidores top‑10 y detecta su jerarquía de H1/H2/H3.
- Propón un esquema superior que cubra todas las intenciones de búsqueda.
- {accion}

Formato de respuesta: un JSON con la siguiente forma:
{{
  "H1": "…",
  "H2": [
      {{
        "titulo": "…",
        "H3": ["…", "…"]{","\n        "contenido": "…"  // ← solo si se pidió rellenar
      }}
  ]
}}
""".strip()

# ═══════════════════════════════════════════════════════════════════
#  UI principal: Generador de esquema / contenido SEO
# ═══════════════════════════════════════════════════════════════════

def render_generador_articulos():
    st.session_state.setdefault("contenido_json", None)
    st.session_state.setdefault("palabra_clave", "")

    st.title("📚 Generador de Esquema SEO (+ Contenido opcional)")
    st.markdown("Carga un JSON de referencia o trabaja sin él, elige modelo y genera la estructura.")

    # ────────────── CARGA DEL JSON OPCIONAL ──────────────
    fuente = st.radio(
        "Fuente del JSON (opcional):",
        ["Ninguno", "Desde ordenador", "Desde Drive", "Desde MongoDB"],
        horizontal=True,
        index=0,
    )

    if fuente == "Desde ordenador":
        archivo = st.file_uploader("Sube un archivo JSON", type="json")
        if archivo:
            st.session_state.contenido_json = archivo.read()
            st.session_state.palabra_clave = ""
            st.success("JSON cargado desde tu ordenador.")

    elif fuente == "Desde Drive":
        if "proyecto_id" not in st.session_state:
            st.warning("Selecciona un proyecto en la barra lateral para usar Drive.")
        else:
            carpeta_id = obtener_o_crear_subcarpeta("scraper etiquetas google", st.session_state.proyecto_id)
            archivos = listar_archivos_en_carpeta(carpeta_id)
            if archivos:
                elegido = st.selectbox("Archivo JSON:", list(archivos.keys()))
                if st.button("📂 Cargar JSON de Drive"):
                    st.session_state.contenido_json = obtener_contenido_archivo_drive(archivos[elegido])
                    st.success("JSON cargado desde Drive.")
            else:
                st.info("Sin archivos en la carpeta del proyecto.")

    elif fuente == "Desde MongoDB":
        docs = obtener_documentos_mongodb(MONGO_URI, MONGO_DB, MONGO_COLL, campo_nombre="busqueda")
        if docs:
            sel = st.selectbox("Documento:", docs)
            if st.button("📂 Cargar JSON de MongoDB"):
                doc = obtener_documento_mongodb(MONGO_URI, MONGO_DB, MONGO_COLL, sel, campo_nombre="busqueda")
                st.session_state.contenido_json = json.dumps(doc, ensure_ascii=False).encode()
                st.success("JSON cargado desde MongoDB.")
        else:
            st.info("No hay documentos en la colección.")

    # ────────────── PARAMETROS SEO ──────────────
    st.markdown("---")
    colA, colB = st.columns(2)
    with colA:
        palabra_clave = st.text_input("Palabra clave", value=st.session_state.palabra_clave)
        idioma = st.selectbox("Idioma", ["Español", "Inglés", "Francés", "Alemán"], index=0)
        tipo_articulo = st.selectbox("Tipo de artículo", ["Informativo", "Transaccional", "Ficha de producto"], index=0)
    with colB:
        modelos = [
            "gpt-4.1-mini-2025-04-14",
            "gpt-4.1-2025-04-14",
            "chatgpt-4o-latest",
            "o3-2025-04-16",
            "o3-mini-2025-04-16",
        ]
        modelo = st.selectbox("Modelo GPT", modelos, index=0)
        temperature = st.slider("Creatividad (temperature)", 0.0, 1.5, 1.0, 0.1)

    # Opciones de generación
    col1, col2 = st.columns(2)
    with col1:
        generar_esquema = st.checkbox("📑 Generar esquema SEO", value=True)
    with col2:
        rellenar_contenido = st.checkbox("✍️ Rellenar contenido debajo de Hn", value=False)

    if st.button("🧠 Generar con IA"):
        if not generar_esquema:
            st.warning("Debes seleccionar al menos 'Generar esquema SEO'.")
            st.stop()

        prompt_usuario = prompt_esquema(palabra_clave, idioma, tipo_articulo, rellenar_contenido)
        contexto = ""
        if st.session_state.contenido_json:
            try:
                data_json = json.loads(
                    st.session_state.contenido_json.decode("utf-8") if isinstance(st.session_state.contenido_json, bytes) else st.session_state.contenido_json
                )
                contexto = "\n\nJSON de referencia:\n" + json.dumps(data_json, ensure_ascii=False, indent=2)
            except Exception:
                st.warning("No se pudo decodificar el JSON cargado.")

        prompt_final = prompt_usuario + contexto
        client = get_openai_client()

        # Token estimado
        tokens_in = len(prompt_final) // 4
        tokens_out = 3000 if rellenar_contenido else 1200
        coste_in, coste_out = estimar_coste(modelo, tokens_in, tokens_out)
        st.info(f"Coste estimado → entrada ${coste_in:.2f} + salida ${coste_out:.2f}")

        with st.spinner("Consultando OpenAI…"):
            try:
                respuesta = client.chat.completions.create(
                    model=modelo,
                    messages=[
                        {"role": "system", "content": "Eres un experto en SEO y copy."},
                        {"role": "user", "content": prompt_final},
                    ],
                    temperature=temperature,
                    max_tokens=tokens_out,
                )
                resultado = respuesta.choices[0].message.content.strip()
                st.session_state["resultado_seo"] = resultado
                st.success("✅ Generado correctamente")
            except Exception as e:
                st.error(f"❌ Error: {e}")
                st.stop()

    # ────────────── MOSTRAR Y EXPORTAR RESULTADO ──────────────
    if "resultado_seo" in st.session_state:
        st.markdown("### Resultado JSON")
        st.code(st.session_state["resultado_seo"], language="json")

        bytes_json = st.session_state["resultado_seo"].encode("utf-8")
        colD, colE = st.columns(2)
        with colD:
            st.download_button(
                "⬇️ Descargar JSON",
                data=bytes_json,
                file_name="esquema_seo.json",
                mime="application/json",
            )
        with colE:
            if st.button("☁️ Subir a Drive"):
                if "proyecto_id" not in st.session_state:
                    st.error("Selecciona primero un proyecto en la barra lateral.")
                else:
                    carpeta = obtener_o_crear_subcarpeta("esquemas seo", st.session_state["proyecto_id"])
                    enlace = subir_json_a_drive("esquema_seo.json", bytes_json, carpeta)
                    if enlace:
                        st.success(f"Subido: [Ver en Drive]({enlace})")
                    else:
                        st.error("Error subiendo a Drive.")

# Llamada principal si el script se ejecuta directamente en Streamlit
if __name__ == "__main__":
    render_generador_articulos()
