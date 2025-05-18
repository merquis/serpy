import streamlit as st
import json
import openai
from collections import Counter
from slugify import slugify
from typing import Any, Dict, List

# ── utilidades Google Drive ─────────────────────────────────────────
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    subir_json_a_drive,
    obtener_o_crear_subcarpeta,
)

# ── utilidades MongoDB ──────────────────────────────────────────────
from modules.utils.mongo_utils import (
    obtener_documentos_mongodb,
    obtener_documento_mongodb,
)

# conexión Mongo (ajusta si cambias credenciales/colección)
MONGO_URI = st.secrets["mongodb"]["uri"]
MONGO_DB = st.secrets["mongodb"]["db"]
MONGO_COLL = "hoteles"  # colección por defecto

# ═══════════════════════════════════════════════════════════════════
# helpers
# ═══════════════════════════════════════════════════════════════════

def get_openai_client():
    return openai.Client(api_key=st.secrets["openai"]["api_key"])


# -------------------------------------------------------------------
# Heurística local: extraer H1/H2/H3 más frecuentes del JSON fuente
# -------------------------------------------------------------------

def _colectar_encabezados(data: Any, nivel: str, bucket: Counter):
    """Recorre recursivamente el JSON y acumula títulos por nivel."""
    if isinstance(data, dict):
        if data.get("level") == nivel and data.get("title"):
            bucket[data["title"].strip()] += 1
        for v in data.values():
            _colectar_encabezados(v, nivel, bucket)
    elif isinstance(data, list):
        for item in data:
            _colectar_encabezados(item, nivel, bucket)


def extract_candidates(json_bytes: bytes, top_k: int = 20) -> Dict[str, List[str]]:
    """Devuelve los encabezados más repetidos para cada nivel."""
    out: Dict[str, List[str]] = {"h1": [], "h2": [], "h3": []}
    if not json_bytes:
        return out

    try:
        data = json.loads(json_bytes.decode("utf-8"))
    except Exception:
        return out

    for lvl in ("h1", "h2", "h3"):
        bucket: Counter = Counter()
        _colectar_encabezados(data, lvl, bucket)
        out[lvl] = [t for t, _ in bucket.most_common(top_k)]
    return out


# -------------------------------------------------------------------
# Construcción dinámica del prompt maestro
# -------------------------------------------------------------------

def generar_prompt_esquema(
    keyword: str,
    idioma: str,
    tipo: str,
    incluir_texto: bool,
    incluir_slug: bool,
    candidatos: Dict[str, List[str]],
) -> str:
    detalles: List[str] = [
        "Un único nodo raíz H1 -> varios H2 -> H3 en árbol.",
        "Ordena los nodos para cubrir todas las intenciones de búsqueda y maximizar CTR.",
        "No repitas exactamente los títulos de la competencia (parafrasa).",
    ]
    if incluir_texto:
        detalles.append("Escribe un párrafo útil y orientado a SEO bajo cada encabezado (≈120‑160 palabras).")
    if incluir_slug:
        detalles.append("Incluye un único campo 'slug' (kebab‑case, sin tildes) SOLO en el H1.")

    contexto_competencia = "\n".join(
        [
            "### Candidatos H1" if i == 0 else "",
            *[f"- {h}" for h in candidatos.get("h1", [])[:5]],
            "### Candidatos H2",
            *[f"- {h}" for h in candidatos.get("h2", [])[:10]],
            "### Candidatos H3",
            *[f"- {h}" for h in candidatos.get("h3", [])[:10]],
        ]
    )

    extras = "\n".join(f"- {d}" for d in detalles)

    plantilla_json = "{" "\"title\":\"<H1>\", \"level\":\"h1\"" + (", \"slug\":\"<slug>\"" if incluir_slug else "") + ", \"children\":[{\"title\":\"<H2>\",\"level\":\"h2\",\"children\":[{\"title\":\"<H3>\",\"level\":\"h3\"}]}]}"  # noqa: E501

    return (
        f"""
Eres un consultor SEO senior especializado en arquitectura de contenidos.
Debes crear la mejor estructura jerárquica (H1/H2/H3) para posicionar en el top‑5 de Google España la keyword «{keyword}» (idioma {idioma}).

Contexto de títulos detectados en la competencia:
{contexto_competencia}

Instrucciones clave:
{extras}

Devuelve ÚNICAMENTE un JSON con esta forma:
{plantilla_json}
""".strip()
    )


# -------------------------------------------------------------------
# Coste estimado (igual que antes)
# -------------------------------------------------------------------

def estimar_coste(modelo: str, tokens_in: int, tokens_out: int):
    precios = {
        "gpt-4.1-mini-2025-04-14": (0.0004, 0.0016),
        "gpt-4.1-2025-04-14": (0.0020, 0.0080),
        "chatgpt-4o-latest": (0.00375, 0.0150),
        "o3-2025-04-16": (0.0100, 0.0400),
        "o3-mini-2025-04-16": (0.0011, 0.0044),
    }
    precio_in, precio_out = precios.get(modelo, (0, 0))
    return (tokens_in / 1000) * precio_in, (tokens_out / 1000) * precio_out


# ═══════════════════════════════════════════════════════════════════
# INTERFAZ PRINCIPAL
# ═══════════════════════════════════════════════════════════════════

def render_generador_articulos():
    st.title("📚 Generador Maestro de Esquemas/Artículos SEO")

    # Estado global mínimo ------------------------------------------------
    st.session_state.setdefault("json_fuente", None)
    st.session_state.setdefault("respuesta_ai", None)

    # ======= Sección de carga de JSON (opcional) =========================
    fuente = st.radio("Fuente JSON opcional:", ["Ninguno", "Ordenador", "Drive", "MongoDB"], horizontal=True)

    if fuente == "Ordenador":
        archivo = st.file_uploader("Sube un JSON", type="json")
        if archivo:
            st.session_state.json_fuente = archivo.read()
            st.session_state["nombre_json"] = archivo.name
            st.experimental_rerun()

    elif fuente == "Drive":
        if "proyecto_id" not in st.session_state or not st.session_state.proyecto_id:
            st.info("Selecciona un proyecto en la barra lateral.")
        else:
            carpeta = obtener_o_crear_subcarpeta("scraper etiquetas google", st.session_state.proyecto_id)
            archivos = listar_archivos_en_carpeta(carpeta)
            if archivos:
                sel = st.selectbox("Archivo en Drive:", list(archivos.keys()))
                if st.button("📥 Cargar"):
                    st.session_state.json_fuente = obtener_contenido_archivo_drive(archivos[sel])
                    st.experimental_rerun()
            else:
                st.info("No hay JSON en esa carpeta.")

    elif fuente == "MongoDB":
        docs = obtener_documentos_mongodb(MONGO_URI, MONGO_DB, MONGO_COLL, campo_nombre="busqueda")
        if docs:
            sel = st.selectbox("Documento:", docs)
            if st.button("📥 Cargar"):
                doc = obtener_documento_mongodb(MONGO_URI, MONGO_DB, MONGO_COLL, sel, campo_nombre="busqueda")
                st.session_state.json_fuente = json.dumps(doc).encode()
                st.experimental_rerun()
        else:
            st.info("No hay documentos en Mongo.")

    # ======= Parámetros del generador ====================================
    st.markdown("---")
    palabra = st.text_input("Keyword principal")
    idioma = st.selectbox("Idioma", ["Español", "Inglés", "Francés", "Alemán"], index=0)
    tipo = st.selectbox("Tipo de contenido", ["Informativo", "Transaccional", "Ficha de producto"], index=0)

    modelos = [
        "gpt-4.1-mini-2025-04-14",
        "gpt-4.1-2025-04-14",
        "chatgpt-4o-latest",
        "o3-2025-04-16",
        "o3-mini-2025-04-16",
    ]
    modelo = st.selectbox("Modelo GPT", modelos, index=0)

    col1, col2, col3 = st.columns(3)
    with col1:
        chk_esquema = st.checkbox("📑 Esquema", True)
    with col2:
        chk_textos = st.checkbox("✍️ Textos", False)
    with col3:
        chk_slug = st.checkbox("🔗 Slug H1", True)

    if st.button("🚀 Ejecutar"):
        if not chk_esquema:
            st.error("Selecciona al menos el esquema.")
            st.stop()

        candidatos = extract_candidates(st.session_state.json_fuente, top_k=20)
        prompt = generar_prompt_esquema(palabra, idioma, tipo, chk_textos, chk_slug, candidatos)

        client = get_openai_client()
        try:
            resp = client.chat.completions.create(
                model=modelo,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                max_tokens=4096,
            )
            raw = resp.choices[0].message.content.strip()
            try:
                st.session_state.respuesta_ai = json.loads(raw)
            except json.JSONDecodeError:
                st.error("La IA no devolvió un JSON válido. Muestra crudo:")
                st.write(raw)
                st.stop()
        except Exception as e:
            st.error(f"Error llamando a OpenAI: {e}")
            st.stop()

    # ======= Mostrar y exportar ==========================================
    if st.session_state.get("respuesta_ai"):
        st.markdown("### Resultado AI (JSON)")
        st.json(st.session_state.respuesta_ai, expanded=False)

        datos_export = json.dumps(st.session_state.respuesta_ai, ensure_ascii=False, indent=2).encode()
        st.download_button("⬇️ Descargar JSON", data=datos_export, file_name="esquema_seo.json", mime="application/json")

        if "proyecto_id" in st.session_state and st.session_state.proyecto_id:
            if st.button("☁️ Guardar en Drive"):
                sub = obtener_o_crear_subcarpeta("posts automaticos", st.session_state.proyecto_id)
                link = subir_json_a_drive("esquema_seo.json", datos_export, sub)
                if link:
                    st.success(f"Subido correctamente → [Ver]({link})")
                else:
                    st.error("Fallo al subir a Drive.")
