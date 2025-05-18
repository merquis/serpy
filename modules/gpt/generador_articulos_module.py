import streamlit as st
import json
import openai
from slugify import slugify

# ── utilidades Google Drive ─────────────────────────────────────────
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    subir_json_a_drive,
    obtener_o_crear_subcarpeta,
)

# ── utilidades MongoDB ── (para cargar JSON de contexto) ────────────
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


def obtener_rango_legible(rango: str) -> str:
    partes = rango.split(" - ")
    if len(partes) == 2:
        return f"entre {partes[0]} y {partes[1]} palabras"
    return rango


def generar_prompt_esquema(
    palabra_clave: str,
    idioma: str,
    tipo: str,
    incluir_texto: bool,
    incluir_slugs: bool,
) -> str:
    """Construye el prompt principal para OpenAI."""

    extra = []
    if incluir_texto:
        extra.append("Redacta un texto SEO optimizado bajo cada encabezado.")
    if incluir_slugs:
        extra.append(
            "Devuelve un campo 'slug' compatible con URL, basado en el título, en minúsculas, sin tildes ni caracteres especiales."
        )

    return f"""
Eres un experto en SEO, IA y arquitectura de contenidos. Tu objetivo es diseñar una estructura H1‑H2‑H3 que posicione en el top‑5 de Google España para la keyword «{palabra_clave}».

Instrucciones:
1. Analiza las cabeceras y temas comunes de los principales competidores.
2. Propón un árbol JSON donde cada nodo incluya:  
   • title → el texto del encabezado (sin número).  
   • level → h1 | h2 | h3.  
   {'• slug → string URL‑friendly.' if incluir_slugs else ''}
3. Sigue esta jerarquía estricta (un único H1, varios H2, cada H2 puede contener H3).
4. Ordena los nodos para cubrir todas las intenciones de búsqueda.
5. Usa un lenguaje persuasivo y claro.
{''.join(extra)}
6. Responde exclusivamente con el JSON.
""".strip()


def estimar_coste(modelo: str, tokens_in: int, tokens_out: int):
    precios = {
        "gpt-4.1-mini-2025-04-14": (0.0004, 0.0016),
        "gpt-4.1-2025-04-14": (0.0020, 0.0080),
        "chatgpt-4o-latest": (0.00375, 0.0150),
        "o3-2025-04-16": (0.0100, 0.0400),
        "o3-mini-2025-04-16": (0.0011, 0.0044),
    }
    entrada, salida = precios.get(modelo, (0, 0))
    return (tokens_in / 1000) * entrada, (tokens_out / 1000) * salida


# ═══════════════════════════════════════════════════════════════════
# interfaz principal
# ═══════════════════════════════════════════════════════════════════

def render_generador_articulos():
    st.title("📚 Generador Maestro de Artículos / Esquemas SEO")

    # Estado global mínimo ----------------------------------------------------
    st.session_state.setdefault("resultado_ai", None)
    st.session_state.setdefault("contenido_json", None)
    st.session_state.setdefault("palabra_clave", "")

    # ───── fuente JSON opcional ─────────────────────────────────────────────
    fuente = st.radio(
        "Fuente del archivo JSON (opcional):",
        ["Ninguno", "Desde ordenador", "Desde Drive", "Desde MongoDB"],
        horizontal=True,
        index=1,
    )

    if fuente == "Desde ordenador":
        archivo = st.file_uploader("Sube un JSON", type="json")
        if archivo:
            st.session_state.contenido_json = archivo.read()
            st.session_state["nombre_base"] = archivo.name
            try:
                st.session_state.palabra_clave = json.loads(
                    st.session_state.contenido_json.decode("utf-8")
                ).get("busqueda", "")
            except Exception:
                pass
            st.rerun()

    elif fuente == "Desde Drive":
        if "proyecto_id" not in st.session_state or not st.session_state.proyecto_id:
            st.warning("Selecciona un proyecto en la barra lateral.")
        else:
            carpeta_id = obtener_o_crear_subcarpeta(
                "scraper etiquetas google", st.session_state.proyecto_id
            )
            archivos = listar_archivos_en_carpeta(carpeta_id)
            if archivos:
                sel = st.selectbox("Selecciona archivo:", list(archivos.keys()))
                if st.button("📥 Cargar JSON"):
                    st.session_state.contenido_json = obtener_contenido_archivo_drive(
                        archivos[sel]
                    )
                    try:
                        data = json.loads(
                            st.session_state.contenido_json.decode("utf-8")
                        )
                        st.session_state.palabra_clave = data.get("busqueda", "")
                    except Exception:
                        pass
                    st.rerun()
            else:
                st.info("No hay archivos JSON en este proyecto.")

    elif fuente == "Desde MongoDB":
        docs = obtener_documentos_mongodb(
            MONGO_URI, MONGO_DB, MONGO_COLL, campo_nombre="busqueda"
        )
        if docs:
            sel = st.selectbox("Documento:", docs)
            if st.button("📥 Cargar JSON"):
                doc = obtener_documento_mongodb(
                    MONGO_URI, MONGO_DB, MONGO_COLL, sel, campo_nombre="busqueda"
                )
                st.session_state.contenido_json = json.dumps(doc, ensure_ascii=False).encode()
                st.session_state.palabra_clave = doc.get("busqueda", "")
                st.session_state["nombre_base"] = sel
                st.rerun()
        else:
            st.info("No se encontraron documentos en MongoDB.")

    # ───── parámetros principales ──────────────────────────────────────────
    st.markdown("---")
    st.subheader("⚙️ Parámetros del generador")

    palabra_clave = st.text_input(
        "Keyword principal", value=st.session_state.palabra_clave, key="kw_input"
    )

    idioma = st.selectbox("Idioma", ["Español", "Inglés", "Francés", "Alemán"], index=0)
    tipo_articulo = st.selectbox("Tipo de contenido", ["Informativo", "Transaccional", "Ficha de producto"], index=0)

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
        chk_esquema = st.checkbox("📑 Generar esquema (Hn)", value=True)
    with col2:
        chk_textos = st.checkbox("✍️ Rellenar textos", value=False)
    with col3:
        chk_slugs = st.checkbox("🔗 Generar slugs", value=True)

    temperature = st.slider("Creatividad (temperature)", 0.0, 1.5, 1.0, 0.1)

    # ───── botón principal ────────────────────────────────────────────────
    if st.button("🚀 Ejecutar IA"):
        if not chk_esquema:
            st.error("Debes seleccionar al menos 'Generar esquema'.")
            st.stop()

        prompt = generar_prompt_esquema(
            palabra_clave, idioma, tipo_articulo, chk_textos, chk_slugs
        )

        contexto = ""
        if st.session_state.contenido_json:
            try:
                contexto = "\n\nJSON de referencia:\n" + json.dumps(
                    json.loads(st.session_state.contenido_json.decode("utf-8")),
                    ensure_ascii=False,
                    indent=2,
                )
            except Exception:
                st.warning("El JSON de entrada no es válido; se ignorará como contexto.")

        prompt_final = prompt + contexto
        client = get_openai_client()

        with st.spinner("Esperando respuesta de OpenAI..."):
            try:
                tokens_in = len(prompt_final) // 4
                tokens_out = 2000 if chk_textos else 800
                resp = client.chat.completions.create(
                    model=modelo,
                    messages=[
                        {
                            "role": "system",
                            "content": "Eres un experto en SEO y redacción.",
                        },
                        {"role": "user", "content": prompt_final.strip()},
                    ],
                    temperature=temperature,
                    max_tokens=tokens_out,
                )
                raw_json = resp.choices[0].message.content.strip()
                try:
                    esquema = json.loads(raw_json)
                except Exception:
                    st.error("La IA no devolvió un JSON válido. Respuesta cruda mostrada.")
                    st.code(raw_json)
                    st.stop()

                # Si no hay slugs y el usuario los quiere, generarlos localmente
                if chk_slugs and "slug" not in str(esquema):
                    def _add_slug(node):
                        node["slug"] = slugify(node["title"])
                        for child in node.get("children", []):
                            _add_slug(child)
                    _add_slug(esquema)

                st.session_state.resultado_ai = esquema
                st.success("✅ Generación completada")
            except Exception as e:
                st.error(f"❌ Error: {e}")
                st.stop()

    # ───── mostrar resultado + acciones extra ────────────────────────────
    if st.session_state.resultado_ai is not None:
        st.markdown("### Resultado JSON")
        st.code(json.dumps(st.session_state.resultado_ai, ensure_ascii=False, indent=2))

        # Exportar
        col_a, col_b, col_c = st.columns(3)
        export_bytes = json.dumps(
            st.session_state.resultado_ai, ensure_ascii=False, indent=2
        ).encode("utf-8")

        with col_a:
            st.download_button(
                "💾 Descargar JSON",
                data=export_bytes,
                file_name="esquema_seo.json",
                mime="application/json",
            )
        with col_b:
            if st.button("☁️ Subir a Drive"):
                if "proyecto_id" not in st.session_state or not st.session_state.proyecto_id:
                    st.error("No hay proyecto activo.")
                else:
                    carpeta = obtener_o_crear_subcarpeta(
                        "posts automaticos", st.session_state.proyecto_id
                    )
                    link = subir_json_a_drive("esquema_seo.json", export_bytes, carpeta)
                    if link:
                        st.success(f"Subido: [Abrir]({link})")

        # Rellenar textos posteriormente -----------------------------------
        if not chk_textos:
            st.markdown("---")
            st.markdown(
                "### ¿Quieres ahora rellenar el esquema con textos? Marca la opción y vuelve a ejecutar."
            )
