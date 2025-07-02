"""
Configuración de XPath para extracción de datos de Booking.com
Estructura idéntica al JSON de salida del servicio booking_extraer_datos_service.py
Cada variable tiene el mismo nombre que el campo JSON correspondiente
"""

class BookingExtraerDatosXPathConfig:
    """Configuración de XPath siguiendo exactamente la estructura del JSON de salida"""
    
    # ========================================
    # NIVEL RAÍZ DEL JSON
    # ========================================
    
    # title - Se genera dinámicamente: "{nombre_alojamiento} – Lujo exclusivo en {ciudad}"
    # No tiene xpath, se construye en _build_final_response()
    
    # content - Se genera dinámicamente con descripción estructurada en HTML
    # ACTUALIZACIÓN: XPaths simples y directos para property-description
    content = [
        # XPaths principales para property-description
        #"//p[@data-testid='property-description']//text()[normalize-space()]",
        "//p[@data-testid='property-description']//text()",

        # XPaths con descendant para buscar profundo
        #"//descendant::p[@data-testid='property-description']//text()[normalize-space()]",
        #"//*[@data-testid='property-description']//text()[normalize-space()]",
       
    ]
    
    # content_h2_headers - Headers H2 que indican secciones de descripción
    content_h2_headers = [
        "//h2[contains(text(), 'Descripción')]",
        "//h2[contains(text(), 'Acerca de')]",
        "//h2[contains(text(), 'About')]",
        "//h2[contains(text(), 'El alojamiento')]"
    ]
    
    # status - Valor fijo: "publish"
    # No tiene xpath, siempre es "publish"
    
    # type - Valor fijo: "alojamientos" 
    # No tiene xpath, siempre es "alojamientos"
    
    # slug - Se genera dinámicamente desde title usando _generate_slug()
    # No tiene xpath, se construye automáticamente
    
    # ========================================
    # obj_featured_media - Imagen destacada principal del hotel
    # ========================================
    # Estructura del objeto JSON resultante:
    # {
    #   "image_url": "",      <- Extraído con los XPath de abajo
    #   "title": "",          <- Generado: "{nombre_hotel}_001"
    #   "alt_text": "",       <- Extraído del atributo alt="" del elemento img
    #   "caption": "",        <- Igual que title
    #   "description": "",    <- Si existe alt_text lo usa, sino usa title
    #   "filename": ""        <- Generado: "{nombre_hotel}_001.jpg"
    # }
    #
    # NOTA: Los XPath siguientes son SOLO para extraer la URL de la imagen (image_url)
    # Los demás campos se generan automáticamente en _extract_image_attributes()
    obj_featured_media = [
        "//div[contains(@class, 'hotel-header-image')]//img/@src",
        "//div[contains(@class, 'hotel-header-image')]//img/@data-src",
        "//div[@data-testid='property-gallery']//img[1]/@src",
        "//div[@data-testid='property-gallery']//img[1]/@data-src",
        "//div[contains(@class, 'gallery-container')]//img[1]/@src",
        "//div[contains(@class, 'gallery-container')]//img[1]/@data-src",
        "//img[contains(@src, 'bstatic.com/xdata/images/hotel') and contains(@src, 'max1024x768')][1]/@src",
        "//img[contains(@data-src, 'bstatic.com/xdata/images/hotel') and contains(@data-src, 'max1024x768')][1]/@data-src",
        "//img[contains(@src, 'bstatic.com/xdata/images/hotel')][1]/@src",
        "//img[contains(@data-src, 'bstatic.com/xdata/images/hotel')][1]/@data-src"
    ]
    
    # ========================================
    # meta - Metadatos del hotel
    # ========================================
    
    # nombre_alojamiento - Nombre oficial del hotel extraído del HTML
    nombre_alojamiento = [
        "//h2[contains(@class, 'pp-header__title')]/text()",
        "//h1[@id='hp_hotel_name']/text()",
        "//h1[contains(@class, 'hotel-name')]/text()"
    ]
    
    # tipo_alojamiento - Tipo de alojamiento (hotel, apartamento, etc.)
    # No tiene xpath específico, se obtiene de datos estructurados JSON-LD o JS (utag_data.hotel_type)
    
    # slogan_principal - Slogan o frase principal del hotel
    # No tiene xpath, se deja vacío por defecto ""
    
    # descripcion_corta - Descripción breve en formato HTML
    # No tiene xpath específico, se obtiene de datos estructurados JSON-LD (data_extraida.description)
    
    # estrellas - Categoría en estrellas del hotel (1-5)
    # No tiene xpath específico, se obtiene de JS (utag_data.hotel_class) o JSON-LD
    
    # precio_noche - Precio por noche en euros
    precio_noche = [
        "//span[contains(@class, 'prco-valign-middle-helper')]/text()",
        "//div[contains(@class, 'bui-price-display__value')]//span[contains(@class, 'prco-valign-middle-helper')]/text()",
        "//div[contains(@data-testid, 'price-and-discounted-price')]//span[contains(@class, 'Value')]/text()",
        "//div[@data-testid='property-card-container']//div[@data-testid='price-and-discounted-price']/span[1]/text()",
        "//span[@data-testid='price-text']/text()",
        "//span[contains(@class, 'fcab3ed991') and contains(@class, 'bd73d13072')]/text()",
        "//div[contains(@class, 'bui-price-display__value')]/text()",
        "//span[contains(@class, 'bui-price-display__value')]/text()",
        "//div[@data-testid='price-and-discounted-price']//span/text()",
        "//span[contains(text(), '€') or contains(text(), 'EUR')]/text()",
        "//div[contains(@class, 'price')]//span[contains(text(), '€')]/text()",
        "//span[contains(@aria-label, 'precio') or contains(@aria-label, 'price')]/text()"
    ]
    
    # alojamiento_destacado - "No por defecto"
    alojamiento_destacado = []
    
    # isla_relacionada - Isla donde se ubica (para destinos insulares)
    # No tiene xpath específico, se extrae de meta keywords con regex I:([^,]+)
    
    # frases_destacadas - Frases promocionales del hotel (objeto con item-0, item-1, etc.)
    frases_destacadas = [
        "//div[@data-testid='PropertyHighlightList-wrapper']//ul/li//div[contains(@class, 'b99b6ef58f')]//span[contains(@class, 'f6b6d2a959') and not(contains(text(), 'Reserva')) and not(contains(text(), 'Guardar')) and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]/text()",
        "//div[contains(@class, 'hp--desc_highlights')]//div[contains(@class,'ph-item-copy-container')]//span[not(contains(text(), 'Reserva')) and not(contains(text(), 'Guardar')) and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]/text()",
        "//div[contains(@class, 'property-highlights')]//span[not(contains(text(), 'Reserva')) and not(contains(text(), 'Guardar')) and not(ancestor::button) and not(ancestor::a) and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]/text()",
        "//div[contains(@class, 'hp_desc_important_facilities')]//span[not(contains(text(), 'Reserva')) and not(contains(text(), 'Guardar')) and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]/text()"
    ]
    
    # servicios - Array de servicios/instalaciones del hotel
    # ACTUALIZACIÓN: XPaths para búsqueda PROFUNDA de elementos con style="--bui_stack_spaced_gap--s:0"
    servicios = [
       
        "//div[@data-testid='property-highlights']//li/div[2]/div/text()"       
       
    ]
    
    # valoracion_limpieza - Puntuación de limpieza (0-10)
    valoracion_limpieza = [
        "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and contains(translate(text(), 'LIMPIEZA', 'limpieza'), 'limpieza')]/following-sibling::*//div[contains(@class, 'f87e152973')]/text()",
        "//li//p[contains(@class, 'review_score_name') and contains(translate(text(), 'LIMPIEZA', 'limpieza'), 'limpieza')]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
    ]
    
    # valoracion_confort - Puntuación de confort (0-10)
    valoracion_confort = [
        
        "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and contains(translate(text(), 'CONFORT', 'confort'), 'confort')]/following-sibling::*//div[contains(@class, 'f87e152973')]/text()",
        "//li//p[contains(@class, 'review_score_name') and contains(translate(text(), 'CONFORT', 'confort'), 'confort')]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
    ]
    
    # valoracion_ubicacion - Puntuación de ubicación (0-10)

    valoracion_ubicacion = [
        "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and contains(translate(normalize-space(text()), 'ÚÁÉÍÓÚÜ', 'uaeiouu'), 'ubicacion')]/following-sibling::div[contains(@class, 'f87e152973')]/text()",
        "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and contains(translate(normalize-space(text()), 'ÚÁÉÍÓÚÜ', 'uaeiouu'), 'ubicacion')]/parent::div//div[contains(@class, 'f87e152973')]/text()",
        "//li//p[contains(@class, 'review_score_name') and contains(translate(normalize-space(text()), 'ÚÁÉÍÓÚÜ', 'uaeiouu'), 'ubicacion')]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
    ]

    # valoracion_instalaciones_servicios_ - Puntuación de instalaciones (0-10)
    # Nota: El guión bajo final es intencional, así está en el JSON
    valoracion_instalaciones_servicios_ = [
        "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and (contains(translate(text(), 'INSTALACIONES', 'instalaciones'), 'instalaciones') or contains(translate(text(), 'SERVICIOS', 'servicios'), 'servicios'))]/following-sibling::div[contains(@class, 'f87e152973')]/text()",
        "//li//p[contains(@class, 'review_score_name') and (contains(translate(text(), 'INSTALACIONES', 'instalaciones'), 'instalaciones') or contains(translate(text(), 'SERVICIOS', 'servicios'), 'servicios'))]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
    ]

    # valoracion_personal - Puntuación del personal (0-10)
    valoracion_personal = [
        "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and (contains(translate(normalize-space(text()), 'ÚÁÉÍÓÚÜ', 'uaeiouu'), 'personal') or contains(translate(normalize-space(text()), 'STAFF', 'staff'), 'staff'))]/following-sibling::div[contains(@class, 'f87e152973')]/text()",
        "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and (contains(translate(normalize-space(text()), 'ÚÁÉÍÓÚÜ', 'uaeiouu'), 'personal') or contains(translate(normalize-space(text()), 'STAFF', 'staff'), 'staff'))]/parent::div//div[contains(@class, 'f87e152973')]/text()",
        "//li//p[contains(@class, 'review_score_name') and (contains(translate(normalize-space(text()), 'ÚÁÉÍÓÚÜ', 'uaeiouu'), 'personal') or contains(translate(normalize-space(text()), 'STAFF', 'staff'), 'staff'))]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
    ]

    # valoracion_calidad_precio - Puntuación calidad-precio (0-10)
    valoracion_calidad_precio = [
        "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and contains(text(), 'calidad')]/following-sibling::*//div[contains(@class, 'f87e152973')]/text()",
        "//li//p[contains(@class, 'review_score_name') and contains(text(), 'calidad')]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
    ]
    
    # valoracion_wifi - Puntuación del WiFi (0-10)
    valoracion_wifi = [
        "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and contains(translate(text(), 'WIFI', 'wifi'), 'wifi')]/following-sibling::div[contains(@class, 'f87e152973')]/text()",
        "//li//p[contains(@class, 'review_score_name') and contains(translate(text(), 'WIFI', 'wifi'), 'wifi')]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
    ]

    # valoracion_global - Puntuación global del hotel (0-10)
    valoracion_global = [
        "//div[@data-testid='review-score-right-component']//div[contains(@class, 'dff2e52086')]/text()",
        "//div[contains(@class, 'bui-review-score__badge')]/text()",
        "//span[contains(@class, 'review-score-badge')]/text()"
    ]
    
    # numero_opiniones - Número total de opiniones/reseñas
    # No está en el JSON de salida pero se usa internamente
    numero_opiniones = [
        "//div[@data-testid='review-score-right-component']//div[contains(@class, 'fb14de7f14')]/text()",
        "//div[contains(@class, 'bui-review-score__text')]/text()",
        "//span[contains(@class, 'review-count')]/text()"
    ]
    
    # images - Galería de imágenes del hotel (objeto con item-0, item-1, etc.)
    # Estructura del objeto JSON resultante para cada imagen:
    # {
    #   "image_url": "",      <- Extraído del src o data-src del elemento img
    #   "title": "",          <- Generado: "{nombre_hotel}_002", "_003", etc.
    #   "alt_text": "",       <- Extraído del atributo alt="" del elemento img
    #   "caption": "",        <- Igual que title
    #   "description": "",    <- Si existe alt_text lo usa, sino usa title
    #   "filename": ""        <- Generado: "{nombre_hotel}_002.jpg", "_003.jpg", etc.
    # }
    #
    # NOTA: Los XPath buscan elementos <img> completos, no solo URLs
    # La función _extract_image_attributes() extrae todos los atributos necesarios
    images = [
        "//a[@data-fancybox='gallery'] img",
        "//div[contains(@class, 'bh-photo-grid-item')] img",
        "//img[contains(@data-src, 'xdata/images/hotel')]",
        "//img[contains(@src, 'bstatic.com/xdata/images/hotel')]"
    ]
    
    # direccion - Dirección física completa del hotel
    direccion = [
        "//a[contains(@data-atlas-latlng, ',')]/following-sibling::span[1]//button//div/text()"
    ]
    
    # enlace_afiliado - URL original de Booking.com
    # No tiene xpath, se pasa directamente como parámetro (la URL procesada)
    
    # sitio_web_oficial - Web oficial del hotel
    # No tiene xpath, se deja vacío por defecto ""
    
    # titulo_h1 - Título principal H1 de la página
    # Se usa el mismo xpath que nombre_alojamiento
    titulo_h1 = [
        "//h2[contains(@class, 'pp-header__title')]/text()",
        "//h1[@id='hp_hotel_name']/text()",
        "//h1[contains(@class, 'hotel-name')]/text()"
    ]
    
    # bloques_contenido_h2 - Secciones H2 con su contenido asociado (objeto con item-0, item-1, etc.)
    # Estructura: {titulo_h2, contenido_h2}
    # Se extraen con _extract_h2_with_content() que busca H2 y su contenido siguiente
    bloques_contenido_h2 = [
        "//h2[not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')]) and not(ancestor::div[contains(@class, 'bui-footer')]) and not(ancestor::div[contains(@class, 'cookie')]) and not(ancestor::div[contains(@class, 'legal')])]",
        "//div[contains(@class, 'hp-description')]//h2[not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]",
        "//div[contains(@class, 'hotel-description')]//h2[not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]",
        "//section//h2[not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]"
    ]
    
    # bloques_contenido_h3 - XPath para H3 (usado internamente en extracción de contenido)
    # No aparece en el JSON final pero se usa para extraer contenido asociado a H2
    bloques_contenido_h3 = [
        "//h3[not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')]) and not(ancestor::div[contains(@class, 'bui-footer')]) and not(ancestor::div[contains(@class, 'cookie')]) and not(ancestor::div[contains(@class, 'legal')])]",
        "//div[contains(@class, 'hp-description')]//h3[not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]",
        "//div[contains(@class, 'hotel-description')]//h3[not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]",
        "//section//h3[not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]"
    ]
    
    # ========================================
    # CONFIGURACIÓN DE EXCLUSIONES
    # ========================================
    
    # Elementos a excluir siempre (footer, cookies, legal, etc.)
    FOOTER_EXCLUSIONS = [
        "not(ancestor::footer)",
        "not(ancestor::div[contains(@class, 'footer')])",
        "not(ancestor::div[contains(@class, 'bui-footer')])",
        "not(ancestor::div[contains(@class, 'cookie')])",
        "not(ancestor::div[contains(@class, 'legal')])",
        "not(ancestor::div[contains(@class, 'navigation')])"
    ]
    
    # Textos a excluir en frases destacadas
    EXCLUDED_TEXTS = [
        "not(contains(text(), 'Reserva'))",
        "not(contains(text(), 'Guardar'))",
        "not(contains(text(), 'Booking.com'))",
        "not(contains(text(), 'Términos'))",
        "not(contains(text(), 'Política'))",
        "not(contains(text(), 'Cookies'))"
    ]
    
    @classmethod
    def get_xpath_with_exclusions(cls, base_xpath: str) -> str:
        """
        Añade exclusiones de footer a un xpath base
        
        Args:
            base_xpath: XPath base sin exclusiones
            
        Returns:
            XPath con exclusiones de footer añadidas
        """
        exclusions = " and ".join(cls.FOOTER_EXCLUSIONS)
        return f"{base_xpath}[{exclusions}]"
    
    @classmethod
    def get_text_xpath_with_exclusions(cls, base_xpath: str) -> str:
        """
        Añade exclusiones de footer y texto a un xpath base
        
        Args:
            base_xpath: XPath base sin exclusiones
            
        Returns:
            XPath con exclusiones completas añadidas
        """
        all_exclusions = cls.FOOTER_EXCLUSIONS + cls.EXCLUDED_TEXTS
        exclusions = " and ".join(all_exclusions)
        return f"{base_xpath}[{exclusions}]"
