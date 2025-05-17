import streamlit as st
import json
import openai
from datetime import datetime

# ──────────────────────────────────────────
#  Utilidades Google Drive
# ──────────────────────────────────────────
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    subir_json_a_drive,
    obtener_o_crear_subcarpeta,
)

# ──────────────────────────────────────────
#  Utilidades MongoDB  (🆕)
# ──────────────────────────────────────────
from modules.utils.mongo_utils import (
    obtener_documentos_mongodb,
    obtener_documento_mongodb,
    subir_a_mongodb,           # para guardar el artículo al final
)

# ═════════════════════════════════════════
#  Configuración global
# ═════════════════════════════════════════
MONGO_URI = "mongodb://serpy:esperanza85@serpy_mongodb:27017/?authSource=admin"
MONGO_DB  = "serpy"
MONGO_COLL_JSON   = "hoteles"        # JSON de contexto (entrada)
MONGO_COLL_OUTPUT = "articulos_seo"  # Artículos generados (salida)

PRECIOS_OPENAI = {
    "gpt-3.5-turbo": (0.0005, 0.0015),
    "gpt-4o-mini":   (0.0005, 0.0015),
    "gpt-4.1-nano":  (0.0010, 0.0030),
    "gpt-4.1-mini":  (0.0015, 0.0045),
    "gpt-4o":        (0.0050, 0.0150),
    "gpt-4-turbo":   (0.0100, 0.0300),
}
MODELOS = list(PRECIOS_OPENAI.keys())


# ═════════════════════════════════════════
#  Funciones auxiliares
# ═════════════════════════════════════════
def get_openai_client():
    return openai.Client(api_key=st.secrets["openai"]["api_key"])


def obtener_rango_legible(rango: str) -> str:
    try:
        ini, fin = rango.split(" - ")
        return f"entre {ini} y {fin} palabras"
    except ValueError:
        return rango


def generar_prompt_extra(
    palabra_clave: str,
    idioma: str,
    tipo_articulo: str,
    rango: str,
    tono: str,
) -> str:
    return f"""
Eres un experto en redacción SEO, copywriting y posicionamiento en Google.

A continuación tienes un resumen de las páginas mejor posicionadas en Google España (idioma {idioma.lower()}) para la palabra clave: "{palabra_clave}".

Tu tarea es:
- Analizar el contenido de referencia.
- Detectar la intención de búsqueda.
- Identificar los temas más relevantes.
- Reconocer la estructura común de encabezados (H1–H3).
- Redactar un artículo original, útil y mejor optimizado.

Tono sugerido: {tono}

Detalles de redacción:
Longitud: {obtener_rango_legible(rango)}
Idioma: {idioma}
Tipo de artículo: {tipo_articulo}
Formato: subtítulos H2/H3, listas, introducción persuasiva y conclusión útil.
Objetivo: posicionarse en Google para la keyword "{palabra_clave}".
No menciones que eres IA.
El 30 % del contenido debe provenir (parafraseado) del JSON de contexto.
El 85 % de los párrafos debe superar las 150 palabras.
""".strip()


def estimar_coste(modelo: str, tok_in: int, tok_out: int):
    p_in, p_out = PRECIOS_OPENAI.get(modelo, (0, 0))
    return tok_in / 1000 * p_in, tok_out / 1000 * p_out


# ═════════════════════════════════════════
#  Interfaz principal
# ═════════════════════════════════════════
def render_generador_articulos():
    # ---------- Estado inicial ----------
    st.session_state.setdefault("contenido_json", None)
    st.session_state.setdefault("nombre_base", None)
    st.session_state.setdefault("maestro_articulo", None)

    # ---------- Cabecera ----------
    st.title("🧠 Generador Maestro de Artículos SEO")
    st.markdown("Crea artículos SEO potentes con o sin contexto JSON. Tú tienes el control.")

    # ---------- Fuente del JSON ----------
    fuente = st.radio(
        "Fuente del archivo JSON (opcional):",
        ["Ninguno", "Desde ordenador", "Desde Drive", "Desde MongoDB"],
        horizontal=True,
        index=0,
    )

    # === 1. Ordenador ===
    if fuente == "Desde ordenador":
        up = st.file_uploader("Sube JSON", type="json")
        if up:
            st.session_state.contenido_json = up.read()
            st.session_state.nombre_base = up.name
            st.rerun()

    # === 2. Google Drive ===
    elif fuente == "Desde Drive":
        if "proyecto_id" not in st.session_state:
            st.error("❌ Selecciona un proyecto en la barra lateral.")
            st.stop()
        carpeta = obtener_o_crear_subcarpeta("scraper etiquetas google", st.session_state.proyecto_id)
        archivos = listar_archivos_en_carpeta(carpeta)
        if archivos:
            sel = st.selectbox("Archivo Drive", list(archivos.keys()))
            if st.button("📂 Cargar desde Drive"):
                st.session_state.contenido_json = obtener_contenido_archivo_drive(archivos[sel])
                st.session_state.nombre_base = sel
                st.rerun()
        else:
            st.warning("⚠️ No hay JSONs en Drive para este proyecto.")

    # === 3. MongoDB (🆕) ===
    elif fuente == "Desde MongoDB":
        try:
            nombres = obtener_documentos_mongodb(
                MONGO_URI, MONGO_DB, MONGO_COLL, campo_nombre="busqueda"
            )
            if nombres:
                sel = st.selectbox("Documento Mongo", nombres)
                if st.button("🗄️ Cargar desde MongoDB"):
                    doc = obtener_documento_mongodb(
                        MONGO_URI, MONGO_DB, MONGO_COLL, sel, campo_nombre="busqueda"
                    )
                    st.session_state.contenido_json = json.dumps(doc, ensure_ascii=False).encode()
                    st.session_state.nombre_base = sel
                    st.rerun()
            else:
                st.warning("⚠️ Colección Mongo vacía.")
        except Exception as e:
            st.error(f"❌ Error MongoDB: {e}")

    # ---------- Parámetros del artículo ----------
    tipos = ["Informativo", "Ficha de producto", "Transaccional"]
    idiomas = ["Español", "Inglés", "Francés", "Alemán"]
    rangos = ["1000 - 2000", "2000 - 3000", "3000 - 4000", "4000 - 5000"]

    col1, col2, col3 = st.columns(3)
    with col1:
        tipo_articulo = st.selectbox("Tipo", tipos, index=0)
    with col2:
        idioma = st.selectbox("Idioma", idiomas, index=0)
    with col3:
        rango_palabras = st.selectbox("Rango palabras", rangos, index=0)

    tono   = st.selectbox("Tono", ["Neutro profesional", "Persuasivo", "Narrativo"], index=1)
    modelo = st.selectbox("Modelo GPT", MODELOS, index=0)

    # ---------- Parámetros avanzados ----------
    temperature        = st.slider("Temperature",       0.0, 1.5, 1.0, 0.1)
    top_p              = st.slider("Top-p",             0.0, 1.0, 0.9, 0.05)
    frequency_penalty  = st.slider("Frecuencia",        0.0, 2.0, 0.7, 0.1)
    presence_penalty   = st.slider("Presencia",         0.0, 2.0, 1.0, 0.1)

    # ---------- Coste estimado ----------
    tok_in  = (len(st.session_state.contenido_json or b"")) // 4
    max_w   = int(rango_palabras.split(" - ")[1])
    tok_out = int(max_w * 1.4)
    c_in, c_out = estimar_coste(modelo, tok_in, tok_out)
    st.info(f"Coste estimado → entrada ${c_in:.3f} + salida ${c_out:.3f} ≈ ${c_in+c_out:.3f}")

    # ---------- Prompt ----------
    palabra_clave = st.text_input("Palabra clave principal", st.session_state.get("palabra_clave", ""))
    prompt_extra  = generar_prompt_extra(palabra_clave, idioma, tipo_articulo, rango_palabras, tono)
    prompt_final  = st.text_area("Prompt para OpenAI", prompt_extra, height=300)

    # ---------- Generar ----------
    if st.button("🚀 Generar artículo") and palabra_clave:
        client   = get_openai_client()
        contexto = ""
        if st.session_state.contenido_json:
            contexto = "\n\nContexto JSON:\n" + st.session_state.contenido_json.decode(errors="ignore")
        with st.spinner("Llamando a OpenAI …"):
            try:
                resp = client.chat.completions.create(
                    model   = modelo,
                    messages=[{"role": "user", "content": prompt_final + contexto}],
                    temperature       = temperature,
                    top_p             = top_p,
                    frequency_penalty = frequency_penalty,
                    presence_penalty  = presence_penalty,
                    max_tokens        = tok_out,
                )
                contenido = resp.choices[0].message.content.strip()
                st.session_state.maestro_articulo = {
                    "fecha": datetime.utcnow().isoformat(),
                    "modelo": modelo,
                    "tipo": tipo_articulo,
                    "idioma": idioma,
                    "tono": tono,
                    "rango": rango_palabras,
                    "keyword": palabra_clave,
                    "json_origen": st.session_state.get("nombre_base"),
                    "contenido": contenido,
                }
            except Exception as e:
                st.error(f"❌ Error OpenAI: {e}")

    # ---------- Mostrar / Exportar ----------
    if st.session_state.get("maestro_articulo"):
        art = st.session_state.maestro_articulo
        st.markdown("## Artículo generado")
        st.write(art["contenido"])

        data_bytes = json.dumps(art, ensure_ascii=False, indent=2).encode()

        col_dl, col_drive, col_save = st.columns(3)
        with col_dl:
            st.download_button(
                "⬇️ Descargar JSON",
                data=data_bytes,
                file_name="articulo_seo.json",
                mime="application/json",
            )
        with col_drive:
            if st.button("☁️ Subir a Drive"):
                if "proyecto_id" not in st.session_state:
                    st.error("❌ No se ha seleccionado un proyecto.")
                else:
                    carpeta_posts = obtener_o_crear_subcarpeta(
                        "posts automaticos", st.session_state.proyecto_id
                    )
                    enlace = subir_json_a_drive("articulo_seo.json", data_bytes, carpeta_posts)
                    if enlace:
                        st.success(f"✅ Archivo subido: [Ver en Drive]({enlace})")
                    else:
                        st.error("❌ Error al subir archivo a Drive.")
        with col_save:
            if st.button("💾 Guardar en MongoDB"):
                try:
                    _id = subir_a_mongodb(
                        art, db_name=MONGO_DB,
                        collection_name=MONGO_COLL_OUTPUT,
                        uri=MONGO_URI,
                    )
                    st.success(f"✅ Guardado en MongoDB con id {_id}")
                except Exception as e:
                    st.error(f"❌ Error al guardar en MongoDB: {e}")
