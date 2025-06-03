"""
Servicio de Chat con GPT
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
        "gpt-4o-mini": (0.40, 1.60),
        "o1-mini": (1.10, 4.40),
        "gpt-4o-2024-11-20": (2.00, 8.00),
        "chatgpt-4o-latest": (3.75, 15.00),
        "o1": (10.00, 40.00),
    }
    
    def __init__(self):
        self._client = None
        self._language_detector = None
    
    def _get_openai_client(self):
        """Obtiene el cliente de OpenAI"""
        if not self._client:
            api_key = st.secrets["openai"]["api_key"]
            self._client = openai.Client(api_key=api_key)
        return self._client
    
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
        Genera una respuesta de chat usando GPT
        
        Args:
            messages: Lista de mensajes de la conversación
            model: Modelo de GPT a usar
            temperature: Temperatura para la generación
            max_tokens: Máximo de tokens a generar
            stream: Si hacer streaming de la respuesta
            
        Returns:
            Respuesta generada (string o generador si stream=True)
        """
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
            logger.error(f"Error generando respuesta: {e}")
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