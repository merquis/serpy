"""
Servicio de Chat con GPT, Claude y Gemini
"""
import json
import zipfile
import pandas as pd
import pytesseract
import fitz  # PyMuPDF
import docx
import io
from PIL import Image
from typing import List, Dict, Any, Optional, Tuple
import openai
import streamlit as st
import logging
from lingua import Language, LanguageDetectorBuilder

logger = logging.getLogger(__name__)

class ChatService:
    """Servicio para gestionar conversaciones con GPT"""
    
    # Idiomas soportados para detección
    SUPPORTED_LANGUAGES = [
        Language.SPANISH,
        Language.ENGLISH,
        Language.FRENCH,
        Language.GERMAN
    ]
    
    # Precios por modelo (entrada, salida) por 1M tokens en USD.
    MODEL_PRICES = {
        # OpenAI (precios por 1M tokens según documentación oficial)
        "gpt-4.1-mini-2025-04-14": (0.40, 1.60),  # GPT-4.1 mini
        "gpt-4.1-2025-04-14": (2.00, 8.00),  # GPT-4.1
        "chatgpt-4o-latest": (5.00, 20.00),  # Asumiendo que es GPT-4o
        "o3-2025-04-16": (2.00, 8.00),  # OpenAI o3
        "o3-mini-2025-04-16": (1.10, 4.40),  # OpenAI o4-mini (en la web aparece como o4-mini)
        # Claude (precios por 1M tokens según documentación oficial)
        "claude-opus-4-20250514": (15.00, 75.00),  # Claude Opus 4
        "claude-sonnet-4-20250514": (3.00, 15.00),  # Claude Sonnet 4
        "claude-3-7-sonnet-20250219": (3.00, 15.00),  # Claude Sonnet 3.7
        "claude-3-7-sonnet-latest": (3.00, 15.00),  # Claude Sonnet 3.7 latest
        "claude-3-5-haiku-20241022": (0.80, 4.00),  # Claude Haiku 3.5
        "claude-3-5-haiku-latest": (0.80, 4.00),  # Claude Haiku 3.5 latest
        # Google Gemini (precios por 1M tokens según documentación oficial)
        "gemini-2.0-flash": (0.075, 0.30),  # Gemini 2.0 Flash (estable)
        "gemini-2.5-flash-preview-05-20": (0.075, 0.30),  # Gemini 2.5 Flash Preview
        "gemini-2.5-pro-preview-06-05": (2.50, 10.00),  # Gemini 2.5 Pro Preview
    }
    
    def __init__(self):
        self._client = None
        self._claude_client = None
        self._gemini_client = None
        self._language_detector = None
    
    def _get_openai_client(self):
        """Obtiene el cliente de OpenAI"""
        if not self._client:
            from config.settings import settings
            api_key = settings.openai_api_key
            self._client = openai.Client(api_key=api_key)
        return self._client
    
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
                from google import genai
                from config.settings import settings
                api_key = settings.gemini_api_key
                self._gemini_client = genai.Client(api_key=api_key)
            except ImportError:
                logger.error("Google GenAI no está instalado. Instala con: pip install google-genai")
                raise
        return self._gemini_client
    
    def _get_language_detector(self):
        """Obtiene el detector de idiomas"""
        if not self._language_detector:
            self._language_detector = LanguageDetectorBuilder.from_languages(
                *self.SUPPORTED_LANGUAGES
            ).build()
        return self._language_detector
    
    def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 1500,
        stream: bool = True
    ):
        """
        Genera una respuesta de chat usando GPT, Claude o Gemini
        
        Args:
            messages: Lista de mensajes de la conversación
            model: Modelo a usar
            temperature: Temperatura para la generación
            max_tokens: Máximo de tokens a generar
            stream: Si hacer streaming de la respuesta
            
        Returns:
            Respuesta generada (string o generador si stream=True)
        """
        # Detectar el proveedor por el modelo
        if model.startswith("claude"):
            # Para Claude, necesitamos ejecutar la función asíncrona
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Crear una función wrapper para manejar el generador asíncrono
            async def run_claude():
                result = await self._generate_claude_response(messages, model, temperature, max_tokens, stream)
                if stream:
                    # Si es stream, ya devolvemos un generador síncrono desde _generate_claude_response
                    return result
                else:
                    return result
            
            result = loop.run_until_complete(run_claude())
            loop.close()
            return result
        elif model.startswith("gemini"):
            # Para Gemini, necesitamos ejecutar la función asíncrona
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Crear una función wrapper para manejar el generador asíncrono
            async def run_gemini():
                result = await self._generate_gemini_response(messages, model, temperature, max_tokens, stream)
                if stream:
                    # Si es stream, ya devolvemos un generador síncrono desde _generate_gemini_response
                    return result
                else:
                    return result
            
            result = loop.run_until_complete(run_gemini())
            loop.close()
            return result
        else:
            return self._generate_openai_response(messages, model, temperature, max_tokens, stream)
    
    def _generate_openai_response(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        stream: bool
    ):
        """Genera respuesta usando OpenAI"""
        client = self._get_openai_client()
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )
            
            if stream:
                return response
            else:
                return response.choices[0].message.content
                
        except Exception as e:
            logger.error(f"Error generando respuesta con OpenAI: {e}")
            raise
    
    async def _generate_claude_response(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        stream: bool
    ):
        """Genera respuesta usando Claude de forma asíncrona"""
        try:
            import asyncio
            client = self._get_claude_client()
            
            # Convertir mensajes al formato de Claude
            system_message = None
            claude_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    claude_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Crear la respuesta
            if stream:
                # Para streaming, necesitamos un enfoque diferente
                # ya que Streamlit no puede manejar generadores asíncronos directamente
                def sync_stream():
                    async def async_generator():
                        async with client.messages.stream(
                            model=model,
                            messages=claude_messages,
                            system=system_message,
                            temperature=temperature,
                            max_tokens=max_tokens
                        ) as stream:
                            async for text in stream.text_stream:
                                yield text
                    
                    # Crear un nuevo event loop para cada chunk
                    import asyncio
                    import threading
                    
                    # Cola thread-safe para pasar chunks entre threads
                    import queue
                    chunk_queue = queue.Queue()
                    
                    def run_async_generator():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        async def collect_chunks():
                            async for chunk in async_generator():
                                chunk_queue.put(chunk)
                            chunk_queue.put(None)  # Señal de fin
                        
                        loop.run_until_complete(collect_chunks())
                        loop.close()
                    
                    # Ejecutar en thread separado
                    thread = threading.Thread(target=run_async_generator)
                    thread.start()
                    
                    # Yield chunks mientras lleguen
                    while True:
                        chunk = chunk_queue.get()
                        if chunk is None:
                            break
                        yield chunk
                    
                    thread.join()
                
                return sync_stream()
            else:
                # Para respuesta completa
                async def get_response():
                    response = await client.messages.create(
                        model=model,
                        messages=claude_messages,
                        system=system_message,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    return response.content[0].text
                
                # Ejecutar de forma síncrona
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(get_response())
                loop.close()
                return result
                
        except ImportError:
            # Si anthropic no está instalado, devolver respuesta de prueba
            logger.warning("Anthropic no está instalado. Devolviendo respuesta de prueba.")
            if stream:
                def mock_stream():
                    yield "Esta es una respuesta de prueba de Claude. "
                    yield "Para usar Claude de verdad, instala el paquete anthropic: "
                    yield "pip install anthropic==0.54.0"
                return mock_stream()
            else:
                return "Esta es una respuesta de prueba de Claude. Para usar Claude de verdad, instala el paquete anthropic: pip install anthropic==0.54.0"
        except Exception as e:
            logger.error(f"Error generando respuesta con Claude: {e}")
            raise
    
    async def _generate_gemini_response(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        stream: bool
    ):
        """Genera respuesta usando Gemini de forma asíncrona"""
        try:
            import asyncio
            from google.genai import types
            client = self._get_gemini_client()
            
            # Convertir mensajes al formato de Gemini
            system_message = None
            gemini_contents = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                elif msg["role"] == "user":
                    gemini_contents.append(types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=msg["content"])]
                    ))
                elif msg["role"] == "assistant":
                    gemini_contents.append(types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=msg["content"])]
                    ))
            
            # Configuración de generación
            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                system_instruction=system_message
            )
            
            # Crear la respuesta
            if stream:
                # Para streaming con Gemini
                def sync_stream():
                    async def async_generator():
                        # Añadir prefijo 'models/' si no está presente
                        model_name = model if model.startswith('models/') else f'models/{model}'
                        async for chunk in await client.aio.models.generate_content_stream(
                            model=model_name,
                            contents=gemini_contents,
                            config=config
                        ):
                            if chunk.text:
                                yield chunk.text
                    
                    # Crear un nuevo event loop para cada chunk
                    import asyncio
                    import threading
                    
                    # Cola thread-safe para pasar chunks entre threads
                    import queue
                    chunk_queue = queue.Queue()
                    
                    def run_async_generator():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        async def collect_chunks():
                            async for chunk in async_generator():
                                chunk_queue.put(chunk)
                            chunk_queue.put(None)  # Señal de fin
                        
                        loop.run_until_complete(collect_chunks())
                        loop.close()
                    
                    # Ejecutar en thread separado
                    thread = threading.Thread(target=run_async_generator)
                    thread.start()
                    
                    # Yield chunks mientras lleguen
                    while True:
                        chunk = chunk_queue.get()
                        if chunk is None:
                            break
                        yield chunk
                    
                    thread.join()
                
                return sync_stream()
            else:
                # Para respuesta completa
                # Añadir prefijo 'models/' si no está presente
                model_name = model if model.startswith('models/') else f'models/{model}'
                response = await client.aio.models.generate_content(
                    model=model_name,
                    contents=gemini_contents,
                    config=config
                )
                return response.text
                
        except ImportError:
            # Si google-genai no está instalado, devolver respuesta de prueba
            logger.warning("Google GenAI no está instalado. Devolviendo respuesta de prueba.")
            if stream:
                def mock_stream():
                    yield "Esta es una respuesta de prueba de Gemini. "
                    yield "Para usar Gemini de verdad, instala el paquete google-genai: "
                    yield "pip install google-genai==1.20.0"
                return mock_stream()
            else:
                return "Esta es una respuesta de prueba de Gemini. Para usar Gemini de verdad, instala el paquete google-genai: pip install google-genai==1.20.0"
        except Exception as e:
            logger.error(f"Error generando respuesta con Gemini: {e}")
            raise
    
    def process_file(self, file) -> Optional[str]:
        """
        Procesa un archivo y extrae su contenido como texto
        
        Args:
            file: Archivo a procesar
            
        Returns:
            Texto extraído del archivo
        """
        try:
            filename = file.name.lower()
            
            if filename.endswith(".txt"):
                return self._read_txt(file)
            elif filename.endswith(".pdf"):
                return self._read_pdf(file)
            elif filename.endswith(".docx"):
                return self._read_docx(file)
            elif filename.endswith(".xlsx"):
                return self._read_excel(file)
            elif filename.endswith(".csv"):
                return self._read_csv(file)
            elif filename.endswith(".json"):
                return self._read_json(file)
            elif filename.endswith((".jpg", ".jpeg", ".png")):
                return self._read_image(file)
            elif filename.endswith(".zip"):
                return self._read_zip(file)
            else:
                logger.warning(f"Tipo de archivo no soportado: {file.name}")
                return None
                
        except Exception as e:
            logger.error(f"Error procesando archivo {file.name}: {e}")
            return None
    
    def _read_txt(self, file) -> str:
        """Lee un archivo de texto"""
        return file.read().decode("utf-8")
    
    def _read_pdf(self, file) -> str:
        """Lee un archivo PDF"""
        doc = fitz.open(stream=file.read(), filetype="pdf")
        text = "\n".join([page.get_text() for page in doc])
        doc.close()
        return text
    
    def _read_docx(self, file) -> str:
        """Lee un archivo Word"""
        doc = docx.Document(file)
        return "\n".join([p.text for p in doc.paragraphs])
    
    def _read_excel(self, file) -> str:
        """Lee un archivo Excel"""
        df = pd.read_excel(file)
        return df.to_string()
    
    def _read_csv(self, file) -> str:
        """Lee un archivo CSV"""
        df = pd.read_csv(file)
        return df.to_string()
    
    def _read_json(self, file) -> str:
        """Lee un archivo JSON"""
        try:
            data = json.load(file)
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"Error al leer JSON: {e}"
    
    def _read_image(self, file) -> str:
        """Lee texto de una imagen usando OCR"""
        try:
            image = Image.open(file)
            return pytesseract.image_to_string(image)
        except Exception as e:
            logger.error(f"Error en OCR: {e}")
            return "Error al procesar imagen"
    
    def _read_zip(self, file) -> str:
        """Lee archivos dentro de un ZIP"""
        text = ""
        with zipfile.ZipFile(file) as z:
            for name in z.namelist():
                with z.open(name) as f:
                    if name.endswith(".txt"):
                        text += f"\n\n--- {name} ---\n" + f.read().decode("utf-8")
                    elif name.endswith(".docx"):
                        text += f"\n\n--- {name} ---\n" + self._read_docx(f)
                    elif name.endswith(".csv"):
                        text += f"\n\n--- {name} ---\n" + pd.read_csv(f).to_string()
                    elif name.endswith(".xlsx"):
                        text += f"\n\n--- {name} ---\n" + pd.read_excel(f).to_string()
                    elif name.endswith(".pdf"):
                        text += f"\n\n--- {name} ---\n" + self._read_pdf(f)
                    elif name.endswith(".json"):
                        text += f"\n\n--- {name} ---\n" + self._read_json(f)
        return text
    
    def create_file_context(self, files: List) -> Optional[str]:
        """
        Crea contexto a partir de archivos subidos
        
        Args:
            files: Lista de archivos subidos
            
        Returns:
            Contexto formateado para el chat
        """
        if not files:
            return None
        
        extracted_texts = []
        
        for file in files:
            text = self.process_file(file)
            if text:
                extracted_texts.append(text)
        
        if not extracted_texts:
            return None
        
        # Combinar todos los textos
        combined_text = "\n\n".join(extracted_texts)
        
        # Detectar idioma
        try:
            detector = self._get_language_detector()
            detected_language = detector.detect_language_of(combined_text)
            language_name = detected_language.name.lower() if detected_language else "unknown"
        except:
            language_name = "unknown"
        
        # Instrucciones según idioma
        instructions = {
            "spanish": "El usuario ha subido uno o más archivos para analizar. A continuación tienes el contenido extraído. Úsalo como contexto para responder.",
            "english": "The user has uploaded one or more files for analysis. Below is the extracted content. Use it as context for your responses.",
            "french": "L'utilisateur a téléchargé un ou plusieurs fichiers à analyser. Voici le contenu extrait. Utilisez-le comme contexte pour vos réponses.",
            "german": "Der Benutzer hat eine oder mehrere Dateien zur Analyse hochgeladen. Verwenden Sie den folgenden Inhalt als Kontext.",
            "unknown": "The user uploaded files. Use the following extracted text as reference context."
        }
        
        context_message = instructions.get(language_name, instructions["unknown"])
        return f"{context_message}\n\n{combined_text}"
    
    def get_model_price(self, model: str) -> Tuple[float, float]:
        """
        Obtiene el precio de un modelo (entrada, salida) por 1M tokens
        
        Returns:
            Tupla (precio_entrada, precio_salida) en USD
        """
        return self.MODEL_PRICES.get(model, (0.0, 0.0))
    
    def format_conversation_for_export(
        self,
        messages: List[Dict[str, str]],
        model: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Formatea una conversación para exportación
        
        Args:
            messages: Lista de mensajes
            model: Modelo usado
            metadata: Metadatos adicionales
            
        Returns:
            Conversación formateada
        """
        export_data = {
            "model": model,
            "messages": messages,
            "message_count": len(messages),
            "timestamp": pd.Timestamp.now().isoformat()
        }
        
        if metadata:
            export_data["metadata"] = metadata
        
        return export_data
