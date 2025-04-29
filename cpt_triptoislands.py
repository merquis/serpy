import streamlit as st
import requests
import pandas as pd

# Módulo para cargar y mostrar Custom Post Types (CPT) desde un sitio WordPress

# Configuración de la conexión en la barra lateral
def render_sidebar():
    st.sidebar.header("🔧 Opciones de Relaciones CPT")
    st.sidebar.info("Configura la conexión a tu sitio WordPress")
    site_url = st.sidebar.text_input("🌐 URL de tu sitio WordPress", value="https://tu-sitio.com")
    post_type = st.sidebar.text_input("📄 Custom Post Type (slug)", value="tu_cpt")
    per_page = st.sidebar.number_input("🔢 Número de items a traer", min_value=1, max_value=100, value=10)
    return site_url, post_type, per_page

# Función principal de renderizado en la zona principal
def render():
    st.title("🔗 Relaciones CPT - TripToIslands")
    site_url, post_type, per_page = render_sidebar()

    if st.button("Cargar CPT"):
        with st.spinner(f"Obteniendo '{post_type}' desde {site_url}..."):
            try:
                api_endpoint = f"{site_url.rstrip('/')}/wp-json/wp/v2/{post_type}?per_page={per_page}"
                response = requests.get(api_endpoint, timeout=10)
                response.raise_for_status()
                items = response.json()

                if not items:
                    st.warning(f"No se encontraron items para el CPT '{post_type}'.")
                    return

                # Normalizar JSON en un DataFrame
                df = pd.json_normalize(items)

                st.success(f"Cargados {len(items)} items de '{post_type}' exitosamente.")
                st.dataframe(df)

            except requests.exceptions.RequestException as err:
                st.error(f"Error al consultar la API de WordPress: {err}")
            except Exception as e:
                st.error(f"Error inesperado: {e}")
