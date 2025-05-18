import streamlit as st
import json
import openai
import re
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

# -------------------------------------------------------------------
# OpenAI helper
# -------------------------------------------------------------------

def get_openai_client():
    return openai.Client(api_key=st.secrets["openai"]["api_key"])

# -------------------------------------------------------------------
# Stop‑word‑aware slug generation (solo raíz)
# -------------------------------------------------------------------

STOPWORDS = {
    "es": {"de", "del", "la", "las", "el", "los", "en", "con", "y", "para", "por", "un", "una"},
    "en": {"the", "of", "in", "and", "for", "to", "a", "an", "with"},
    "fr": {"de", "la", "les", "des", "et", "en", "pour", "du", "un", "une"},
    "de": {"der", "die", "das", "und", "mit", "für", "ein", "eine", "von", "in"},
}

def make_slug(title: str, lang_code: str = "es") -> str:
    """Genera slug kebab‑case sin stopwords ni tildes."""
    words = re.sub(r"[^\w\s-]", "", title.lower()).split()
    cleaned = [w for w in words if w not in STOPWORDS.get(lang_code, set())]
    return slugify(" ".join(cleaned))

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
    detalles: List[str] = [
        "Devuelve una estructura JSON: un nodo raíz (H1) con children H2 y cada H2 con children H3.",
        "Parafrasa los títulos respecto a la competencia y ordena por relevancia.",
        "Incluye un único campo 'slug' (kebab‑case, sin stopwords) SOLO en el H1 si se solicita.",
        "Incluye en cada nodo un campo 'word_count' con la longitud objetivo en palabras.",
    ]
    if want_text:
        detalles.append("Genera un párrafo orientado SEO bajo cada nodo ('contenido'). Utiliza ~30 % más palabras que la media detectada para su nivel.")

    def ctx(lvl: str, n: int):
        lista = cands.get(lvl, {}).get("titles", [])[:n]
        return "\n".join(f"- {t}" for t in lista) if lista else "- (vacío)"

    contexto = f"""
### Candidatos de la competencia
• H1 frecuentes:\n{ctx('h1',5)}\n• H2 frecuentes:\n{ctx('h2',10)}\n• H3 frecuentes:\n{ctx('h3',10)}"""

    detalles_txt = "\n".join(f"- {d}" for d in detalles)

    return f"""
Eres consultor SEO senior especializado en arquitectura de contenidos.
Genera el MEJOR esquema H1/H2/H3 para posicionar en top‑5 Google la keyword \"{keyword}\" (idioma {idioma}).

{contexto}

Instrucciones:
{detalles_txt}

Devuelve SOLO un JSON válido sin comentarios. Empieza directamente con '{{'.""".strip()

# -------------------------------------------------------------------
# Coste estimado
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

    # colocamos los cuatro controles en una sola fila (25 % cada uno)
    modelos = [
        "gpt-4.1-mini-2025-04-14",
        "gpt-4.1-2025-04-14",
        "chatgpt-4o-latest",
        "o3-2025-04-16",
        "o3-mini-2025-04-16",
    ]

    col_kw, col_idioma, col_tipo, col_model = st.columns(4)
    with col_kw:
        palabra = st.text_input("Keyword principal", value=st.session_state.get("pre_kw", ""))
    with col_idioma:
        idioma = st.selectbox("Idioma", ["Español", "Inglés", "Francés", "Alemán"], index=0)
    with col_tipo:
        tipo = st.selectbox("Tipo de contenido", ["Informativo", "Transaccional", "Ficha de producto"], index=0)
    with col_model:
        modelo = st.selectbox("Modelo GPT", modelos, index=0)

    # === Ajustes avanzados ==========================================
    with st.expander("⚙️ Ajustes avanzados", expanded=False):
        colA, colB = st.columns(2)
        with colA:
            temperature = st.slider("Temperature", 0.0, 2.0, 0.9, 0.05)
            top_p = st.slider("Top‑p", 0.0, 1.0, 1.0, 0.05)
        with colB:
            freq_pen = st.slider("Frequency penalty", 0.0, 2.0, 0.0, 0.1)
            pres_pen = st.slider("Presence penalty", 0.0, 2.0, 0.0, 0.1)

    # === Opciones de generación =====================================
    col1, col2, col3 = st.columns(3)
    with col1:
        gen_schema = st.checkbox("📑 Esquema", value=True)
    with col2:
        gen_text = st.checkbox("✍️ Textos")
    with col3:
        want_slug = st.checkbox("🔗 Slug H1", value=True)

    # === Coste estimado =============================================
    est_in = len(st.session_state.json_fuente or b"") // 4
    est_out = 3000 if gen_text else 800  # más margen cuando solo esquema
    cin, cout = estimate_cost(modelo, est_in, est_out)
    st.markdown(f"💰 Coste aprox → Entrada: {cin:.2f} / Salida: {cout:.2f} (<1 € objetivo)")

    # === Ejecutar ====================================================
    if st.button("🚀 Ejecutar"):
        if not palabra:
            st.warning("Debe introducirse una keyword")
            st.stop()

        client = get_openai_client()
        candidates = extract_candidates(st.session_state.json_fuente)
        prompt = build_prompt(
            palabra,
            idioma,
            tipo,
            gen_text,
            want_slug,
            candidates,
        )

        with st.spinner("Llamando a OpenAI..."):
            try:
                rsp = client.chat.completions.create(
                    model=modelo,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    top_p=top_p,
                    frequency_penalty=freq_pen,
                    presence_penalty=pres_pen,
                    max_tokens=est_out,
                )
                raw = rsp.choices[0].message.content.strip()
                try:
                    parsed = json.loads(raw)
                except Exception:
                    st.error("La IA no devolvió un JSON válido. Respuesta cruda mostrada.")
                    st.code(raw)
                    st.stop()

                # Añade slug si falta y se solicitó
                if want_slug and "slug" not in parsed:
                    parsed["slug"] = make_slug(parsed.get("title", palabra), "es")

                st.session_state.respuesta_ai = parsed
            except Exception as e:
                st.error(f"❌ Error OpenAI: {e}")
                st.stop()

    # === Mostrar resultado ==========================================
    if st.session_state.get("respuesta_ai"):
        st.markdown("### Resultado JSON")
        st.json(st.session_state.respuesta_ai, expanded=True)  # mostrado expandido

        file_bytes = json.dumps(st.session_state.respuesta_ai, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button("⬇️ Descargar JSON", data=file_bytes, file_name="esquema_seo.json", mime="application/json")

        if st.button("☁️ Subir a Drive"):
            if not st.session_state.get("proyecto_id"):
                st.error("Debes seleccionar un proyecto")
            else:
                carpeta = obtener_o_crear_subcarpeta("posts automaticos", st.session_state["proyecto_id"])
                link = subir_json_a_drive("esquema_seo.json", file_bytes, carpeta)
                if link:
                    st.success(f"Subido ✔️ [Ver en Drive]({link})")
                else:
                    st.error("Error al subir a Drive")
