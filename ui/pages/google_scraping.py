"""
Página de UI para Scraping de Google
"""
import streamlit as st
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from ui.components.common import Card, Alert, Button, LoadingSpinner, DataDisplay, SelectBox
from services.google_scraping_service import GoogleScrapingService
from services.tag_scraping_service import TagScrapingService
from services.drive_service import DriveService
from config import config
from repositories.mongo_repository import MongoRepository

class GoogleScrapingPage:
    """Página para scraping de resultados de Google"""
    
    def __init__(self):
        self.scraping_service = GoogleScrapingService()
        self.tag_service = TagScrapingService()
        self.drive_service = DriveService()
        # Importar la página de etiquetas para reutilizar su visualización
        from ui.pages.tag_scraping import TagScrapingPage
        self.tag_page = TagScrapingPage()
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
            st.session_state.extract_tags = False
        if "generate_article" not in st.session_state:
            st.session_state.generate_article = False
    
    def render(self):
        """Renderiza la página completa"""
        st.title(f"{config.ui.icons['search']} Scraping de URLs desde Google")
        
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
                options=list(config.scraping.search_languages.keys()),
                index=list(config.scraping.search_languages.keys()).index(st.session_state.language_option)
            )
            st.session_state.language_option = language_option
            
            # Dominio de Google
            domain_option = st.selectbox(
                "🧭 Dominio de Google",
                options=list(config.scraping.google_domains.keys()),
                index=list(config.scraping.google_domains.keys()).index(st.session_state.domain_option)
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
            col1, col2 = st.columns([1, 3])
            with col1:
                if Button.primary("Buscar", icon=config.ui.icons["search"]):
                    self._perform_search()
            with col2:
                # Checkbox para extraer etiquetas
                extract_tags = st.checkbox(
                    "🏷️ Extraer etiquetas HTML automáticamente",
                    value=st.session_state.extract_tags,
                    help="Extrae la estructura H1/H2/H3 de las URLs encontradas",
                    key="extract_tags_cb"
                )
                
                # Checkbox para generar artículo (siempre visible)
                # Si extract_tags es False, forzar generate_article a False también
                generate_article_value = st.session_state.generate_article if extract_tags else False
                
                generate_article = st.checkbox(
                    "📝 Generar artículo JSON",
                    value=generate_article_value,
                    help="Genera un artículo SEO usando las etiquetas extraídas (requiere extraer etiquetas HTML)",
                    disabled=not extract_tags,  # Deshabilitar si no hay etiquetas
                    key="generate_article_cb"
                )
                
                # Actualizar estados
                st.session_state.extract_tags = extract_tags
                st.session_state.generate_article = generate_article if extract_tags else False
                
                # Si se activa generar artículo, mostrar la interfaz del generador
                if st.session_state.generate_article and st.session_state.extract_tags:
                    self._render_article_generator_interface()
    
    def _perform_search(self):
        """Ejecuta la búsqueda en Google y opcionalmente extrae etiquetas HTML"""
        if not st.session_state.query_input:
            Alert.warning("Por favor, introduce al menos una búsqueda")
            return
        
        # Parsear términos de búsqueda
        raw_input = st.session_state.query_input.replace("\n", ",")
        queries = [q.strip() for q in raw_input.split(",") if q.strip()]
        
        # Obtener configuraciones actuales
        language_code, region_code = config.scraping.search_languages[st.session_state.language_option]
        google_domain = config.scraping.google_domains[st.session_state.domain_option]
        
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
                            
                            # Actualizar los resultados con las etiquetas extraídas
                            st.session_state.scraping_results = tag_results
                            
                            # Contar URLs procesadas
                            total_urls = sum(len(r.get("resultados", [])) for r in tag_results)
                            Alert.success(f"✅ Se procesaron {total_urls} URLs con sus etiquetas HTML")
                            
                            # Si también está marcado generar artículo, ejecutar el generador
                            if st.session_state.generate_article:
                                self._generate_article_from_tags(tag_results)
                            
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
            # Obtener o crear subcarpeta
            folder_id = self.drive_service.get_or_create_folder(
                "scraping google", 
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
            
            # Determinar la colección según si se extrajeron etiquetas o no
            collection_name = "hoteles" if st.session_state.extract_tags else "URLs Google"
            
            inserted_ids = mongo.insert_many(
                documents=st.session_state.scraping_results,
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
            
        # Si se extrajeron etiquetas, mostrar como en la página de etiquetas HTML
        elif st.session_state.extract_tags and st.session_state.scraping_results and isinstance(st.session_state.scraping_results, list) and st.session_state.scraping_results[0].get('resultados'):
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
        """Genera artículos para cada keyword usando las etiquetas extraídas"""
        # Parsear keywords del textarea
        raw_input = st.session_state.query_input.replace("\n", ",")
        keywords = [q.strip() for q in raw_input.split(",") if q.strip()]
        
        if not keywords:
            Alert.warning("No se encontraron keywords para generar artículos")
            return
        
        Alert.info(f"Generando {len(keywords)} artículos con IA...")
        
        # Convertir los resultados a JSON para usar como datos de competencia
        competition_data = json.dumps(tag_results).encode()
        
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
                            "urls_analyzed": sum(len(r.get("resultados", [])) for r in tag_results),
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
