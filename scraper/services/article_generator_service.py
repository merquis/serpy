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
                from anthropic import Anthropic  # Usar cliente síncrono
                from config.settings import settings
                api_key = settings.claude_api_key
                logger.info(f"Inicializando cliente Claude con API key: {api_key[:10]}...")
                self._claude_client = Anthropic(api_key=api_key)
            except ImportError:
                logger.error("Anthropic no está instalado. Instala con: pip install anthropic")
                raise
            except Exception as e:
                logger.error(f"Error inicializando cliente Claude: {e}")
                raise
        return self._claude_client
    
    def _get_gemini_client(self):
        """Obtiene el cliente de Gemini"""
        if not self._gemini_client:
            try:
                from google import genai
                from config.settings import settings
                api_key = settings.gemini_api_key
                self._gemini_client = genai.Client(api_key=api_key)
            except ImportError:
                logger.error("Google GenAI no está instalado. Instala con: pip install google-genai")
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
                # Usar Claude sin límites
                raw_content = self._generate_with_claude(
                    prompt=prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=None
                )
            elif model.startswith("gemini"):
                # Usar Gemini sin límites
                raw_content = self._generate_with_gemini(
                    prompt=prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=None
                )
            else:
                # Usar OpenAI sin límites
                client = self._get_openai_client()
                
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    top_p=top_p,
                    frequency_penalty=frequency_penalty,
                    presence_penalty=presence_penalty,
                    # Sin límite de tokens
                )
                
                raw_content = response.choices[0].message.content.strip()
            
            # Parsear JSON
            try:
                # Con response_schema, Gemini ya devuelve JSON válido
                result = json.loads(raw_content)
            except json.JSONDecodeError as e:
                logger.error(f"Error parseando JSON: {e}")
                logger.error(f"Contenido raw completo:\n{raw_content}")  # Log completo para debug
                
                # Para Gemini, intentar usar el objeto parsed si está disponible
                if model.startswith("gemini") and hasattr(locals().get('response', None), 'parsed'):
                    try:
                        result = locals()['response'].parsed
                        if result:
                            # Convertir el objeto Pydantic a dict
                            result = result.dict() if hasattr(result, 'dict') else result
                            logger.info("Usando respuesta parsed de Gemini")
                            return result
                    except Exception as parse_error:
                        logger.error(f"Error usando parsed: {parse_error}")
                
                # Si falla, intentar extraer JSON del texto
                json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        raise ValueError(f"La IA no devolvió un JSON válido. Error: {str(e)}")
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
    
    def generate_hotel_slogan(
        self,
        content: str,
        title: str,
        search_term: str = "",
        model: str = "claude-3-5-haiku-latest"
    ) -> str:
        """
        Genera un slogan cautivador para un hotel usando IA con reintentos y fallback
        
        Args:
            content: Descripción completa del hotel
            title: Título del hotel
            search_term: Término de búsqueda del cliente
            model: Modelo de Claude a usar
            
        Returns:
            Slogan atractivo de máximo 80 caracteres
        """
        prompt = f"""
Eres un experto en marketing de lujo y copywriting hotelero. Tu misión es crear una frase IRRESISTIBLE que haga que los clientes quieran reservar inmediatamente.

INFORMACIÓN DEL HOTEL:
Búsqueda del cliente: "{search_term}"
Hotel: "{title}"

DESCRIPCIÓN COMPLETA:
{content[:800]}

INSTRUCCIONES:
Crea una frase de máximo 80 caracteres que:
✨ Sea IRRESISTIBLE y genere deseo inmediato de reservar
✨ Destaque la característica más exclusiva y única
✨ Use lenguaje emocional y sensorial
✨ Transmita lujo, exclusividad y experiencia única
✨ Sea memorable y diferente a frases típicas de hoteles

EJEMPLOS DE ESTILO (NO copies, inspírate):
- "Donde el lujo se encuentra con el paraíso atlántico"
- "Tu refugio exclusivo entre acantilados y estrellas Michelin"
- "Vive la experiencia que solo unos pocos conocen"

Devuelve ÚNICAMENTE la frase, sin comillas ni explicaciones.
"""
        
        # Lista de modelos a intentar en orden: OpenAI primero (con fondos), luego Gemini, luego Claude
        models_to_try = [
            "chatgpt-4o-latest",            # OpenAI GPT-4o (primero ahora que hay fondos)
            "gemini-2.5-pro-preview-06-05", # Google Gemini Pro
            "claude-sonnet-4-20250514"      # Claude Sonnet 4 (último por sobrecarga)
        ]
        
        # Si se especificó un modelo diferente, usarlo primero
        if model not in models_to_try:
            models_to_try.insert(0, model)
        
        for attempt, current_model in enumerate(models_to_try):
            try:
                logger.info(f"Intento {attempt + 1}: Generando slogan con modelo {current_model}")
                
                if current_model.startswith("claude"):
                    # Intentar con Claude
                    slogan = self._generate_with_claude(
                        prompt=prompt,
                        model=current_model,
                        temperature=0.9,
                        max_tokens=60
                    ).strip()
                elif current_model.startswith("gemini"):
                    # Intentar con Gemini
                    slogan = self._generate_with_gemini(
                        prompt=prompt,
                        model=current_model,
                        temperature=0.9,
                        max_tokens=60
                    ).strip()
                else:
                    # OpenAI (gpt, chatgpt, etc.)
                    client = self._get_openai_client()
                    response = client.chat.completions.create(
                        model=current_model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.9,
                        max_tokens=60
                    )
                    slogan = response.choices[0].message.content.strip()
                
                # Validar longitud
                if len(slogan) > 80:
                    slogan = slogan[:77] + "..."
                
                logger.info(f"✅ Slogan generado exitosamente con {current_model}: '{slogan}'")
                return slogan
                
            except Exception as e:
                error_type = type(e).__name__
                logger.warning(f"Intento {attempt + 1} falló con {current_model}: {error_type} - {str(e)}")
                
                # Si es el último modelo, retornar un slogan por defecto
                if attempt == len(models_to_try) - 1:
                    logger.error("Todos los modelos fallaron. Usando slogan por defecto.")
                    # Generar un slogan básico basado en el título
                    if "5*" in title or "5 estrellas" in title:
                        return "Tu experiencia de lujo te espera"
                    elif "4*" in title or "4 estrellas" in title:
                        return "Confort y calidad en el paraíso"
                    else:
                        return "Tu refugio perfecto para unas vacaciones inolvidables"
                
                # Esperar un poco antes del siguiente intento
                import time
                time.sleep(1)
        
        return ""
    
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
    
    def _generate_with_claude(self, prompt: str, model: str, temperature: float, max_tokens: Optional[int]) -> str:
        """Genera contenido usando Claude (versión síncrona)"""
        try:
            client = self._get_claude_client()
            
            # Claude requiere un max_tokens, usar el máximo permitido si es None
            if max_tokens is None:
                max_tokens = 4096  # Máximo para Claude
            
            logger.info(f"=== LLAMADA A CLAUDE ===")
            logger.info(f"Modelo: {model}")
            logger.info(f"Temperature: {temperature}")
            logger.info(f"Max tokens: {max_tokens}")
            logger.info(f"Prompt (primeros 300 chars): {prompt[:300]}...")
            
            # Verificar que el cliente está inicializado
            if not client:
                raise ValueError("Cliente Claude no inicializado")
            
            # Llamada síncrona directa
            response = client.messages.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Verificar respuesta
            if not response or not response.content:
                raise ValueError("Respuesta vacía de Claude")
            
            result = response.content[0].text
            logger.info(f"=== RESPUESTA DE CLAUDE ===")
            logger.info(f"Longitud respuesta: {len(result)} caracteres")
            logger.info(f"Respuesta (primeros 200 chars): {result[:200]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"=== ERROR EN CLAUDE ===")
            logger.error(f"Tipo de error: {type(e).__name__}")
            logger.error(f"Mensaje de error: {str(e)}")
            import traceback
            logger.error(f"Traceback completo:\n{traceback.format_exc()}")
            raise
    
    def _generate_with_gemini(self, prompt: str, model: str, temperature: float, max_tokens: Optional[int]) -> str:
        """Genera contenido usando Gemini"""
        try:
            # Detectar si es para generar JSON o texto simple
            is_json_request = "JSON" in prompt and "{" in prompt
            
            if is_json_request:
                # Lógica para generar esquemas JSON
                from pydantic import BaseModel
                from typing import List, Optional
                
                # Definir el esquema usando Pydantic
                class H3Item(BaseModel):
                    title: str
                    contenido: str
                
                class H2Item(BaseModel):
                    title: str
                    contenido: str
                    H3: Optional[List[H3Item]] = []
                
                class H1Item(BaseModel):
                    title: str
                    contenido: str
                
                class ArticleSchema(BaseModel):
                    title: str
                    slug: str
                    contenido: str
                    total_palabras: int
                    H1: H1Item
                    H2: List[H2Item]
                
                # Configuración para JSON
                config = {
                    "response_mime_type": "application/json",
                    "response_schema": ArticleSchema,
                    "temperature": temperature,
                }
            else:
                # Configuración para texto simple (slogans)
                config = {
                    "temperature": temperature,
                }
            
            # Solo agregar max_output_tokens si no es None
            if max_tokens is not None:
                config["max_output_tokens"] = max_tokens
            
            # Obtener el cliente
            client = self._get_gemini_client()
            
            logger.info(f"=== LLAMADA A GEMINI ===")
            logger.info(f"Modelo: {model}")
            logger.info(f"Temperature: {temperature}")
            logger.info(f"Max tokens: {max_tokens}")
            logger.info(f"Tipo de respuesta: {'JSON' if is_json_request else 'Texto'}")
            logger.info(f"Prompt (primeros 300 chars): {prompt[:300]}...")
            
            # Generar contenido
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )
            
            if is_json_request and hasattr(response, 'parsed') and response.parsed:
                logger.info(f"Usando respuesta parsed de Gemini")
                # Convertir el objeto Pydantic a JSON string
                result = response.parsed
                if hasattr(result, 'model_dump_json'):
                    return result.model_dump_json()
                elif hasattr(result, 'json'):
                    return result.json()
                else:
                    # Si es una lista de objetos
                    import json
                    if isinstance(result, list):
                        return json.dumps([item.dict() if hasattr(item, 'dict') else item for item in result])
                    else:
                        return json.dumps(result.dict() if hasattr(result, 'dict') else result)
            
            # Para texto simple o si no hay parsed
            if response and hasattr(response, 'text'):
                result = response.text
                if result:  # Verificar que result no sea None
                    logger.info(f"=== RESPUESTA DE GEMINI ===")
                    logger.info(f"Longitud respuesta: {len(result)} caracteres")
                    logger.info(f"Respuesta (primeros 200 chars): {result[:200]}...")
                    return result
                else:
                    logger.error(f"Gemini devolvió texto vacío o None")
                    raise ValueError("Gemini devolvió una respuesta vacía")
            else:
                logger.error(f"Respuesta de Gemini sin texto ni parsed")
                raise ValueError("La respuesta de Gemini no contiene texto ni objeto parsed")
                
        except Exception as e:
            logger.error(f"=== ERROR EN GEMINI ===")
            logger.error(f"Tipo de error: {type(e).__name__}")
            logger.error(f"Mensaje de error: {str(e)}")
            import traceback
            logger.error(f"Traceback completo:\n{traceback.format_exc()}")
            raise
