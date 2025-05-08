# Refactor del módulo `generador_articulos_module.py` con máxima flexibilidad, control y claridad + subida a Drive y exportación completa

import streamlit as st
import openai
import json
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    subir_json_a_drive,
    obtener_o_crear_subcarpeta
)

def estimar_coste(modelo, tokens_entrada, tokens_salida):
    # Precios actualizados desde: https://platform.openai.com/docs/pricing
    precios = {
        "gpt-4o-mini": (0.0005, 0.0015),
        "gpt-4.1-nano": (0.0010, 0.0030),
        "gpt-4.1-mini": (0.0015, 0.0045),
        "gpt-4o": (0.0050, 0.0150),
        "gpt-4-turbo": (0.0100, 0.0300)
    }
    entrada_usd, salida_usd = precios.get(modelo, (0, 0))
    costo_entrada = tokens_entrada / 1000 * entrada_usd
    costo_salida = tokens_salida / 1000 * salida_usd
    return round(costo_entrada, 4), round(costo_salida, 4)

def generar_prompt_maestro(palabra_clave, idioma, tipo_articulo, rango, tono, extra_manual, datos_json):
    instrucciones = f"""
Eres un redactor SEO profesional.

Tu objetivo es redactar un artículo de tipo "{tipo_articulo}" en idioma "{idioma}" para la palabra clave "{palabra_clave}".

Tono: {tono}
Rango de palabras: {rango}

Estructura esperada:
- Introducción
- H2 y H3 bien organizados
- Contenido basado en los datos estructurados JSON
- Parafrasear al menos el 30% del JSON
- Evitar frases genéricas
- Optimizado para SEO (listas, llamadas a la acción, etc.)

{extra_manual.strip()}

Este es el contenido estructurado en JSON:
{json.dumps(datos_json, ensure_ascii=False, indent=2)}
"""
    return instrucciones.strip()

def render_generador_articulos():
    st.title("🧠 Generador Maestro de Artículos SEO")

    openai.api_key = st.secrets["openai"]["api_key"]

    modelos = ["gpt-4o-mini", "gpt-4.1-nano", "gpt-4.1-mini", "gpt-4o", "gpt-4-turbo"]
    idiomas = ["Español", "Inglés", "Francés", "Alemán"]
    tipos = ["Informativo", "Ficha de producto", "Transaccional"]
    tonos = ["Neutro profesional", "Persuasivo", "Informal", "Inspirador", "Narrativo"]
    rangos = ["1000 - 2000", "2000 - 3000", "3000 - 4000", "4000 - 5000", "5000 - 6000"]

    st.session_state.setdefault("contenido_json", None)
    st.session_state.setdefault("nombre_json", None)

    with st.sidebar:
        st.markdown("### 📁 Cargar JSON")
        fuente = st.radio("Fuente del JSON", ["Ninguno", "Desde ordenador", "Desde Drive"], index=1)

        if fuente == "Desde ordenador":
            archivo = st.file_uploader("Sube un archivo JSON", type="json")
            if archivo:
                st.session_state.contenido_json = json.load(archivo)
                st.session_state.nombre_json = archivo.name

        elif fuente == "Desde Drive":
            if "proyecto_id" not in st.session_state:
                st.warning("Selecciona primero un proyecto en la barra lateral.")
            else:
                carpeta = obtener_o_crear_subcarpeta("scraper etiquetas google", st.session_state.proyecto_id)
                archivos = listar_archivos_en_carpeta(carpeta)
                if archivos:
                    seleccionado = st.selectbox("Selecciona archivo JSON:", list(archivos.keys()))
                    if st.button("📂 Cargar archivo"):
                        contenido = obtener_contenido_archivo_drive(archivos[seleccionado])
                        st.session_state.contenido_json = json.loads(contenido.decode("utf-8"))
                        st.session_state.nombre_json = seleccionado
                else:
                    st.info("No hay archivos disponibles.")

    st.markdown("---")
    st.subheader("⚙️ Parámetros del artículo")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        tipo = st.selectbox("📄 Tipo de artículo", tipos)
    with col2:
        idioma = st.selectbox("🌍 Idioma", idiomas)
    with col3:
        rango = st.selectbox("🔢 Rango de palabras", rangos)
    with col4:
        modelo = st.selectbox("🤖 Modelo GPT", modelos)

    tono = st.selectbox("🎙️ Tono del artículo", tonos, index=1)
    palabra_clave = st.text_area("🔑 Palabra clave principal", height=80)

    extra = st.text_area("📝 Instrucciones personalizadas (opcional)")

    st.markdown("### 🎛️ Parámetros avanzados")
    temp = st.slider("🔥 Temperature", 0.0, 1.5, 0.9)
    top_p = st.slider("📊 Top-p", 0.0, 1.0, 0.85)
    freq_penalty = st.slider("🔁 Penalización frecuencia", 0.0, 2.0, 0.5)
    pres_penalty = st.slider("🆕 Penalización presencia", 0.0, 2.0, 0.6)

    if st.button("✍️ Generar artículo (por bloques)") and palabra_clave.strip() and st.session_state.contenido_json:
        json_data = st.session_state.contenido_json
        bloques_generados = []

        for seccion in json_data.get("estructura", []):
            if "subsecciones" in seccion and seccion["subsecciones"]:
                for subseccion in seccion["subsecciones"]:
                    prompt = f"""
Eres un redactor SEO profesional.

Redacta solo el bloque para la subsección: {subseccion['h3']}.

Contenido base:
{subseccion['contenido']}

Tono: {tono}
Longitud esperada: 100-130 palabras.
No generes nada fuera del bloque solicitado.
"""
                    tokens_entrada = len(prompt) // 4
                    tokens_salida = 200
                    with st.spinner(f"✍️ Generando bloque: {subseccion['h3']}..."):
                        try:
                            resp = openai.ChatCompletion.create(
                                model=modelo,
                                messages=[
                                    {"role": "system", "content": "Eres un redactor SEO profesional."},
                                    {"role": "user", "content": prompt}
                                ],
                                temperature=temp,
                                top_p=top_p,
                                frequency_penalty=freq_penalty,
                                presence_penalty=pres_penalty,
                                max_tokens=tokens_salida
                            )
                            bloques_generados.append({
                                "seccion": seccion['h2'],
                                "subseccion": subseccion['h3'],
                                "contenido": resp.choices[0].message.content.strip()
                            })
                        except Exception as e:
                            bloques_generados.append({
                                "seccion": seccion['h2'],
                                "subseccion": subseccion['h3'],
                                "contenido": f"❌ Error: {e}"
                            })
            if "hoteles" in seccion:
                for hotel in seccion["hoteles"]:
                    prompt = f"""
Eres un redactor SEO profesional.

Redacta solo el bloque para el hotel: {hotel['h3']}.

Usa exclusivamente los siguientes datos:
{json.dumps(hotel['datos'], ensure_ascii=False, indent=2)}

Tono: {tono}
Longitud esperada: 130-150 palabras.
Finaliza con una llamada a la acción que incluya el enlace afiliado.
No generes nada fuera del bloque solicitado.
"""
                    tokens_entrada = len(prompt) // 4
                    tokens_salida = 200
                    with st.spinner(f"✍️ Generando bloque: {hotel['h3']}..."):
                        try:
                            resp = openai.ChatCompletion.create(
                                model=modelo,
                                messages=[
                                    {"role": "system", "content": "Eres un redactor SEO profesional."},
                                    {"role": "user", "content": prompt}
                                ],
                                temperature=temp,
                                top_p=top_p,
                                frequency_penalty=freq_penalty,
                                presence_penalty=pres_penalty,
                                max_tokens=tokens_salida
                            )
                            bloques_generados.append({
                                "hotel": hotel['h3'],
                                "contenido": resp.choices[0].message.content.strip()
                            })
                        except Exception as e:
                            bloques_generados.append({
                                "hotel": hotel['h3'],
                                "contenido": f"❌ Error: {e}"
                            })
        tokens_entrada = len(prompt) // 4
        tokens_salida = int(rango.split(" - ")[1]) * 1.4
        costo_in, costo_out = estimar_coste(modelo, tokens_entrada, tokens_salida)

        with st.expander("📊 Resumen de coste estimado", expanded=True):
            st.markdown(f"**🧮 Tokens de entrada:** ~{tokens_entrada:,} → **${costo_in:.4f}**")
            st.markdown(f"**🧾 Tokens de salida (máx.):** ~{tokens_salida:,} → **${costo_out:.4f}**")
            st.markdown(f"**💵 Total estimado:** **${costo_in + costo_out:.4f} USD** para este artículo con el modelo **{modelo}**")

        with st.spinner("Generando artículo..."):
            try:
                resp = openai.ChatCompletion.create(
                    model=modelo,
                    messages=[
                        {"role": "system", "content": "Eres un redactor SEO profesional."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temp,
                    top_p=top_p,
                    frequency_penalty=freq_penalty,
                    presence_penalty=pres_penalty,
                    max_tokens=int(tokens_salida)
                )
                resultado = resp.choices[0].message.content.strip()
                st.markdown("### 🧱 Bloques generados")
        for bloque in bloques_generados:
            st.markdown(f"#### {bloque['hotel']}")
            st.write(bloque['contenido'])
                json_final = {
    "modelo": modelo,
    "rango_palabras": rango,
    "tipo": tipo,
    "tono": tono,
    "idioma": idioma,
    "keyword": palabra_clave,
    "json_origen": st.session_state.nombre_json,
    "bloques": bloques_generados,
    "prompt_usado": prompt
}
                st.download_button("⬇️ Descargar artículo", json.dumps(json_final, ensure_ascii=False, indent=2), file_name="articulo_generado.json")

                if st.button("☁️ Subir a Google Drive"):
                    if "proyecto_id" in st.session_state:
                        subcarpeta = obtener_o_crear_subcarpeta("posts automaticos", st.session_state.proyecto_id)
                        enlace = subir_json_a_drive("articulo_generado.json", json.dumps(json_final).encode("utf-8"), subcarpeta)
                        if enlace:
                            st.success(f"✅ Archivo subido: [Ver en Drive]({enlace})")
                        else:
                            st.error("❌ Error al subir el archivo a Drive.")
                    else:
                        st.error("❌ Proyecto no definido. No se puede subir a Drive.")

            except Exception as e:
                st.error(f"❌ Error: {e}")
