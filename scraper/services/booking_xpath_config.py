"""
Configuración centralizada de XPath para extracción de datos de Booking.com
Este archivo contiene todos los selectores XPath organizados por categorías
"""

class BookingXPathConfig:
    """Configuración centralizada de todos los XPath para Booking.com"""
    
    # ========================================
    # INFORMACIÓN BÁSICA DEL HOTEL
    # ========================================
    
    HOTEL_NAME = [
        "//h2[contains(@class, 'pp-header__title')]/text()",
        "//h1[@id='hp_hotel_name']/text()",
        "//h1[contains(@class, 'hotel-name')]/text()"
    ]
    
    # ========================================
    # PRECIOS
    # ========================================
    
    PRICE = [
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
    
    # ========================================
    # VALORACIONES Y OPINIONES
    # ========================================
    
    GLOBAL_RATING = [
        "//div[@data-testid='review-score-right-component']//div[contains(@class, 'dff2e52086')]/text()",
        "//div[contains(@class, 'bui-review-score__badge')]/text()",
        "//span[contains(@class, 'review-score-badge')]/text()"
    ]
    
    REVIEWS_COUNT = [
        "//div[@data-testid='review-score-right-component']//div[contains(@class, 'fb14de7f14')]/text()",
        "//div[contains(@class, 'bui-review-score__text')]/text()",
        "//span[contains(@class, 'review-count')]/text()"
    ]
    
    # Valoraciones detalladas por categoría
    DETAILED_RATINGS = {
        'personal': [
            "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and (contains(translate(text(), 'PERSONAL', 'personal'), 'personal') or contains(translate(text(), 'STAFF', 'staff'), 'staff'))]/following-sibling::*//div[contains(@class, 'f87e152973')]/text()",
            "//li//p[contains(@class, 'review_score_name') and (contains(translate(text(), 'PERSONAL', 'personal'), 'personal') or contains(translate(text(), 'STAFF', 'staff'), 'staff'))]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
        ],
        'limpieza': [
            "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and contains(translate(text(), 'LIMPIEZA', 'limpieza'), 'limpieza')]/following-sibling::*//div[contains(@class, 'f87e152973')]/text()",
            "//li//p[contains(@class, 'review_score_name') and contains(translate(text(), 'LIMPIEZA', 'limpieza'), 'limpieza')]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
        ],
        'confort': [
            "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and contains(translate(text(), 'CONFORT', 'confort'), 'confort')]/following-sibling::*//div[contains(@class, 'f87e152973')]/text()",
            "//li//p[contains(@class, 'review_score_name') and contains(translate(text(), 'CONFORT', 'confort'), 'confort')]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
        ],
        'ubicacion': [
            "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and (contains(translate(text(), 'UBICACIÓN', 'ubicacion'), 'ubicacion') or contains(translate(text(), 'UBICACION', 'ubicacion'), 'ubicacion'))]/following-sibling::*//div[contains(@class, 'f87e152973')]/text()",
            "//li//p[contains(@class, 'review_score_name') and (contains(translate(text(), 'UBICACIÓN', 'ubicacion'), 'ubicacion') or contains(translate(text(), 'UBICACION', 'ubicacion'), 'ubicacion'))]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
        ],
        'instalaciones_servicios': [
            "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and contains(text(), 'instalaciones')]/following-sibling::*//div[contains(@class, 'f87e152973')]/text()",
            "//li//p[contains(@class, 'review_score_name') and contains(text(), 'instalaciones')]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
        ],
        'calidad_precio': [
            "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and contains(text(), 'calidad')]/following-sibling::*//div[contains(@class, 'f87e152973')]/text()",
            "//li//p[contains(@class, 'review_score_name') and contains(text(), 'calidad')]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
        ],
        'wifi': [
            "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and contains(text(), 'wifi')]/following-sibling::*//div[contains(@class, 'f87e152973')]/text()",
            "//li//p[contains(@class, 'review_score_name') and contains(text(), 'wifi')]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
        ]
    }
    
    # ========================================
    # UBICACIÓN Y DIRECCIÓN
    # ========================================
    
    ADDRESS = [
        "//a[contains(@data-atlas-latlng, ',')]/following-sibling::span[1]//button//div/text()"
    ]
    
    # ========================================
    # ESTADO DEL ALOJAMIENTO
    # ========================================
    
    PREFERRED_STATUS = [
        "//span[@data-testid='preferred-icon']",
        "//div[contains(@class, 'preferred-badge')]",
        "//span[contains(@class, 'preferred')]"
    ]
    
    # ========================================
    # FRASES DESTACADAS (excluyendo footer)
    # ========================================
    
    HIGHLIGHTS = [
        "//div[@data-testid='PropertyHighlightList-wrapper']//ul/li//div[contains(@class, 'b99b6ef58f')]//span[contains(@class, 'f6b6d2a959') and not(contains(text(), 'Reserva')) and not(contains(text(), 'Guardar')) and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]/text()",
        "//div[contains(@class, 'hp--desc_highlights')]//div[contains(@class,'ph-item-copy-container')]//span[not(contains(text(), 'Reserva')) and not(contains(text(), 'Guardar')) and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]/text()",
        "//div[contains(@class, 'property-highlights')]//span[not(contains(text(), 'Reserva')) and not(contains(text(), 'Guardar')) and not(ancestor::button) and not(ancestor::a) and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]/text()",
        "//div[contains(@class, 'hp_desc_important_facilities')]//span[not(contains(text(), 'Reserva')) and not(contains(text(), 'Guardar')) and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]/text()"
    ]
    
    # ========================================
    # ESTRUCTURA DE CONTENIDO (excluyendo footer)
    # ========================================
    
    H2_ELEMENTS = [
        "//h2[not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')]) and not(ancestor::div[contains(@class, 'bui-footer')]) and not(ancestor::div[contains(@class, 'cookie')]) and not(ancestor::div[contains(@class, 'legal')])]",
        "//div[contains(@class, 'hp-description')]//h2[not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]",
        "//div[contains(@class, 'hotel-description')]//h2[not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]",
        "//section//h2[not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]"
    ]
    
    H3_ELEMENTS = [
        "//h3[not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')]) and not(ancestor::div[contains(@class, 'bui-footer')]) and not(ancestor::div[contains(@class, 'cookie')]) and not(ancestor::div[contains(@class, 'legal')])]",
        "//div[contains(@class, 'hp-description')]//h3[not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]",
        "//div[contains(@class, 'hotel-description')]//h3[not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]",
        "//section//h3[not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]"
    ]
    
    # ========================================
    # SERVICIOS E INSTALACIONES (excluyendo footer)
    # ========================================
    
    FACILITIES = [
        "//div[contains(@class, 'hotel-facilities__list') and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])] li .bui-list__description/text()",
        "//div[contains(@class, 'facilitiesChecklistSection') and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])] li span/text()",
        "//div[contains(@class, 'hp_desc_important_facilities') and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])] li/text()",
        "//div[@data-testid='property-most-popular-facilities-wrapper' and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])] div[@data-testid='facility-badge'] span/text()",
        "//div[@data-testid='facilities-block' and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])] li div[2] span/text()",
        "//div[@data-testid='property-most-popular-facilities-wrapper' and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]//span[contains(@class, 'db29ecfbe2')]/text()",
        "//div[contains(@class, 'hp_desc_important_facilities') and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]//span/text()",
        "//ul[contains(@class, 'hotel-facilities-group') and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]//span/text()",
        "//div[contains(@class, 'facilitiesChecklistSection') and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]//div[contains(@class, 'bui-list__description')]/text()",
        "//div[@data-testid='facilities-block' and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]//span[contains(@class, 'db29ecfbe2')]/text()",
        "//div[contains(@class, 'hp-description') and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]//li/text()",
        "//div[contains(@class, 'important_facilities') and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]//span/text()",
        "//span[contains(@class, 'hp-desc-highlighted-text') and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]/text()"
    ]
    
    # ========================================
    # IMÁGENES
    # ========================================
    
    IMAGES = [
        "//a[@data-fancybox='gallery'] img",
        "//div[contains(@class, 'bh-photo-grid-item')] img",
        "//img[contains(@data-src, 'xdata/images/hotel')]",
        "//img[contains(@src, 'bstatic.com/xdata/images/hotel')]"
    ]
    
    FEATURED_IMAGE = [
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
    # DESCRIPCIÓN Y CONTENIDO PRINCIPAL
    # ========================================
    
    DESCRIPTION = [
        "//div[contains(@class, 'hp-description') and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]//p/text()",
        "//div[contains(@class, 'hotel-description') and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]//p/text()",
        "//div[@data-testid='property-description' and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]//text()",
        "//section[contains(@class, 'description') and not(ancestor::footer) and not(ancestor::div[contains(@class, 'footer')])]//p/text()"
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
