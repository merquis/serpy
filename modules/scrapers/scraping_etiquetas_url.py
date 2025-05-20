import json
import streamlit as st
import asyncio
from playwright.async_api import async_playwright
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    subir_json_a_drive,
    obtener_o_crear_subcarpeta
)
from modules.utils.scraper_tags_tree import scrape_tags_as_tree
from modules.utils.mongo_utils import subir_a_mongodb

def render_scraping_etiquetas_url():
    st.session_state["_called_script"] = "scraping_etiquetas_url"
    st.title("🧬 Extraer estructura jerárquica (h1 → h2 → h3) desde archivo JSON")
    st.markdown("### 📁 Sube un archivo JSON con URLs obtenidas de Google")

    fuente = st.radio("Selecciona fuente del archivo:", ["Desde Drive", "Desde ordenador"], horizontal=True, index=0)

    def procesar_json(crudo):
        try:
            if isinstance(crudo, bytes):
                crudo = crudo.decode("utf-8")
            return json.loads(crudo)
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {e}")
            return None

    if fuente == "Desde ordenador":
        archivo_subido = st.file_uploader("Sube archivo JSON", type="json")
        if archivo_subido:
            st.session_state["json_contenido"] = archivo_subido.read()
            st.session_state["json_nombre"] = archivo_subido.name
            st.session_state.pop("salida_json", None)

    else:
        if "proyecto_id" not in st.session_state:
            st.error("❌ Selecciona primero un proyecto en la barra lateral izquierda.")
            return

        carpeta_principal = st.session_state.proyecto_id
        subcarpeta_id = obtener_o_crear_subcarpeta("scraper urls google", carpeta_principal)
        if not subcarpeta_id:
            st.error("❌ No se pudo acceder a la subcarpeta scraper urls google.")
            return

        archivos_json = listar_archivos_en_carpeta(subcarpeta_id)
        if not archivos_json:
            st.warning("⚠️ No hay archivos JSON en esa subcarpeta.")
            return

        archivo_drive = st.selectbox("Selecciona un archivo de Drive", list(archivos_json.keys()))
        if st.button("📅 Cargar archivo de Drive"):
            st.session_state["json_contenido"] = obtener_contenido_archivo_drive(archivos_json[archivo_drive])
            st.session_state["json_nombre"] = archivo_drive
            st.session_state.pop("salida_json", None)

    if "json_contenido" in st.session_state and "salida_json" not in st.session_state:
        datos_json = procesar_json(st.session_state["json_contenido"])
        if not datos_json:
            return

        iterable = datos_json if isinstance(datos_json, list) else [datos_json]
        salidas = []

        async def procesar_urls_playwright(urls):
            resultados = []
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
                context = await browser.new_context(
                    ignore_https_errors=True,
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
                )
                page = await context.new_page()

                for url in urls:
                    with st.spinner(f"Analizando {url}..."):
                        try:
                            await page.goto(url, timeout=60000, wait_until="load")
                            await page.mouse.move(100, 100)
                            await page.keyboard.press("PageDown")
                            await page.wait_for_timeout(2000)
                            resultado = await scrape_tags_as_tree(url, browser)
                        except Exception as e:
                            resultado = {"url": url, "status_code": "error", "error": str(e)}
                        resultados.append(resultado)

                await page.close()
                await context.close()
                await browser.close()
            return resultados

        for entrada in iterable:
            if not isinstance(entrada, dict):
                continue

            contexto = {
                "busqueda": entrada.get("busqueda", ""),
                "idioma": entrada.get("idioma", ""),
                "region": entrada.get("region", ""),
                "dominio": entrada.get("dominio", ""),
                "url_busqueda": entrada.get("url_busqueda", "")
            }

            urls = []
            if "urls" in entrada:
                for item in entrada["urls"]:
                    if isinstance(item, str):
                        urls.append(item)
                    elif isinstance(item, dict) and "url" in item:
                        urls.append(item["url"])

            if "resultados" in entrada:
                for res in entrada["resultados"]:
                    if isinstance(res, dict) and "url" in res:
                        urls.append(res["url"])

            if not urls:
                continue

            resultados = asyncio.run(procesar_urls_playwright(urls))
            salidas.append({**contexto, "resultados": resultados})

        st.session_state["salida_json"] = salidas
        base = st.session_state.get("json_nombre", "etiquetas_jerarquicas.json")
        st.session_state["nombre_archivo_exportar"] = (
            base.replace(".json", "_ALL.json") if base.endswith(".json") else base + "_ALL.json"
        )

    if "salida_json" in st.session_state:
        salida = st.session_state["salida_json"]
        nombre_archivo = st.text_input("📄 Nombre para exportar el archivo JSON", value=st.session_state["nombre_archivo_exportar"])
        st.session_state["nombre_archivo_exportar"] = nombre_archivo

        col_export = st.columns([1, 1, 1])

        with col_export[0]:
            st.download_button(
                label="⬇️ Exportar JSON",
                data=json.dumps(salida, ensure_ascii=False, indent=2),
                file_name=nombre_archivo,
                mime="application/json"
            )

        with col_export[1]:
            if st.button("☁️ Subir archivo a Google Drive", key="subir_drive"):
                contenido_bytes = json.dumps(salida, ensure_ascii=False, indent=2).encode("utf-8")
                enlace = subir_json_a_drive(nombre_archivo, contenido_bytes, st.session_state["proyecto_id"])
                if enlace:
                    st.success(f"✅ Subido: [Ver en Drive]({enlace})")
                else:
                    st.error("❌ Error al subir archivo a Drive.")

        with col_export[2]:
            if st.button("📤 Subir JSON a MongoDB", key="subir_mongo"):
                try:
                    inserted_id = subir_a_mongodb(
                        salida,
                        db_name=st.secrets["mongodb"]["db"],
                        collection_name="hoteles",
                        uri=st.secrets["mongodb"]["uri"]
                    )

                    if isinstance(inserted_id, list):
                        ids_formateados = "\n".join([f"- `{_id}`" for _id in inserted_id])
                        st.success(f"✅ Subidos {len(inserted_id)} JSON(s) a MongoDB:\n\n{ids_formateados}")
                    else:
                        st.success(f"✅ JSON subido a MongoDB con ID:\n\n- `{inserted_id}`")

                except Exception as e:
                    st.error(f"❌ Error al subir a MongoDB: {e}")

        st.subheader("📦 Resultados estructurados")
        st.markdown("<div style='max-width: 100%; overflow-x: auto;'>", unsafe_allow_html=True)
        st.json(salida)
        st.markdown("</div>", unsafe_allow_html=True)
