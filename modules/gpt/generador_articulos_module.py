import streamlit as st
import json
import openai
from collections import Counter
from statistics import mean
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
# Heurística local: extraer H1/H2/H3 más frecuentes y métricas
# -------------------------------------------------------------------

def _collect_headers(data: Any, lvl: str, bucket: Counter, lens: List[int]):
    """Recorre recursivamente el JSON y acumula títulos + longitud."""
    if isinstance(data, dict):
        if data.get("level") == lvl and data.get("title"):
            title = data["title"].strip()
            bucket[title] += 1
            if isinstance(data.get("contenido"), str):
                lens.append(len(data["contenido"].split()))
        for v in data.values():
            _collect_headers(v, lvl, bucket, lens)
    elif isinstance(data, list):
        for it in data:
            _collect_headers(it, lvl, bucket, lens)


def extract_candidates(json_bytes: bytes, top_k: int = 25) -> Dict[str, Dict[str, Any]]:
    """Devuelve top titles y longitud media por nivel."""
    out: Dict[str, Dict[str, Any]] = {"h1": {}, "h2": {}, "h3": {}}
    if not json_bytes:
        return out
    try:
        data = json.loads(json_bytes.decode("utf-8"))
    except Exception:
        return out

    for lvl in ("h1", "h2", "h3"):
        bucket: Counter = Counter()
        lens: List[int] = []
        _collect_headers(data, lvl, bucket, lens)
        out[lvl]["titles"] = [t for t, _ in bucket.most_common(top_k)]
        out[lvl]["avg_len"] = mean(lens) if lens else 120
    return out


# -------------------------------------------------------------------
# Construcción del prompt maestro
# -------------------------------------------------------------------

def build_prompt(
    keyword: str,
    idioma: str,
    tipo: str,
    want_text: bool,
    want_slug: bool,
    cands: Dict[str, Dict[str, Any]],
) -> str:
    # reglas dinámicas
    detalles: List[str] = [
        "Devuelve una estructura JSON: un nodo raíz (H1) con children H2 y cada H2 con children H3.",
        "Parafrasa los títulos respecto a la competencia y ordena por relevancia de búsqueda.",
        "Incluye un único campo 'slug' (kebab‑case, sin tildes) solo en el H1 si se solicita.",
        "Incluye en cada nodo un campo 'word_count' con la longitud objetivo en palabras.",
    ]
    if want_text:
        detalles.append("Genera un párrafo orientado SEO bajo cada nodo ('contenido'). Utiliza ~30 % más palabras que la media detectada para su nivel.")
    # contexto candidatos
    def ctx(lvl: str, n: int):
        lista = cands.get(lvl, {}).get("titles", [])[:n]
        return "\n".join(f"- {t}" for t in lista) if lista else "- (vacío)"

    contexto = f"""
### Candidatos de la competencia
• H1 frecuentes:\n{ctx('h1',5)}\n• H2 frecuentes:\n{ctx('h2',10)}\n• H3 frecuentes:\n{ctx('h3',10)}"""

    plantilla = (
        "{\n  \"title\":\"<H1>\", \n  \"level\":\"h1\"," + (
            "\n  \"slug\":\"<slug>\"," if want_slug else ""
        )
        + "\n  \"word_count\":<int>,"
        + ("\n  \"contenido\":\"<texto opcional>\"," if want_text else "")
        + "\n  \"children\":[{\"title\":\"<H2>\",\"level\":\"h2\",\"word_count\":<int>,\"children\":[{\"title\":\"<H3>\",\"level\":\"h3\",\"word_count\":<int>}] }] }"
    )

    extras = "\n".join(f"- {d}" for d in detalles)

    return f"""
Eres consultor SEO senior especializado en arquitectura de contenidos multilingüe.
Crea el MEJOR esquema H1/H2/H3 para posicionar en top‑5 Google la keyword \"{keyword}\" (idioma {idioma}).

{contexto}

Instrucciones:
{extras}

Devuelve SOLO un JSON con la forma de ejemplo (sin comentarios). Empieza directamente con '{{'.
JSON ejemplo de forma:
{plantilla}
""".strip()


# -------------------------------------------------------------------
# Coste estimado (se mantiene)
# -------------------------------------------------------------------

def estimate_cost(modelo: str, tin: int, tout: int):
    precios = {
        "gpt-4.1-mini-2025-04-14": (0.0004, 0.0016),
        "gpt-4.1-2025-04-14": (0.0020, 0.0080),
        "chatgpt-4o-latest": (0.00375, 0.0150),
        "o3-2025-04-16": (0.0100, 0.0400),
        "o3-mini-2025-04-16": (0.0011, 0.0044),
    }
    pin, pout = precios.get(modelo, (0, 0))
    return (tin / 1000) * pin, (tout / 1000) * pout


# -------------------------------------------------------------------
# Utilidad: precargar keyword desde JSON
# -------------------------------------------------------------------

def preload_keyword(json_bytes: bytes):
    """Si el JSON fuente tiene campo 'busqueda', guárdalo en session."""
    if not json_bytes:
        return
    try:
        data = json.loads(json_bytes.decode("utf-8"))
        kw = data.get("busqueda") or data.get("keyword")
        if kw:
            st.session_state["pre_kw"] = kw
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════════
# INTERFAZ STREAMLIT
# ═══════════════════════════════════════════════════════════════════

def render_generador_articulos():
    st.session_state.setdefault("json_fuente", None)
    st.session_state.setdefault("respuesta_ai", None)

    st.title("📚 Generador Maestro de Esquemas/Artículos SEO")

    # === Carga JSON ===================================================
    fuente = st.radio("Fuente JSON opcional:", ["Ninguno", "Ordenador", "Drive", "MongoDB"], horizontal=True)

    if fuente == "Ordenador":
        archivo = st.file_uploader("Sube un JSON", type="json")
        if archivo:
            st.session_state.json_fuente = archivo.read()
            preload_keyword(st.session_state.json_fuente)
            st.rerun()

    elif fuente == "Drive":
        if not st.session_state.get("proyecto_id"):
            st.info("Selecciona un proyecto en la barra lateral.")
        else:
            carpeta = obtener_o_crear_subcarpeta("scraper etiquetas google", st.session_state.proyecto_id)
            archivos = listar_archivos_en_carpeta(carpeta)
            if archivos:
                sel = st.selectbox("Archivo en Drive:", list(archivos.keys()))
                if st.button("📥 Cargar"):
                    st.session_state.json_fuente = obtener_contenido_archivo_drive(archivos[sel])
                    preload_keyword(st.session_state.json_fuente)
                    st.rerun()
            else:
                st.info("No hay JSON en esa carpeta.")

    elif fuente == "MongoDB":
        docs = obtener_documentos_mongodb(MONGO_URI, MONGO_DB, MONGO_COLL, campo_nombre="busqueda")
        if docs:
            sel = st.selectbox("Documento:", docs)
            if st.button("📥 Cargar"):
                doc = obtener_documento_mongodb(MONGO_URI, MONGO_DB, MONGO_COLL, sel, campo_nombre="busqueda")
                st.session_state.json_fuente = json.dumps(doc).encode()
                preload_keyword(st.session_state.json_fuente)
                st.rerun()
        else:
            st.info("No hay documentos en Mongo.")

    # === Parámetros principales ======================================
    st.markdown("---")
    palabra = st.text_input("Keyword principal", value=st.session_state.get("pre_kw", ""))
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

    with st.expander("⚙️ Ajustes avanzados", expanded=False):
        colA, colB = st.columns(2)
        with colA:
            temperature = st.slider("Temperature", 0.0, 2.0, 0.9, 0.05)
            top_p = st.slider("Top‑p", 0.0, 1.0, 1.0
