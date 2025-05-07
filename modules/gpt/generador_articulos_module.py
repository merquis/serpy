import streamlit as st
import openai
import json
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    subir_json_a_drive,
    obtener_o_crear_subcarpeta
)

def obtener_rango_legible(rango):
    partes = rango.split(" - ")
    if len(partes) == 2:
        return f"entre {partes[0]} y {partes[1]} palabras"
    return rango

def generar_prompt_extra(palabra_clave, idioma, tipo_articulo, rango):
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

✍️ Detalles de redacción:
🔢 Longitud: {obtener_rango_legible(rango)}
🌍 Idioma: {idioma}
📄 Tipo de artículo: {tipo_articulo}
🗂️ Formato: Utiliza subtítulos claros (H2 y H3), listas, introducción persuasiva y conclusión útil.
📈 Objetivo: Posicionarse en Google para la keyword \"{palabra_clave}\".
🚫 No menciones que eres una IA ni expliques que estás generando un texto.
✅ Hazlo como si fueras un redactor profesional experto en turismo y SEO.
🧩 El 30% del contenido debe ser cogido del propio JSON y parafraseado para que no se detecte como contenido duplicado.
🧱 El 85% de los párrafos deben tener más de 150 palabras.
contexto = f"\n\n📦 JSON de referencia:\n```json\n{json.dumps(datos, ensure_ascii=False, indent=2)}\n```"

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

    openai.api_key = st.secrets["openai"]["api_key"]

    st.session_state.setdefault("maestro_articulo", None)
    st.session_state.setdefault("palabra_clave", "")
    st.session_state.setdefault("contenido_json", None)
    st.session_state.setdefault("idioma_detectado", None)
    st.session_state.setdefault("tipo_detectado", None)
    st.session_state.setdefault("mensaje_busqueda", "")
    st.session_state.setdefault("prompt_extra_manual", "")

    if st.session_state.mensaje_busqueda:
        st.markdown(f"🔍 **Palabra clave detectada**: `{st.session_state.mensaje_busqueda}`")

    fuente = st.radio("📂 Fuente del archivo JSON (opcional):",
                      ["Ninguno", "Desde ordenador", "Desde Drive"],
                      horizontal=True,
                      index=2)

    if fuente == "Desde ordenador":
        archivo = st.file_uploader("📁 Sube un archivo JSON", type="json")
        if archivo:
            st.session_state.contenido_json = archivo.read()
            st.session_state["nombre_base"] = archivo.name
            st.session_state.palabra_clave_fijada = False
            st.session_state.mensaje_busqueda = ""
            st.experimental_rerun()

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
                    crudo = (st.session_state.contenido_json.decode("utf-8")
                             if isinstance(st.session_state.contenido_json, bytes)
                             else st.session_state.contenido_json)
                    datos = json.loads(crudo)
                    st.session_state.palabra_clave = datos.get("busqueda", "")
                    st.session_state.idioma_detectado = datos.get("idioma", None)
                    st.session_state.tipo_detectado = datos.get("tipo_articulo", None)
                except Exception as e:
                    st.session_state.mensaje_busqueda = f"Error leyendo JSON: {e}"

                st.experimental_rerun()
        else:
            st.warning("⚠️ No se encontraron archivos JSON en este proyecto.")

    st.markdown("---")
    st.subheader("⚙️ Parámetros del artículo")

    tipos = ["Informativo", "Ficha de producto", "Transaccional"]
    idiomas = ["Español", "Inglés", "Francés", "Alemán"]
    rangos_palabras = [
        "1000 - 2000", "2000 - 3000", "3000 - 4000", "4000 - 5000",
        "5000 - 6000", "6000 - 7000", "7000 - 8000", "8000 - 9000", "9000 - 10000"
    ]
    modelos = [
        "gpt-3.5-turbo",
        "gpt-4o-mini",
        "gpt-4.1-nano",
        "gpt-4.1-mini",
        "gpt-4o",
        "gpt-4-turbo"
    ]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        tipo_articulo = st.selectbox("📄 Tipo de artículo", tipos,
            index=tipos.index(st.session_state.tipo_detectado) if st.session_state.tipo_detectado in tipos else 0)
    with col2:
        idioma = st.selectbox("🌍 Idioma", idiomas,
            index=idiomas.index(st.session_state.idioma_detectado) if st.session_state.idioma_detectado in idiomas else 0)
    with col3:
        rango_palabras = st.selectbox("🔢 Rango de palabras", rangos_palabras, index=3)
        st.session_state["rango_palabras"] = rango_palabras
    with col4:
        modelo = st.selectbox("🤖 Modelo GPT", modelos, index=0)

    caracteres_json = len(st.session_state.contenido_json.decode("utf-8")) if st.session_state.contenido_json else 0
    tokens_entrada = int(caracteres_json / 4)
    rango_split = rango_palabras.split(" - ")
    salida_palabras = int(sum(map(int, rango_split)) / 2)
    tokens_salida = int(salida_palabras * 1.4)
    costo_in, costo_out = estimar_coste(modelo, tokens_entrada, tokens_salida)

    st.markdown(f"""
**💰 Estimación de coste:**
- Entrada estimada: ~{tokens_entrada:,} tokens → ${costo_in:.2f}
- Salida estimada: ~{salida_palabras:,} palabras (~{tokens_salida:,} tokens) → ${costo_out:.2f}
- **Total estimado:** ${costo_in + costo_out:.2f}
""")

    st.session_state.setdefault("palabra_clave_input", st.session_state.palabra_clave)
    palabra_clave = st.text_area("🔑 Palabra clave principal", value=st.session_state.palabra_clave_input,
                                 height=80, key="palabra_clave_input")
    st.session_state.palabra_clave = palabra_clave

    prompt_extra_autogenerado = generar_prompt_extra(palabra_clave, idioma, tipo_articulo, rango_palabras)
    st.markdown("### 🧠 Instrucciones completas para el redactor GPT")
    prompt_extra_autogenerado = st.text_area("", value=prompt_extra_autogenerado, height=340)

    st.markdown("### ✍️ Instrucciones adicionales personalizadas")
    prompt_extra_manual = st.text_area("",
                                       value=st.session_state.get("prompt_extra_manual", ""),
                                       height=140, placeholder="Opcional: añade tono, estilo o detalles específicos.")
    st.session_state["prompt_extra_manual"] = prompt_extra_manual

    if st.button("✍️ Generar artículo con GPT") and palabra_clave.strip():
        contexto = ""
        if st.session_state.contenido_json:
            try:
                crudo = (st.session_state.contenido_json.decode("utf-8")
                         if isinstance(st.session_state.contenido_json, bytes)
                         else st.session_state.contenido_json)
                datos = json.loads(crudo)
                contexto = "\n\nEste es el contenido estructurado de referencia:\n" + \
                           json.dumps(datos, ensure_ascii=False, indent=2)
            except Exception as e:
                st.warning(f"⚠️ No se pudo usar el JSON: {e}")

        prompt_final = f"""
{prompt_extra_autogenerado.strip()}

{prompt_extra_manual.strip()}

{contexto}
"""

        with st.spinner("🧠 Generando artículo..."):
            try:
                resp = openai.ChatCompletion.create(
                    model=modelo,
                    messages=[
                        {"role": "system", "content": "Eres un redactor profesional experto en SEO."},
                        {"role": "user",    "content": prompt_final.strip()}
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
                st.session_state.maestro_articulo = {
                    "tipo": tipo_articulo,
                    "idioma": idioma,
                    "modelo": modelo,
                    "rango_palabras": rango_palabras,
                    "keyword": palabra_clave,
                    "prompt_extra": prompt_extra_manual,
                    "contenido": resp.choices[0].message.content.strip(),
                    "json_usado": st.session_state.get("nombre_base")
                }
            except Exception as e:
                st.error(f"❌ Error al generar el artículo: {e}")

    if st.session_state.maestro_articulo:
        st.markdown("### 📰 Artículo generado")
        st.write(st.session_state.maestro_articulo["contenido"])

        resultado_json = json.dumps(
            st.session_state.maestro_articulo,
            ensure_ascii=False,
            indent=2
        ).encode("utf-8")

        col = st.columns([1, 1])
        with col[0]:
            st.download_button(
                label="⬇️ Exportar JSON",
                data=resultado_json,
                file_name="articulo_seo.json",
                mime="application/json"
            )

        with col[1]:
            if st.button("☁️ Subir archivo a Google Drive", key="subir_drive_gpt"):
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
