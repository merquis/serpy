"""
Página de UI para Scraping de Google
"""
import streamlit as st
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from ui.components.common import Card, Alert, Button, LoadingSpinner, DataDisplay, SelectBox
from services.google_buscar_service import GoogleBuscarService
from services.google_extraer_datos_service import GoogleExtraerDatosService
from services.drive_service import DriveService
from services.embeddings_service import EmbeddingsService
from config import settings
from repositories.mongo_repository import MongoRepository

class GoogleBuscarPage:
    """Página para scraping de resultados de Google"""
    
    def __init__(self):
        self.scraping_service = GoogleBuscarService()
        self.tag_service = GoogleExtraerDatosService()
        self.drive_service = DriveService()
        self.embeddings_service = EmbeddingsService()
        # Importar la página de etiquetas para reutilizar su visualización
        from ui.pages.google_extraer_datos import GoogleExtraerDatosPage
        self.tag_page = GoogleExtraerDatosPage()
        # Importar la página del generador de artículos
        from ui.pages.article_generator import ArticleGeneratorPage
        self.article_page = ArticleGeneratorPage()
        self._init_session_state()
    
    def _init_session_state(self):
        """Inicializa el estado de la sesión"""
        if "query_input" not in st.session_state:
            st.session_state.query_input = ""
        if "scraping_results" not in st.session_state:
            st.session_state.scraping_results = []
        # Estados para las configuraciones
        if "num_results" not in st.session_state:
            st.session_state.num_results = 30
        if "language_option" not in st.session_state:
            st.session_state.language_option = "Español (España)"
        if "domain_option" not in st.session_state:
            st.session_state.domain_option = "España (.es)"
        if "extract_tags" not in st.session_state:
            st.session_state.extract_tags = True
        if "semantic_analysis" not in st.session_state:
            st.session_state.semantic_analysis = True
        if "generate_article" not in st.session_state:
            st.session_state.generate_article = True
    
    def render(self):
        """Renderiza la página completa"""
        st.title(f"{settings.icons['search']} Scraping de URLs desde Google")
        
        # Sección de configuración
        self._render_configuration_section()
        
        # Botones de acción
        self._render_action_buttons()
        
        # Mostrar resultados si existen
        if st.session_state.scraping_results:
            self._render_results_section()
    
    def _render_configuration_section(self):
        """Renderiza la sección de configuración"""
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.session_state.query_input = st.text_area(
                "📝 Escribe una o más búsquedas separadas por coma o enter",
                st.session_state.query_input,
                height=400,
                placeholder="ej: mejores hoteles Madrid, restaurantes Barcelona"
            )
        
        with col2:
            # Número de resultados
            num_results = st.selectbox(
                "📄 Nº resultados",
                options=list(range(10, 101, 10)),
                index=list(range(10, 101, 10)).index(st.session_state.num_results)
            )
            st.session_state.num_results = num_results
            
            # Idioma y región
            language_option = st.selectbox(
                "🌐 Idioma y región",
                options=list(settings.search_languages.keys()),
                index=list(settings.search_languages.keys()).index(st.session_state.language_option)
            )
            st.session_state.language_option = language_option
            
            # Dominio de Google
            domain_option = st.selectbox(
                "🧭 Dominio de Google",
                options=list(settings.google_domains.keys()),
                index=list(settings.google_domains.keys()).index(st.session_state.domain_option)
            )
            st.session_state.domain_option = domain_option
    
    def _render_action_buttons(self):
        """Renderiza los botones de acción"""
        if st.session_state.scraping_results:
            # Verificar si se generaron artículos (ya están guardados en MongoDB)
            articles_generated = (isinstance(st.session_state.scraping_results, dict) and 
                               "generated_articles" in st.session_state.scraping_results)
            
            if articles_generated:
                # Solo mostrar botones de Buscar y Nueva Búsqueda cuando hay artículos generados
                col1, col2 = st.columns(2)
                
                with col1:
                    if Button.primary("Buscar", icon=config.ui.icons["search"]):
                        self._perform_search()
                
                with col2:
                    if Button.secondary("Nueva Búsqueda", icon=config.ui.icons["clean"]):
                        self._clear_search()
            else:
                # Mostrar todos los botones cuando NO hay artículos generados
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    if Button.primary("Buscar", icon=config.ui.icons["search"]):
                        self._perform_search()
                
                with col2:
                    if Button.secondary("Nueva Búsqueda", icon=config.ui.icons["clean"]):
                        self._clear_search()
                
                with col3:
                    if Button.secondary("Exportar JSON", icon=config.ui.icons["download"]):
                        self._export_json()
                
                with col4:
                    if Button.secondary("Exportar a MongoDB", icon="🧬"):
                        self._export_to_mongo()
                with col5:
                    if Button.secondary("Subir a Drive", icon=config.ui.icons["upload"]):
                        self._upload_to_drive()
        else:
            # Primera fila con el checkbox de extraer etiquetas
            extract_tags = st.checkbox(
                "🏷️ Extraer etiquetas HTML automáticamente",
                value=st.session_state.extract_tags,
                help="Extrae la estructura H1/H2/H3 de las URLs encontradas",
                key="extract_tags_checkbox"
            )
            
            # Segunda fila con los checkboxes dependientes
            if extract_tags:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Checkbox para análisis semántico
                    semantic_analysis = st.checkbox(
                        "📊 Ejecutar análisis semántico",
                        value=st.session_state.semantic_analysis,
                        help="Analiza semánticamente las etiquetas para crear un árbol SEO optimizado",
                        key="semantic_analysis_checkbox"
                    )
                
                with col2:
                    # Checkbox para generar artículo
                    generate_article = st.checkbox(
                        "📝 Generar artículo JSON",
                        value=st.session_state.generate_article,
                        help="Genera un artículo SEO usando las etiquetas extraídas o el árbol semántico optimizado",
                        key="generate_article_checkbox"
                    )
            else:
                semantic_analysis = False
                generate_article = False
            
            # Actualizar estados
            st.session_state.extract_tags = extract_tags
            st.session_state.semantic_analysis = semantic_analysis
            st.session_state.generate_article = generate_article
            
            # Si se activa análisis semántico, mostrar parámetros de configuración
            if st.session_state.semantic_analysis and st.session_state.extract_tags:
                self._render_semantic_analysis_parameters()
            
            # Si se activa generar artículo, mostrar la interfaz del generador
            # ocupando todo el ancho debajo de los checkboxes
            if st.session_state.generate_article and st.session_state.extract_tags:
                self._render_article_generator_interface()
            
            # Botón buscar al final
            if Button.primary("Buscar", icon=config.ui.icons["search"]):
                self._perform_search()
    
    def _perform_search(self):
        """Ejecuta la búsqueda en Google y opcionalmente extrae etiquetas HTML"""
        if not st.session_state.query_input:
            Alert.warning("Por favor, introduce al menos una búsqueda")
            return
        
        # Parsear términos de búsqueda
        raw_input = st.session_state.query_input.replace("\n", ",")
        queries = [q.strip() for q in raw_input.split(",") if q.strip()]
        
        # Obtener configuraciones actuales
        language_code, region_code = settings.search_languages[st.session_state.language_option]
        google_domain = settings.google_domains[st.session_state.domain_option]
        
        with LoadingSpinner.show("Consultando BrightData SERP API..."):
            try:
                results = self.scraping_service.search_multiple_queries(
                    queries=queries,
                    num_results=st.session_state.num_results,
                    language_code=language_code,
                    region_code=region_code,
                    google_domain=google_domain
                )
                
                # Si el checkbox está marcado, extraer etiquetas HTML
                if st.session_state.extract_tags:
                    Alert.info("Extrayendo etiquetas HTML de las URLs encontradas...")
                    
                    # Contenedor para el progreso
                    progress_container = st.container()
                    
                    with progress_container:
                        # Ejecutar extracción de etiquetas
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        try:
                            tag_results = loop.run_until_complete(
                                self.tag_service.scrape_tags_from_json(
                                    results,
                                    max_concurrent=5,
                                    progress_callback=None
                                )
                            )
                            
                            # Contar URLs procesadas
                            total_urls = sum(len(r.get("resultados", [])) for r in tag_results)
                            Alert.success(f"✅ Se procesaron {total_urls} URLs con sus etiquetas HTML")
                            
                            # Si está marcado el análisis semántico, ejecutarlo
                            if st.session_state.semantic_analysis:
                                Alert.info("📊 Ejecutando análisis semántico consolidado de todas las etiquetas...")
                                
                                try:
                                    # Ejecutar análisis semántico con TODOS los resultados combinados
                                    # Esto generará UN SOLO árbol SEO consolidado
                                    semantic_tree = self.embeddings_service.analyze_and_group_titles(
                                        data=tag_results,  # Pasar TODOS los resultados
                                        max_titles_h2=st.session_state.get("max_titles_h2", 300),
                                        max_titles_h3=st.session_state.get("max_titles_h3", 900),
                                        n_clusters_h2=st.session_state.get("n_clusters_h2", 10),
                                        n_clusters_h3=st.session_state.get("n_clusters_h3", 30),
                                        model=st.session_state.get("semantic_model", "chatgpt-4o-latest")
                                    )
                                    
                                    # Guardar el árbol semántico único
                                    st.session_state.scraping_results = {
                                        "tipo": "arbol_semantico_consolidado",
                                        "busquedas_originales": queries,
                                        "total_urls_analizadas": total_urls,
                                        "arbol_semantico": semantic_tree,
                                        "datos_originales": tag_results,
                                        "parametros_analisis": {
                                            "max_titles_h2": st.session_state.get("max_titles_h2", 300),
                                            "max_titles_h3": st.session_state.get("max_titles_h3", 900),
                                            "n_clusters_h2": st.session_state.get("n_clusters_h2", 10),
                                            "n_clusters_h3": st.session_state.get("n_clusters_h3", 30),
                                            "model": st.session_state.get("semantic_model", "chatgpt-4o-latest")
                                        }
                                    }
                                    Alert.success("✅ Análisis semántico completado - Árbol SEO consolidado generado")
                                    
                                except Exception as e:
                                    Alert.error(f"Error en análisis semántico: {str(e)}")
                                    # Si falla, mantener los resultados originales
                                    st.session_state.scraping_results = tag_results
                            else:
                                # Solo actualizar con las etiquetas extraídas
                                st.session_state.scraping_results = tag_results
                            
                            # Si también está marcado generar artículo, ejecutar el generador
                            if st.session_state.generate_article:
                                self._generate_article_from_tags(st.session_state.scraping_results)
                            
                        finally:
                            loop.close()
                else:
                    # Solo guardar resultados de Google
                    st.session_state.scraping_results = results
                    Alert.success(f"Se encontraron resultados para {len(results)} búsquedas")
                
                st.rerun()
                
            except Exception as e:
                Alert.error(f"Error durante la búsqueda: {str(e)}")
    
    def _clear_search(self):
        """Limpia la búsqueda actual"""
        st.session_state.scraping_results = []
        st.session_state.query_input = ""
        st.rerun()
    
    def _export_json(self):
        """Exporta los resultados a JSON"""
        if not st.session_state.scraping_results:
            return
        
        filename = f"resultados_{st.session_state.query_input.replace(' ', '_').replace(',', '-')}.json"
        json_bytes = json.dumps(
            st.session_state.scraping_results, 
            ensure_ascii=False, 
            indent=2
        ).encode("utf-8")
        
        st.download_button(
            label="⬇️ Descargar JSON",
            data=json_bytes,
            file_name=filename,
            mime="application/json"
        )
    
    def _upload_to_drive(self):
        """Sube los resultados a Google Drive"""
        if not st.session_state.get("proyecto_id"):
            Alert.warning("Por favor, selecciona un proyecto en la barra lateral")
            return
        
        filename = f"resultados_{st.session_state.query_input.replace(' ', '_').replace(',', '-')}.json"
        json_bytes = json.dumps(
            st.session_state.scraping_results, 
            ensure_ascii=False, 
            indent=2
        ).encode("utf-8")
        
        try:
            # Determinar carpeta según el tipo de resultados
            if isinstance(st.session_state.scraping_results, dict) and st.session_state.scraping_results.get("tipo") == "arbol_semantico_consolidado":
                folder_name = "arboles seo"
            elif st.session_state.extract_tags:
                folder_name = "scraper etiquetas google"
            else:
                folder_name = "scraping google"
            
            # Obtener o crear subcarpeta
            folder_id = self.drive_service.get_or_create_folder(
                folder_name, 
                st.session_state.proyecto_id
            )
            
            # Subir archivo
            link = self.drive_service.upload_file(
                filename,
                json_bytes,
                folder_id
            )
            
            if link:
                Alert.success(f"Archivo subido correctamente: [Ver archivo]({link})")
            else:
                Alert.error("Error al subir el archivo")
                
        except Exception as e:
            Alert.error(f"Error al subir a Drive: {str(e)}")

    def _export_to_mongo(self):
        """Exporta los resultados a MongoDB"""
        try:
            mongo = MongoRepository(config.mongo_uri, config.app.mongo_default_db)
            
            # Determinar la colección según el tipo de resultados
            if isinstance(st.session_state.scraping_results, dict) and st.session_state.scraping_results.get("tipo") == "arbol_semantico_consolidado":
                # Es un árbol semántico consolidado
                collection_name = "arboles_seo"
                # Guardar solo el árbol semántico con metadatos
                documents_to_save = [{
                    "tipo": "arbol_semantico_consolidado",
                    "busquedas_originales": st.session_state.scraping_results.get("busquedas_originales", []),
                    "total_urls_analizadas": st.session_state.scraping_results.get("total_urls_analizadas", 0),
                    "arbol_semantico": st.session_state.scraping_results.get("arbol_semantico", {}),
                    "parametros_analisis": st.session_state.scraping_results.get("parametros_analisis", {}),
                    "fecha_creacion": datetime.now().isoformat()
                }]
            elif not st.session_state.extract_tags:
                # Sin extraer etiquetas HTML -> Guardar en "URLs Google"
                collection_name = "URLs Google"
                documents_to_save = st.session_state.scraping_results
            else:
                # Con extraer etiquetas HTML marcado -> Guardar en "URLs Google Tags"
                collection_name = "URLs Google Tags"
                documents_to_save = st.session_state.scraping_results
            
            inserted_ids = mongo.insert_many(
                documents=documents_to_save,
                collection_name=collection_name
            )
            Alert.success(f"{len(inserted_ids)} JSON exportado a MongoDB (colección: {collection_name}):\n" + "\n".join(f"- {i}" for i in inserted_ids))
            return
        except Exception as e:
            Alert.error(f"Error exportando a MongoDB: {str(e)}")
    
    def _render_results_section(self):
        """Renderiza la sección de resultados"""
        Card.render(
            title="Resultados de Búsqueda",
            icon=config.ui.icons["document"],
            content=lambda: self._display_results()
        )
    
    def _display_results(self):
        """Muestra los resultados según el modo: URLs, etiquetas o artículos generados"""
        # Si se generaron múltiples artículos
        if isinstance(st.session_state.scraping_results, dict) and "generated_articles" in st.session_state.scraping_results:
            st.subheader("📄 Artículos Generados")
            
            # Mostrar resumen
            total_articles = st.session_state.scraping_results.get("total_articles", 0)
            st.success(f"✅ Se generaron {total_articles} artículos exitosamente")
            
            # Métricas generales
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total artículos", total_articles)
            with col2:
                st.metric("Colección", "posts")
            with col3:
                st.metric("Estado", "Guardados en MongoDB")
            
            # Mostrar cada artículo generado
            for idx, article_data in enumerate(st.session_state.scraping_results["generated_articles"]):
                keyword = article_data["keyword"]
                article = article_data["article"]
                article_id = article_data["article_id"]
                
                with st.expander(f"📝 Artículo {idx + 1}: {keyword}", expanded=(idx == 0)):
                    # Info del artículo
                    st.info(f"**Keyword:** {keyword} | **MongoDB ID:** {article_id[-12:]}")
                    
                    # Vista previa del contenido
                    st.markdown("#### 👁️ Vista Previa")
                    
                    # Título principal
                    title = article.get("title", "")
                    if title:
                        st.markdown(f"**{title}**")
                    
                    # Slug
                    slug = article.get("slug", "")
                    if slug:
                        st.caption(f"🔗 URL: /{slug}")
                    
                    # Total de palabras
                    total_words = article.get("total_palabras")
                    if total_words:
                        st.write(f"📊 Total de palabras: {total_words}")
                    
                    # Mostrar JSON del artículo
                    DataDisplay.json(
                        article,
                        title=f"JSON del Artículo: {keyword}",
                        expanded=False
                    )
            
            # Mostrar resumen de etiquetas HTML usadas
            if "tag_results" in st.session_state.scraping_results:
                with st.expander("🏷️ Etiquetas HTML extraídas (datos de competencia)"):
                    DataDisplay.json(
                        st.session_state.scraping_results["tag_results"],
                        title="Etiquetas HTML usadas para generar los artículos",
                        expanded=False
                    )
            
        # Si tenemos un árbol semántico consolidado
        elif isinstance(st.session_state.scraping_results, dict) and st.session_state.scraping_results.get("tipo") == "arbol_semantico_consolidado":
            st.subheader("🌲 Árbol SEO Consolidado")
            
            result = st.session_state.scraping_results
            
            # Resumen
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Búsquedas combinadas", len(result.get("busquedas_originales", [])))
            with col2:
                st.metric("URLs analizadas", result.get("total_urls_analizadas", 0))
            with col3:
                st.metric("Estado", "✅ Análisis completado")
            
            # Mostrar búsquedas originales
            st.info(f"**Búsquedas originales:** {', '.join(result.get('busquedas_originales', []))}")
            
            # Mostrar el árbol semántico
            semantic_tree = result.get("arbol_semantico", {})
            if semantic_tree:
                # Card con el H1 generado
                Card.render(
                    title="🏷️ H1 Generado",
                    content=f"# {semantic_tree.get('title', 'Sin título')}",
                    icon="🎯"
                )
                
                # Estructura del árbol
                st.markdown("### 🌲 Vista Previa del Árbol SEO")
                
                # Mostrar cada H2 con sus H3s
                for h2_item in semantic_tree.get("H2", []):
                    with st.expander(f"📂 {h2_item['titulo']}", expanded=True):
                        h3_list = h2_item.get("H3", [])
                        if h3_list:
                            for h3 in h3_list:
                                st.markdown(f"    └── 📄 {h3}")
                        else:
                            st.caption("    └── Sin H3s asociados")
                
                # Estadísticas del árbol
                st.markdown("### 📈 Resumen Estadístico")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total H2", len(semantic_tree.get("H2", [])))
                
                with col2:
                    total_h3 = sum(len(h2.get("H3", [])) for h2 in semantic_tree.get("H2", []))
                    st.metric("Total H3", total_h3)
                
                with col3:
                    avg_h3_per_h2 = total_h3 / len(semantic_tree.get("H2", [])) if semantic_tree.get("H2") else 0
                    st.metric("Promedio H3 por H2", f"{avg_h3_per_h2:.1f}")
            
            # Mostrar parámetros del análisis
            with st.expander("⚙️ Parámetros del análisis"):
                params = result.get("parametros_analisis", {})
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Max títulos H2:** {params.get('max_titles_h2', 'N/A')}")
                    st.write(f"**Clusters H2:** {params.get('n_clusters_h2', 'N/A')}")
                with col2:
                    st.write(f"**Max títulos H3:** {params.get('max_titles_h3', 'N/A')}")
                    st.write(f"**Clusters H3:** {params.get('n_clusters_h3', 'N/A')}")
                st.write(f"**Modelo:** {params.get('model', 'N/A')}")
            
            # Mostrar JSON completo
            DataDisplay.json(
                result,
                title="JSON Completo (Árbol SEO Consolidado)",
                expanded=True
            )
            
        # Si se extrajeron etiquetas, mostrar como en la página de etiquetas HTML
        elif st.session_state.extract_tags and st.session_state.scraping_results and isinstance(st.session_state.scraping_results, list):
            # Esta es la visualización normal de etiquetas (sin análisis semántico)
            st.subheader("📦 Resultados estructurados")
            
            # Resumen
            total_searches = len(st.session_state.scraping_results)
            total_urls = sum(len(r.get("resultados", [])) for r in st.session_state.scraping_results)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Búsquedas procesadas", total_searches)
            with col2:
                st.metric("URLs analizadas", total_urls)
            
            # Mostrar resultados por búsqueda
            for result in st.session_state.scraping_results:
                search_term = result.get("busqueda", "Sin término")
                urls_count = len(result.get("resultados", []))
                
                with st.expander(f"🔍 {search_term} - {urls_count} URLs"):
                    # Información de contexto
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Idioma:** {result.get('idioma', 'N/A')}")
                    with col2:
                        st.write(f"**Región:** {result.get('region', 'N/A')}")
                    with col3:
                        st.write(f"**Dominio:** {result.get('dominio', 'N/A')}")
                    
                    # Resultados por URL
                    for url_result in result.get("resultados", []):
                        self._display_url_result(url_result)
            
            # Mostrar JSON completo
            DataDisplay.json(
                st.session_state.scraping_results,
                title="JSON Completo (Etiquetas HTML)",
                expanded=True
            )
        else:
            # Mostrar resultados normales de Google
            for result in st.session_state.scraping_results:
                with st.expander(f"🔍 {result['busqueda']} - {len(result.get('urls', []))} URLs"):
                    # Información de la búsqueda
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Idioma:** {result['idioma']}")
                    with col2:
                        st.write(f"**Región:** {result['region']}")
                    with col3:
                        st.write(f"**Dominio:** {result['dominio']}")
                    
                    # Mostrar URLs
                    if result.get('urls'):
                        st.write("**URLs encontradas:**")
                        for i, url in enumerate(result['urls'], 1):
                            st.write(f"{i}. {url}")
                    else:
                        st.write("No se encontraron URLs")
                    
                    # Mostrar error si existe
                    if result.get('error'):
                        Alert.error(f"Error: {result['error']}")
            
            # Mostrar JSON completo
            DataDisplay.json(
                st.session_state.scraping_results,
                title="JSON Completo (URLs de Google)",
                expanded=True
            )
    
    def _display_url_result(self, url_result: Dict[str, Any]):
        """Reutiliza el método de visualización de la página de etiquetas HTML"""
        # Usar directamente el método de la página de etiquetas
        self.tag_page._display_url_result(url_result)
    
    def _render_semantic_analysis_parameters(self):
        """Renderiza los parámetros de configuración del análisis semántico"""
        st.markdown("---")
        st.markdown("#### ⚙️ Parámetros de Agrupación")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.session_state.n_clusters_h2 = st.slider(
                "🧠 Número de clústeres para H2",
                min_value=2,
                max_value=30,
                value=10,
                help="Número de grupos para agrupar títulos H2"
            )
            
            st.session_state.max_titles_h2 = st.slider(
                "📄 Máximo de títulos H2",
                min_value=100,
                max_value=1500,
                value=300,
                help="Máximo número de títulos H2 a procesar"
            )
        
        with col2:
            st.session_state.n_clusters_h3 = st.slider(
                "🧠 Número de clústeres para H3",
                min_value=2,
                max_value=100,
                value=30,
                help="Número de grupos para agrupar títulos H3"
            )
            
            st.session_state.max_titles_h3 = st.slider(
                "📄 Máximo de títulos H3",
                min_value=100,
                max_value=3000,
                value=900,
                help="Máximo número de títulos H3 a procesar"
            )
        
        # Modelo GPT
        st.markdown("#### 🤖 Modelo de IA")
        st.session_state.semantic_model = st.selectbox(
            "Modelo GPT",
            config.app.gpt_models,
            index=config.app.gpt_models.index("chatgpt-4o-latest") if "chatgpt-4o-latest" in config.app.gpt_models else 0,
            help="Modelo de IA para generar títulos representativos"
        )
    
    def _render_article_generator_interface(self):
        """Renderiza la interfaz del generador de artículos"""
        st.markdown("---")
        st.markdown("#### ⚙️ Parámetros del Generador de Artículos")
        
        # Mostrar las keywords que se usarán
        raw_input = st.session_state.query_input.replace("\n", ",")
        keywords = [q.strip() for q in raw_input.split(",") if q.strip()]
        
        if keywords:
            st.info(f"📝 Se generarán {len(keywords)} artículos, uno por cada keyword: {', '.join(keywords)}")
        
        # Parámetros principales (sin el campo keyword)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Detectar idioma basado en la configuración de búsqueda
            language_map = {
                "Español (España)": "Español",
                "Inglés (Estados Unidos)": "Inglés",
                "Inglés (Reino Unido)": "Inglés",
                "Francés (Francia)": "Francés",
                "Alemán (Alemania)": "Alemán"
            }
            default_language = language_map.get(st.session_state.language_option, "Español")
            
            language = st.selectbox(
                "Idioma",
                ["Español", "Inglés", "Francés", "Alemán"],
                index=["Español", "Inglés", "Francés", "Alemán"].index(default_language)
            )
            st.session_state.language = language
        
        with col2:
            content_type = st.selectbox(
                "Tipo de contenido",
                ["Informativo", "Transaccional", "Ficha de producto"],
                index=0
            )
            st.session_state.content_type = content_type
        
        with col3:
            models = config.app.gpt_models
            model = st.selectbox(
                "Modelo GPT",
                models,
                index=models.index("gpt-4o-latest") if "gpt-4o-latest" in models else 0
            )
            st.session_state.model = model
        
        # Ajustes avanzados
        with st.expander("⚙️ Ajustes avanzados", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.session_state.temperature = st.slider(
                    "Temperature",
                    0.0, 2.0, 0.9, 0.05,
                    help="Controla la creatividad (mayor = más creativo)"
                )
                st.session_state.top_p = st.slider(
                    "Top-p",
                    0.0, 1.0, 1.0, 0.05,
                    help="Controla la diversidad del vocabulario"
                )
            
            with col2:
                st.session_state.frequency_penalty = st.slider(
                    "Frequency penalty",
                    0.0, 2.0, 0.0, 0.1,
                    help="Reduce la repetición de palabras"
                )
                st.session_state.presence_penalty = st.slider(
                    "Presence penalty",
                    0.0, 2.0, 0.0, 0.1,
                    help="Aumenta la probabilidad de hablar sobre nuevos temas"
                )
        
        # Opciones de generación
        st.markdown("#### 📝 Opciones de Generación")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.session_state.generate_schema = st.checkbox(
                "📑 Esquema",
                value=True,
                help="Genera la estructura H1/H2/H3"
            )
        
        with col2:
            st.session_state.generate_text = st.checkbox(
                "✍️ Textos",
                value=True,
                help="Genera contenido completo para cada sección"
            )
        
        with col3:
            st.session_state.generate_slug = st.checkbox(
                "🔗 Slug H1",
                value=True,
                help="Genera URL amigable del H1"
            )
        
        # Estimación de coste
        # Los datos de competencia serán los resultados de etiquetas
        est_input = len(json.dumps(st.session_state.scraping_results).encode()) // 4 if st.session_state.scraping_results else 1000
        est_output = 3000 if st.session_state.get("generate_text", False) else 800
        
        cost_in, cost_out = self.article_page.article_service.estimate_cost(
            st.session_state.get("model", "gpt-4o-mini"),
            est_input,
            est_output
        )
        
        st.markdown(
            f"💰 **Coste estimado:** Entrada: ${cost_in:.3f} / "
            f"Salida: ${cost_out:.3f} / "
            f"**Total: ${cost_in + cost_out:.3f}**"
        )
    
    def _generate_article_from_tags(self, tag_results):
        """Genera artículos para cada keyword usando las etiquetas extraídas o el árbol semántico"""
        # Parsear keywords del textarea
        raw_input = st.session_state.query_input.replace("\n", ",")
        keywords = [q.strip() for q in raw_input.split(",") if q.strip()]
        
        if not keywords:
            Alert.warning("No se encontraron keywords para generar artículos")
            return
        
        Alert.info(f"Generando {len(keywords)} artículos con IA...")
        
        # Verificar si tenemos un árbol semántico consolidado
        is_semantic_tree = (
            isinstance(tag_results, dict) and 
            tag_results.get("tipo") == "arbol_semantico_consolidado"
        )
        
        if is_semantic_tree:
            Alert.info("📊 Usando árbol semántico consolidado para generar los artículos")
            # Para el árbol semántico, usar los datos originales si están disponibles
            data_for_competition = tag_results.get("datos_originales", tag_results)
            urls_analyzed = tag_results.get("total_urls_analizadas", 0)
        else:
            # Es una lista de resultados de etiquetas
            data_for_competition = tag_results
            urls_analyzed = sum(len(r.get("resultados", [])) for r in tag_results) if isinstance(tag_results, list) else 0
        
        # Convertir los resultados a JSON para usar como datos de competencia
        competition_data = json.dumps(data_for_competition).encode()
        
        # Conectar a MongoDB una sola vez
        mongo = MongoRepository(config.mongo_uri, config.app.mongo_default_db)
        
        # Lista para almacenar todos los artículos generados
        generated_articles = []
        
        # Crear un contenedor para mostrar el progreso
        progress_container = st.container()
        
        with progress_container:
            # Barra de progreso
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, keyword in enumerate(keywords):
                try:
                    # Actualizar estado
                    status_text.text(f"Generando artículo {idx + 1} de {len(keywords)}: {keyword}")
                    
                    # Llamar al servicio del generador de artículos
                    result = self.article_page.article_service.generate_article_schema(
                        keyword=keyword,
                        language=st.session_state.get("language", "Español"),
                        content_type=st.session_state.get("content_type", "Informativo"),
                        model=st.session_state.get("model", "gpt-4o-mini"),
                        generate_text=st.session_state.get("generate_text", True),
                        generate_slug=st.session_state.get("generate_slug", True),
                        competition_data=competition_data,
                        temperature=st.session_state.get("temperature", 0.9),
                        top_p=st.session_state.get("top_p", 1.0),
                        frequency_penalty=st.session_state.get("frequency_penalty", 0.0),
                        presence_penalty=st.session_state.get("presence_penalty", 0.0)
                    )
                    
                    # Añadir metadatos al artículo
                    article_with_metadata = {
                        **result,
                        "metadata": {
                            "generated_from": "google_scraping",
                            "search_query": keyword,
                            "all_keywords": keywords,
                            "language_option": st.session_state.language_option,
                            "domain_option": st.session_state.domain_option,
                            "num_results": st.session_state.num_results,
                            "urls_analyzed": urls_analyzed,
                            "used_semantic_tree": is_semantic_tree,
                            "generation_date": datetime.now().isoformat()
                        }
                    }
                    
                    # Guardar en MongoDB
                    inserted_id = mongo.insert_one(
                        article_with_metadata,
                        collection_name="posts"
                    )
                    
                    # Añadir a la lista de artículos generados
                    generated_articles.append({
                        "keyword": keyword,
                        "article": result,
                        "article_id": str(inserted_id)
                    })
                    
                    Alert.success(f"✅ Artículo '{keyword}' generado y guardado con ID: {inserted_id}")
                    
                    # Actualizar barra de progreso
                    progress_bar.progress((idx + 1) / len(keywords))
                    
                except Exception as e:
                    Alert.error(f"Error al generar artículo para '{keyword}': {str(e)}")
                    continue
            
            # Limpiar el texto de estado
            status_text.text(f"✅ Proceso completado: {len(generated_articles)} artículos generados")
        
        # Actualizar los resultados para incluir todos los artículos generados
        if generated_articles:
            st.session_state.scraping_results = {
                "tag_results": tag_results,
                "generated_articles": generated_articles,
                "total_articles": len(generated_articles)
            }
            
            Alert.success(f"🎉 Se generaron {len(generated_articles)} artículos exitosamente")
