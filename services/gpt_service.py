"""
Servicio GPT - Gestión de interacciones con OpenAI
"""
import openai
import json
from typing import Dict, List, Any, Optional, Tuple
from config import config
import re
from collections import Counter
from statistics import mean
from slugify import slugify
import logging

logger = logging.getLogger(__name__)

class GPTService:
    """Servicio para interacciones con OpenAI GPT"""
    
    # Stopwords por idioma
    STOPWORDS = {
        "es": {"de", "del", "la", "las", "el", "los", "en", "con", "y", "para", "por", "un", "una"},
        "en": {"the", "of", "in", "and", "for", "to", "a", "an", "with"},
        "fr": {"de", "la", "les", "des", "et", "en", "pour", "du", "un", "une"},
        "de": {"der", "die", "das", "und", "mit", "für", "ein", "eine", "von", "in"},
    }
    
    # Precios de modelos (por 1K tokens)
    MODEL_PRICES = {
        "gpt-4.1-mini-2025-04-14": (0.0004, 0.0016),
        "gpt-4.1-2025-04-14": (0.0020, 0.0080),
        "chatgpt-4o-latest": (0.00375, 0.0150),
        "o3-2025-04-16": (0.0100, 0.0400),
        "o3-mini-2025-04-16": (0.0011, 0.0044),
    }
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.openai_api_key
        self.client = openai.Client(api_key=self.api_key)
    
    def generate_seo_schema(
        self,
        keyword: str,
        language: str,
        content_type: str,
        competitors_data: Optional[Dict[str, Any]] = None,
        model: str = "gpt-4.1-mini-2025-04-14",
        temperature: float = 0.9,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        generate_text: bool = False,
        generate_slug: bool = True
    ) -> Dict[str, Any]:
        """
        Genera un esquema SEO optimizado basado en análisis de competencia
        
        Args:
            keyword: Palabra clave principal
            language: Idioma del contenido
            content_type: Tipo de contenido (Informativo, Transaccional, etc.)
            competitors_data: Datos extraídos de competidores
            model: Modelo GPT a usar
            temperature: Control de creatividad
            top_p: Control de diversidad
            frequency_penalty: Penalización por frecuencia
            presence_penalty: Penalización por presencia
            generate_text: Si debe generar contenido de texto
            generate_slug: Si debe generar slug para H1
            
        Returns:
            Esquema SEO estructurado en formato JSON
        """
        # Construir prompt
        prompt = self._build_seo_prompt(
            keyword, 
            language, 
            content_type, 
            competitors_data,
            generate_text,
            generate_slug
        )
        
        # Estimar tokens
        estimated_tokens = 3000 if generate_text else 800
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                max_tokens=estimated_tokens
            )
            
            content = response.choices[0].message.content.strip()
            
            # Intentar parsear como JSON
            try:
                result = json.loads(content)
                
                # Asegurar slug si se pidió y no existe
                if generate_slug and "slug" not in result and "title" in result:
                    result["slug"] = self.make_slug(result["title"], self._get_lang_code(language))
                
                return result
                
            except Exception:
                logger.error("La respuesta de GPT no es JSON válido")
                return {"error": "Respuesta no válida", "raw_response": content}
                
        except Exception as e:
            logger.error(f"Error al llamar a OpenAI: {e}")
            raise
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4.1-mini-2025-04-14",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Genera una respuesta de chat usando GPT
        
        Args:
            messages: Historial de mensajes
            model: Modelo a usar
            temperature: Control de creatividad
            max_tokens: Máximo de tokens en la respuesta
            
        Returns:
            Respuesta generada
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error en chat completion: {e}")
            raise
    
    def estimate_cost(
        self, 
        model: str, 
        input_tokens: int, 
        output_tokens: int
    ) -> Tuple[float, float]:
        """
        Estima el costo de una llamada a GPT
        
        Args:
            model: Modelo a usar
            input_tokens: Número de tokens de entrada
            output_tokens: Número de tokens de salida
            
        Returns:
            Tupla (costo_entrada, costo_salida)
        """
        price_in, price_out = self.MODEL_PRICES.get(model, (0, 0))
        cost_in = (input_tokens / 1000) * price_in
        cost_out = (output_tokens / 1000) * price_out
        return cost_in, cost_out
    
    def make_slug(self, title: str, lang_code: str = "es") -> str:
        """
        Genera un slug SEO-friendly removiendo stopwords
        
        Args:
            title: Título a convertir
            lang_code: Código de idioma
            
        Returns:
            Slug en formato kebab-case
        """
        # Limpiar y dividir en palabras
        words = re.sub(r"[^\w\s-]", "", title.lower()).split()
        
        # Remover stopwords
        stopwords = self.STOPWORDS.get(lang_code, set())
        cleaned_words = [w for w in words if w not in stopwords]
        
        # Generar slug
        return slugify(" ".join(cleaned_words))
    
    def analyze_competitors(
        self, 
        json_data: Dict[str, Any], 
        top_k: int = 25
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analiza datos de competidores para extraer patrones
        
        Args:
            json_data: Datos JSON de competidores
            top_k: Número de títulos más frecuentes a considerar
            
        Returns:
            Diccionario con títulos frecuentes y longitudes promedio por nivel
        """
        result = {"h1": {}, "h2": {}, "h3": {}}
        
        for level in ["h1", "h2", "h3"]:
            titles_counter = Counter()
            lengths = []
            
            # Extraer títulos y longitudes
            self._extract_titles_recursive(json_data, level, titles_counter, lengths)
            
            # Top títulos más frecuentes
            result[level]["titles"] = [title for title, _ in titles_counter.most_common(top_k)]
            
            # Longitud promedio
            result[level]["avg_length"] = mean(lengths) if lengths else 120
            
        return result
    
    def _build_seo_prompt(
        self,
        keyword: str,
        language: str,
        content_type: str,
        competitors_data: Optional[Dict[str, Any]],
        generate_text: bool,
        generate_slug: bool
    ) -> str:
        """Construye el prompt para generar esquema SEO"""
        details = [
            "La clave raíz debe contener: 'title', 'slug' (si se pide), 'contenido', 'total_palabras', 'H1'.",
            "Dentro de 'H1' NO pongas 'children'. Las secciones H2 cuélgalas directamente en la raíz dentro de un array 'H2'.",
            "Cada elemento de 'H2' puede contener opcionalmente un array 'H3'.",
            "NO incluyas 'word_count' en ninguna parte (solo lo usarás internamente para calcular longitudes).",
            "Parafrasa los títulos, ordena por relevancia y asigna longitudes ~30% superiores a la media de la competencia."
        ]
        
        if generate_slug:
            details.append("Genera 'slug' (kebab-case sin stopwords) usando el H1.")
        
        if generate_text:
            details.append("Añade 'contenido' con un párrafo SEO en H1, cada H2 y cada H3.")
        
        # Contexto de competencia
        context = ""
        if competitors_data:
            h1_titles = "\n".join(f"- {t}" for t in competitors_data.get("h1", {}).get("titles", [])[:5])
            h2_titles = "\n".join(f"- {t}" for t in competitors_data.get("h2", {}).get("titles", [])[:10])
            h3_titles = "\n".join(f"- {t}" for t in competitors_data.get("h3", {}).get("titles", [])[:10])
            
            context = f"""
### Aparición en competencia
• H1 frecuentes:
{h1_titles}
• H2 frecuentes:
{h2_titles}
• H3 frecuentes:
{h3_titles}"""
        
        instructions = "\n".join(f"- {d}" for d in details)
        
        return f"""
Eres consultor SEO senior especializado en arquitectura de contenidos.
Genera el **mejor** esquema H1/H2/H3 para posicionar en top-5 Google la keyword "{keyword}" (idioma {language}).

{context}

Instrucciones:
{instructions}

Devuelve únicamente un JSON válido. Empieza directamente con '{{'.
""".strip()
    
    def _extract_titles_recursive(
        self, 
        data: Any, 
        level: str, 
        counter: Counter, 
        lengths: List[int]
    ):
        """Extrae títulos y longitudes de forma recursiva"""
        if isinstance(data, dict):
            if data.get("level") == level and data.get("titulo"):
                title = data["titulo"].strip()
                counter[title] += 1
                if isinstance(data.get("contenido"), str):
                    lengths.append(len(data["contenido"].split()))
            
            for value in data.values():
                self._extract_titles_recursive(value, level, counter, lengths)
                
        elif isinstance(data, list):
            for item in data:
                self._extract_titles_recursive(item, level, counter, lengths)
    
    def _get_lang_code(self, language: str) -> str:
        """Convierte nombre de idioma a código"""
        lang_map = {
            "Español": "es",
            "Inglés": "en",
            "Francés": "fr",
            "Alemán": "de"
        }
        return lang_map.get(language, "es") 