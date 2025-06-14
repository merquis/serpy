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
        # OpenAI
        "gpt-4.1-mini-2025-04-14": (0.0004, 0.0016),
        "gpt-4.1-2025-04-14": (0.0020, 0.0080),
        "chatgpt-4o-latest": (0.0050, 0.0200),
        "o3-2025-04-16": (0.0020, 0.0080),
        "o3-mini-2025-04-16": (0.0011, 0.0044),
        # Claude
        "claude-opus-4-20250514": (0.0150, 0.0750),
        "claude-sonnet-4-20250514": (0.0030, 0.0150),
        "claude-3-7-sonnet-20250219": (0.0030, 0.0150),
        "claude-3-7-sonnet-latest": (0.0030, 0.0150),
        "claude-3-5-haiku-20241022": (0.0008, 0.0040),
        "claude-3-5-haiku-latest": (0.0008, 0.0040),
        # Google Gemini (precios por 1K tokens)
        "gemini-2.0-flash": (0.000075, 0.0003),
        "gemini-2.5-flash-preview-05-20": (0.000075, 0.0003),
        "gemini-2.5-pro-preview-06-05": (0.0025, 0.010),
    }
    
    def __init__(self):
        self._openai_client = None
        self._claude_client = None
        self._gemini_client = None
    
    def _get_openai_client(self):
        """Obtiene el cliente de OpenAI"""
        if not self._openai_client:
            from config.settings import settings
            api_key = settings.openai_api_key
            self._openai_client = openai.Client(api_key=api_key)
        return self._openai_client
    
    def _get_claude_client(self):
        """Obtiene el cliente de Claude"""
        if not self._claude_client:
            try:
                from anthropic import AsyncAnthropic
                from config.settings import settings
                api_key = settings.claude_api_key
                self._claude_client = AsyncAnthropic(api_key=api_key)
            except ImportError:
                logger.error("Anthropic no está instalado. Instala con: pip install anthropic")
                raise
        return self._claude_client
    
    def _get_gemini_client(self):
        """Obtiene el cliente de Gemini"""
        if not self._gemini_client:
            try:
                import google.generativeai as genai
                from config.settings import settings
                api_key = settings.gemini_api_key
                genai.configure(api_key=api_key)
                self._gemini_client = genai
            except ImportError:
                logger.error("Google Generative AI no está instalado. Instala con: pip install google-generativeai")
                raise
        return self._gemini_client
    
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
        
        try:
            # Detectar el tipo de modelo
            if model.startswith("claude"):
                # Usar Claude
                raw_content = self._generate_with_claude(
                    prompt=prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=3000 if generate_text else 800
                )
            elif model.startswith("gemini"):
                # Usar Gemini
                raw_content = self._generate_with_gemini(
                    prompt=prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=3000 if generate_text else 800
                )
            else:
                # Usar OpenAI
                client = self._get_openai_client()
                
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
                # Con response_schema, Gemini ya devuelve JSON válido
                result = json.loads(raw_content)
            except json.JSONDecodeError as e:
                logger.error(f"Error parseando JSON: {e}")
                logger.error(f"Contenido raw: {raw_content[:500]}...")  # Log primeros 500 chars
                
                # Si falla, intentar extraer JSON del texto
                json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise ValueError(f"La IA no devolvió un JSON válido. Error: {str(e)}")
            
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

IMPORTANTE: Devuelve ÚNICAMENTE un objeto JSON válido, sin texto adicional antes o después. El JSON debe empezar con {{ y terminar con }}. No incluyas explicaciones, comentarios ni formato markdown.""".strip()
    
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
    
    def _generate_with_claude(self, prompt: str, model: str, temperature: float, max_tokens: int) -> str:
        """Genera contenido usando Claude"""
        import asyncio
        
        async def generate():
            client = self._get_claude_client()
            
            response = await client.messages.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.content[0].text
        
        # Ejecutar de forma síncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(generate())
        loop.close()
        
        return result
    
    def _generate_with_gemini(self, prompt: str, model: str, temperature: float, max_tokens: int) -> str:
        """Genera contenido usando Gemini"""
        try:
            genai = self._get_gemini_client()
            
            # Definir el esquema de respuesta esperado según la documentación
            response_schema = {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING"},
                    "slug": {"type": "STRING"},
                    "contenido": {"type": "STRING"},
                    "total_palabras": {"type": "INTEGER"},
                    "H1": {
                        "type": "OBJECT",
                        "properties": {
                            "title": {"type": "STRING"},
                            "contenido": {"type": "STRING"}
                        }
                    },
                    "H2": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "title": {"type": "STRING"},
                                "contenido": {"type": "STRING"},
                                "H3": {
                                    "type": "ARRAY",
                                    "items": {
                                        "type": "OBJECT",
                                        "properties": {
                                            "title": {"type": "STRING"},
                                            "contenido": {"type": "STRING"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "propertyOrdering": ["title", "slug", "contenido", "total_palabras", "H1", "H2"]
            }
            
            # Configuración de generación
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
                "response_mime_type": "application/json",
                "response_schema": response_schema
            }
            
            # Crear el modelo
            model_name = model if not model.startswith('gemini') else model
            gemini_model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=generation_config
            )
            
            logger.info(f"Llamando a Gemini con modelo: {model_name}")
            
            # Generar respuesta
            response = gemini_model.generate_content(prompt)
            
            # Obtener el texto de la respuesta
            if response and response.text:
                return response.text
            else:
                logger.error(f"Respuesta de Gemini sin texto: {response}")
                raise ValueError("La respuesta de Gemini no contiene texto")
                
        except Exception as e:
            logger.error(f"Error en _generate_with_gemini: {str(e)}")
            raise
