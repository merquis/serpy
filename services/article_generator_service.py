"""
Servicio de Generación de Artículos SEO
"""
import json
import re
from collections import Counter
from statistics import mean
from typing import Dict, List, Any, Optional, Tuple
from slugify import slugify
import openai
import streamlit as st
import logging

logger = logging.getLogger(__name__)

class ArticleGeneratorService:
    """Servicio para generar esquemas y artículos SEO con IA"""
    
    # Stop words por idioma
    STOPWORDS = {
        "es": {"de", "del", "la", "las", "el", "los", "en", "con", "y", "para", "por", "un", "una"},
        "en": {"the", "of", "in", "and", "for", "to", "a", "an", "with"},
        "fr": {"de", "la", "les", "des", "et", "en", "pour", "du", "un", "une"},
        "de": {"der", "die", "das", "und", "mit", "für", "ein", "eine", "von", "in"},
    }
    
    # Precios por modelo (entrada, salida) por 1K tokens
    MODEL_PRICES = {
        "gpt-4.1-mini-2025-04-14": (0.0004, 0.0016),
        "gpt-4.1-2025-04-14": (0.0020, 0.0080),
        "chatgpt-4o-latest": (0.00375, 0.0150),
        "o3-2025-04-16": (0.0100, 0.0400),
        "o3-mini-2025-04-16": (0.0011, 0.0044),
    }
    
    def __init__(self):
        self._client = None
    
    def _get_openai_client(self):
        """Obtiene el cliente de OpenAI"""
        if not self._client:
            api_key = st.secrets["openai"]["api_key"]
            self._client = openai.Client(api_key=api_key)
        return self._client
    
    def generate_article_schema(
        self,
        keyword: str,
        language: str,
        content_type: str,
        model: str = "gpt-4o-mini",
        generate_text: bool = False,
        generate_slug: bool = True,
        competition_data: Optional[bytes] = None,
        temperature: float = 0.9,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0
    ) -> Dict[str, Any]:
        """
        Genera un esquema de artículo SEO optimizado
        
        Args:
            keyword: Palabra clave principal
            language: Idioma del contenido
            content_type: Tipo de contenido (Informativo, Transaccional, etc.)
            model: Modelo de GPT a usar
            generate_text: Si generar textos completos
            generate_slug: Si generar slug del H1
            competition_data: Datos JSON de la competencia
            temperature: Parámetro de temperatura
            top_p: Parámetro top-p
            frequency_penalty: Penalización de frecuencia
            presence_penalty: Penalización de presencia
            
        Returns:
            Esquema del artículo en formato JSON
        """
        # Extraer candidatos de la competencia
        candidates = self._extract_candidates(competition_data) if competition_data else {}
        
        # Construir prompt
        prompt = self._build_prompt(
            keyword, language, content_type,
            generate_text, generate_slug, candidates
        )
        
        # Llamar a OpenAI
        client = self._get_openai_client()
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                max_tokens=3000 if generate_text else 800,
            )
            
            raw_content = response.choices[0].message.content.strip()
            
            # Parsear JSON
            try:
                result = json.loads(raw_content)
            except json.JSONDecodeError:
                # Si falla, intentar extraer JSON del texto
                json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise ValueError("La IA no devolvió un JSON válido")
            
            # Asegurar slug si se pidió
            if generate_slug and "slug" not in result:
                lang_code = self._get_language_code(language)
                result["slug"] = self.make_slug(
                    result.get("title", keyword), 
                    lang_code
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error generando esquema: {e}")
            raise
    
    def _extract_candidates(self, json_bytes: bytes, top_k: int = 25) -> Dict[str, Dict[str, Any]]:
        """Extrae títulos candidatos y estadísticas de la competencia"""
        output = {"h1": {}, "h2": {}, "h3": {}}
        
        if not json_bytes:
            return output
        
        try:
            data = json.loads(json_bytes.decode("utf-8"))
        except Exception:
            return output
        
        for level in ("h1", "h2", "h3"):
            counter = Counter()
            lengths = []
            self._collect_headers(data, level, counter, lengths)
            
            output[level]["titles"] = [title for title, _ in counter.most_common(top_k)]
            output[level]["avg_len"] = mean(lengths) if lengths else 120
        
        return output
    
    def _collect_headers(self, data: Any, level: str, counter: Counter, lengths: List[int]):
        """Recorre recursivamente el JSON y acumula títulos y longitudes"""
        if isinstance(data, dict):
            if data.get("level") == level and data.get("title"):
                title = data["title"].strip()
                counter[title] += 1
                if isinstance(data.get("contenido"), str):
                    lengths.append(len(data["contenido"].split()))
            
            for value in data.values():
                self._collect_headers(value, level, counter, lengths)
                
        elif isinstance(data, list):
            for item in data:
                self._collect_headers(item, level, counter, lengths)
    
    def _build_prompt(
        self,
        keyword: str,
        language: str,
        content_type: str,
        generate_text: bool,
        generate_slug: bool,
        candidates: Dict[str, Dict[str, Any]]
    ) -> str:
        """Construye el prompt para OpenAI"""
        
        # Detalles de estructura
        details = [
            "La clave raíz debe contener: 'title', 'slug' (si se pide), 'contenido', 'total_palabras', 'H1'.",
            "Dentro de 'H1' NO pongas 'children'. Las secciones H2 cuélgalas directamente en la raíz dentro de un array 'H2'.",
            "Cada elemento de 'H2' puede contener opcionalmente un array 'H3'.",
            "NO incluyas 'word_count' en ninguna parte (solo lo usarás internamente para calcular longitudes).",
            "Parafrasa los títulos, ordena por relevancia y asigna longitudes ~30% superiores a la media de la competencia.",
        ]
        
        if generate_slug:
            details.append("Genera 'slug' (kebab-case sin stopwords) usando el H1.")
        
        if generate_text:
            details.append("Añade 'contenido' con un párrafo SEO en H1, cada H2 y cada H3.")
        
        # Contexto de competencia
        def format_context(level: str, count: int):
            titles = candidates.get(level, {}).get("titles", [])[:count]
            return "\n".join(f"- {t}" for t in titles) if titles else "- (vacío)"
        
        competition_context = f"""
### Aparición en competencia
• H1 frecuentes:
{format_context('h1', 5)}

• H2 frecuentes:
{format_context('h2', 10)}

• H3 frecuentes:
{format_context('h3', 10)}"""
        
        instructions = "\n".join(f"- {d}" for d in details)
        
        return f"""
Eres consultor SEO senior especializado en arquitectura de contenidos.
Genera el **mejor** esquema H1/H2/H3 para posicionar en top-5 Google la keyword "{keyword}" (idioma {language}).

{competition_context}

Instrucciones:
{instructions}

Devuelve únicamente un JSON válido. Empieza directamente con '{{'.""".strip()
    
    def make_slug(self, title: str, lang_code: str = "es") -> str:
        """Genera slug kebab-case sin stopwords ni tildes"""
        words = re.sub(r"[^\w\s-]", "", title.lower()).split()
        cleaned = [w for w in words if w not in self.STOPWORDS.get(lang_code, set())]
        return slugify(" ".join(cleaned))
    
    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> Tuple[float, float]:
        """
        Estima el coste de la generación
        
        Returns:
            Tupla (coste_entrada, coste_salida) en USD
        """
        price_in, price_out = self.MODEL_PRICES.get(model, (0, 0))
        cost_in = (input_tokens / 1000) * price_in
        cost_out = (output_tokens / 1000) * price_out
        return cost_in, cost_out
    
    def extract_keyword_from_json(self, json_bytes: bytes) -> Optional[str]:
        """Extrae la keyword principal de un JSON de competencia"""
        if not json_bytes:
            return None
        
        try:
            data = json.loads(json_bytes.decode("utf-8"))
            # Buscar en varios campos posibles
            keyword = data.get("busqueda") or data.get("keyword") or data.get("query")
            return keyword
        except Exception:
            return None
    
    def _get_language_code(self, language: str) -> str:
        """Convierte nombre de idioma a código"""
        lang_map = {
            "Español": "es",
            "Inglés": "en", 
            "Francés": "fr",
            "Alemán": "de"
        }
        return lang_map.get(language, "es") 