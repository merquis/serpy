import streamlit as st
import openai
import json
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    subir_json_a_drive,
    obtener_o_crear_subcarpeta
)

def obtener_rango_legible(rango):
    partes = rango.split(" - ")
    if len(partes) == 2:
        return f"entre {partes[0]} y {partes[1]} palabras"
    return rango

def generar_prompt_extra(palabra_clave, idioma, tipo_articulo, rango):
    return f"""
Eres un experto en redacción SEO, copywriting y posicionamiento en Google.

A continuación tienes un resumen estructurado de las páginas mejor posicionadas en Google España (idioma {idioma.lower()}) para la palabra clave: \"{palabra_clave}\".

Este resumen se basa en la recopilación de las etiquetas HTML y contenido visible de los artículos mejor posicionados para dicha búsqueda.

Tu tarea es:

- Analizar el contenido de referencia.
- Detectar las intenciones de búsqueda del usuario.
- Identificar los temas más recurrentes y relevantes.
- Reconocer la estructura común de encabezados (H1, H2, H3).
- Estudiar el enfoque editorial de los competidores.

Luego, redacta un artículo original, más útil, más completo y mejor optimizado para SEO que los que ya existen. No repitas información innecesaria ni uses frases genéricas.

✍️ Detalles de redacción:
🔢 Longitud: {obtener_rango_legible(rango)}
🌍 Idioma: {idioma}
📄 Tipo de artículo: {tipo_articulo}
🗂️ Formato: Utiliza subtítulos claros (H2 y H3), listas, introducción persuasiva y conclusión útil.
📈 Objetivo: Posicionarse en Google para la keyword \"{palabra_clave}\".
🚫 No menciones que eres una IA ni expliques que estás generando un texto.
✅ Hazlo como si fueras un redactor profesional experto en turismo y SEO.
"""

def obtener_prompt_humano():
    return """
Mi objetivo principal es que este texto suene lo más humano posible y sea difícil de identificar como generado por inteligencia artificial por las herramientas de detección. Para lograrlo, te pido que apliques las siguientes directrices al escribir:

Variedad en la Estructura y Longitud de las Frases: Alterna de forma natural frases cortas y directas con otras más largas y complejas. Evita que todas las oraciones tengan una estructura sintáctica o una longitud similar.
Lenguaje Natural y Fluido: Utiliza un vocabulario, expresiones y giros (si son apropiados para el contexto y público) que suenen a una persona real hablando o escribiendo de manera espontánea. Evita la formalidad rígida o un lenguaje que parezca seleccionado de forma puramente estadística.
Ritmo de Escritura Impredecible (similar a la 'Perplejidad' y 'Burstiness'): Haz que la elección de palabras y el flujo del texto sean menos predecibles. Varía el ritmo del texto; introduce pausas, cambia la cadencia de las frases, no sigas una secuencia lógica o gramatical excesivamente obvia o repetitiva en cada paso.
Evita Patrones Genéricos o Robóticos: No uses frases introductorias, conectores o estructuras de cierre que son extremadamente comunes en textos generados por IA. Busca formas más originales o naturales de enlazar ideas y comenzar/terminar párrafos. Que suene auténtico, no como si siguiera una plantilla invisible.
Adopta una Voz o Tono Específico (Opcional pero Recomendado): Si aplica al contexto, escribe como si fueras [Describe aquí una persona específica o un tipo de personalidad, ej: un experto apasionado compartiendo su conocimiento, un joven entusiasta, un narrador informal y amigable, alguien que cuenta una anécdota personal]. Esto añadirá una capa de personalidad y hará el texto más único y humano.
"""

# El resto del código permanece igual. Añade esta llamada en el punto adecuado:
st.session_state["prompt_extra_manual"] = obtener_prompt_humano()

# Puedes colocar esta línea justo antes o después del input de instrucciones personalizadas, según si quieres que el usuario pueda editarlo también o no.
