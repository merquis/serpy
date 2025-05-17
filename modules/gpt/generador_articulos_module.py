import streamlit as st
import json
import openai
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    subir_json_a_drive,
    obtener_o_crear_subcarpeta
)
from modules.utils.mongo_utils import (
    obtener_documentos_mongodb,
    obtener_documento_mongodb
)

def get_openai_client():
    return openai.Client(api_key=st.secrets["openai"]["api_key"])

def obtener_rango_legible(rango):
    partes = rango.split(" - ")
    if len(partes) == 2:
        return f"entre {partes[0]} y {partes[1]} palabras"
    return rango

def generar_prompt_extra(palabra_clave, idioma, tipo_articulo, rango, tono):
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

def estimar_coste(modelo, tokens_entrada, tokens_salida):
    precios = {
        "gpt-3.5-turbo": (0.0005, 0.0015),
        "gpt-4o-mini": (0.0005, 0.0015),
        "gpt-4.1-nano": (0.0010, 0.0030),
        "gpt-4.1-mini": (0.0015, 0.0045),
        "gpt-4o": (0.0050, 0.0150),
        "gpt-4-turbo": (0.0100, 0.0300)
    }
    entrada_usd, salida_usd = precios.get(modelo, (0, 0))
    return tokens_entrada / 1000 * entrada_usd, tokens_salida / 1000 * salida_usd

def render_generador_articulos():
    st.session_state["_called_script"] = "generador_articulos"
    st.title("🧠 Generador Maestro de Artículos SEO")
    st.markdown("Crea artículos SEO potentes con o sin contexto JSON. Tú tienes el control.")

    client = get_openai_client()

    st.session_state.setdefault("maestro_articulo", None)
    st.session_state.setdefault("palabra_clave", "")
    st.session_state.setdefault("contenido_json", None)
    st.session_state.setdefault("idioma_detectado", None)
    st.session_state.setdefault("tipo_detectado", None)
    st.session_state.setdefault("mensaje_busqueda", "")
    st.session_state.setdefault("prompt_extra_manual", "")

    fuente = st.radio("Fuente del archivo JSON (opcional):", ["Ninguno", "Desde ordenador", "Desde Drive", "Desde MongoDB"], horizontal=True, index=2)

    if fuente == "Desde ordenador":
        archivo = st.file_uploader("Sube un archivo JSON", type="json")
        if archivo:
            st.session_state.contenido_json = archivo.read()
            st.session_state["nombre_base"] = archivo.name
            st.session_state.palabra_clave_fijada = False
            st.session_state.mensaje_busqueda = ""
            st.rerun()

    elif fuente == "Desde Drive":
        if "proyecto_id" not in st.session_state:
            st.error("❌ Selecciona primero un proyecto en la barra lateral.")
            return
        carpeta_id = obtener_o_crear_subcarpeta("scraper etiquetas google", st.session_state.proyecto_id)
        archivos = listar_archivos_en_carpeta(carpeta_id)

        if archivos:
            elegido = st.selectbox("Selecciona archivo JSON:", list(archivos.keys()))
            if st.button("📅 Cargar desde Drive"):
                st.session_state.contenido_json = obtener_contenido_archivo_drive(archivos[elegido])
                st.session_state["nombre_base"] = elegido
                st.session_state.palabra_clave_fijada = False
                try:
                    crudo = st.session_state.contenido_json.decode("utf-8") if isinstance(st.session_state.contenido_json, bytes) else st.session_state.contenido_json
                    datos = json.loads(crudo)
                    st.session_state.palabra_clave = datos.get("busqueda", "")
                    st.session_state.idioma_detectado = datos.get("idioma", None)
                    st.session_state.tipo_detectado = datos.get("tipo_articulo", None)
                except Exception as e:
                    st.session_state.mensaje_busqueda = f"Error leyendo JSON: {e}"
                st.rerun()
        else:
            st.warning("⚠️ No se encontraron archivos JSON en este proyecto.")

    elif fuente == "Desde MongoDB":
        try:
            uri = "mongodb://serpy:esperanza85@serpy_mongodb:27017/?authSource=admin"
            db = "serpy"
            collection = "hoteles"

            documentos = obtener_documentos_mongodb(uri, db, collection, campo_nombre="nombre")

            if documentos:
                elegido = st.selectbox("Selecciona documento JSON desde MongoDB:", documentos)
                if st.button("📤 Cargar desde MongoDB"):
                    doc = obtener_documento_mongodb(uri, db, collection, elegido, campo_nombre="nombre")
                    if doc:
                        crudo = json.dumps(doc, ensure_ascii=False)
                        st.session_state.contenido_json = crudo.encode("utf-8")
                        st.session_state["nombre_base"] = elegido
                        st.session_state.palabra_clave_fijada = False
                        st.session_state.palabra_clave = doc.get("busqueda", "")
                        st.session_state.idioma_detectado = doc.get("idioma", None)
                        st.session_state.tipo_detectado = doc.get("tipo_articulo", None)
                        st.rerun()
                    else:
                        st.warning("⚠️ No se encontró el documento.")
            else:
                st.warning("⚠️ No hay documentos disponibles en MongoDB.")
        except Exception as e:
            st.error(f"❌ Error accediendo a MongoDB: {e}")

    st.markdown("---")
    tipos = ["Informativo", "Ficha de producto", "Transaccional"]
idiomas = ["Español", "Inglés", "Francés", "Alemán"]
rangos_palabras = ["1000 - 2000", "2000 - 3000", "3000 - 4000", "4000 - 5000", "5000 - 6000", "6000 - 7000", "7000 - 8000", "8000 - 9000", "9000 - 10000"]
modelos = ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4.1-nano", "gpt-4.1-mini", "gpt-4o", "gpt-4-turbo"]

col1, col2, col3, col4 = st.columns(4)
with col1:
    tipo_articulo = st.selectbox("Tipo de artículo", tipos, index=tipos.index(st.session_state.tipo_detectado) if st.session_state.tipo_detectado in tipos else 0)
    recomendaciones_tono = {"Informativo": "Persuasivo", "Ficha de producto": "Persuasivo", "Transaccional": "Persuasivo o Inspirador"}
    tono_sugerido = recomendaciones_tono.get(tipo_articulo, "Persuasivo")
    st.markdown(f"💡 Tono recomendado: {tono_sugerido}")
    tonos = ["Neutro profesional", "Persuasivo", "Informal", "Inspirador", "Narrativo"]
    tono = st.selectbox("Tono del artículo", tonos, index=1 if tono_sugerido.startswith("Persuasivo") else 0)
    st.session_state["tono_articulo"] = tono
with col2:
    idioma = st.selectbox("Idioma", idiomas, index=idiomas.index(st.session_state.idioma_detectado) if st.session_state.idioma_detectado in idiomas else 0)
with col3:
    rango_palabras = st.selectbox("Rango de palabras", rangos_palabras, index=3)
    st.session_state["rango_palabras"] = rango_palabras
with col4:
    modelo = st.selectbox("Modelo GPT", modelos, index=0)

st.markdown("### Parámetros avanzados del modelo")
col1, col2 = st.columns(2)
with col1:
    temperature = st.slider("Temperature (creatividad)", 0.0, 1.5, 1.2, 0.1)
    top_p = st.slider("Top-p (variedad del muestreo)", 0.0, 1.0, 0.9, 0.05)
with col2:
    frequency_penalty = st.slider("Penalización por frecuencia", 0.0, 2.0, 0.7, 0.1)
    presence_penalty = st.slider("Penalización por presencia", 0.0, 2.0, 1.0, 0.1)

caracteres_json = len(st.session_state.contenido_json.decode("utf-8")) if st.session_state.contenido_json else 0
tokens_entrada = int(caracteres_json / 4)
palabras_max = int(rango_palabras.split(" - ")[1])
tokens_salida = int(palabras_max * 1.4)
costo_in, costo_out = estimar_coste(modelo, tokens_entrada, tokens_salida)

st.markdown(f"**Estimación de coste:** Entrada: ~{tokens_entrada:,} tokens → ${costo_in:.2f}, Salida: hasta {palabras_max:,} palabras (~{tokens_salida:,} tokens) → ${costo_out:.2f}, Total: ${costo_in + costo_out:.2f}")

palabra_clave = st.text_area("Palabra clave principal", value=st.session_state.get("palabra_clave", ""), height=80)
st.session_state.palabra_clave = palabra_clave

prompt_extra_autogenerado = generar_prompt_extra(palabra_clave, idioma, tipo_articulo, rango_palabras, tono)
st.markdown("### Instrucciones completas para GPT")
prompt_extra_autogenerado = st.text_area("", value=prompt_extra_autogenerado, height=340)

st.markdown("### Instrucciones adicionales personalizadas")
prompt_extra_manual = st.text_area("", value=st.session_state.get("prompt_extra_manual", ""), height=140).strip()
st.session_state["prompt_extra_manual"] = prompt_extra_manual

if st.button("Generar artículo con GPT") and palabra_clave.strip():
    contexto = ""
    if st.session_state.contenido_json:
        try:
            crudo = st.session_state.contenido_json.decode("utf-8") if isinstance(st.session_state.contenido_json, bytes) else st.session_state.contenido_json
            datos = json.loads(crudo)
            contexto = "

Este es el contenido estructurado de referencia:
" + json.dumps(datos, ensure_ascii=False, indent=2)
        except Exception as e:
            st.warning(f"⚠️ No se pudo usar el JSON: {e}")

    prompt_final = f"{prompt_extra_autogenerado.strip()}

{prompt_extra_manual.strip()}

{contexto}"

    with st.spinner("Generando artículo..."):
        try:
            resp = client.chat.completions.create(
                model=modelo,
                messages=[
                    {"role": "system", "content": "Eres un redactor profesional experto en SEO."},
                    {"role": "user", "content": prompt_final.strip()}
                ],
                temperature=temperature,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                max_tokens=tokens_salida
            )
            st.session_state.maestro_articulo = {
                "tipo": tipo_articulo,
                "idioma": idioma,
                "modelo": modelo,
                "rango_palabras": rango_palabras,
                "tono": tono,
                "keyword": palabra_clave,
                "prompt_extra": prompt_extra_manual,
                "contenido": resp.choices[0].message.content.strip(),
                "json_usado": st.session_state.get("nombre_base")
            }
        except Exception as e:
            st.error(f"❌ Error al generar el artículo: {e}")

if st.session_state.maestro_articulo:
    st.markdown("### Artículo generado")
    st.write(st.session_state.maestro_articulo["contenido"])

    resultado_json = json.dumps(
        st.session_state.maestro_articulo,
        ensure_ascii=False,
        indent=2
    ).encode("utf-8")

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="⬇️ Exportar JSON",
            data=resultado_json,
            file_name="articulo_seo.json",
            mime="application/json"
        )
    with col2:
        if st.button("☁️ Subir a Google Drive", key="subir_drive_gpt"):
            if "proyecto_id" not in st.session_state:
                st.error("❌ No se ha seleccionado un proyecto.")
            else:
                subcarpeta = obtener_o_crear_subcarpeta("posts automaticos", st.session_state["proyecto_id"])
                if not subcarpeta:
                    st.error("❌ No se pudo acceder a la subcarpeta 'posts automaticos'.")
                    return
                enlace = subir_json_a_drive("articulo_seo.json", resultado_json, subcarpeta)
                if enlace:
                    st.success(f"✅ Archivo subido: [Ver en Drive]({enlace})")
                else:
                    st.error("❌ Error al subir archivo a Drive.")
