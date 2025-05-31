"""
Servicio de Análisis Semántico con Embeddings
"""
import json
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import openai
import streamlit as st
import logging

logger = logging.getLogger(__name__)

class EmbeddingsService:
    """Servicio para análisis semántico y agrupación con embeddings"""
    
    def __init__(self):
        self._client = None
    
    def _get_openai_client(self):
        """Obtiene el cliente de OpenAI"""
        if not self._client:
            api_key = st.secrets["openai"]["api_key"]
            self._client = openai.Client(api_key=api_key)
        return self._client
    
    def analyze_and_group_titles(
        self,
        data: Any,
        max_titles_h2: int = 300,
        max_titles_h3: int = 900,
        n_clusters_h2: int = 10,
        n_clusters_h3: int = 30,
        model: str = "chatgpt-4o-latest"
    ) -> Dict[str, Any]:
        """
        Analiza y agrupa títulos H2 y H3 usando embeddings y clustering
        
        Args:
            data: Datos JSON a analizar
            max_titles_h2: Máximo de títulos H2 a procesar
            max_titles_h3: Máximo de títulos H3 a procesar
            n_clusters_h2: Número de clusters para H2
            n_clusters_h3: Número de clusters para H3
            model: Modelo de GPT a usar
            
        Returns:
            Estructura de árbol SEO con H1, H2 y H3 agrupados
        """
        # Asegurar que data es una lista
        if isinstance(data, dict):
            data = [data]
        elif isinstance(data, bytes):
            data = [json.loads(data.decode("utf-8"))]
        elif isinstance(data, str):
            data = [json.loads(data)]
        
        # Extraer títulos
        h2_titles, h3_titles, h1_titles = self._extract_titles(data)
        
        # Limitar cantidad de títulos
        h2_titles = h2_titles[:max_titles_h2]
        h3_titles = h3_titles[:max_titles_h3]
        
        if not h2_titles:
            raise ValueError("No se encontraron títulos H2 para analizar")
        
        # Agrupar títulos por clustering
        df_h2 = self._cluster_titles(h2_titles, n_clusters_h2)
        df_h3 = self._cluster_titles(h3_titles, n_clusters_h3) if h3_titles else pd.DataFrame()
        
        # Generar títulos representativos para cada cluster
        df_h2 = self._generate_cluster_titles(df_h2, "H2", model)
        if not df_h3.empty:
            df_h3 = self._generate_cluster_titles(df_h3, "H3", model)
        
        # Asociar H3 a H2 por similitud semántica
        h3_to_h2_map = {}
        if not df_h3.empty:
            h3_to_h2_map = self._associate_h3_to_h2(df_h2, df_h3)
        
        # Construir estructura de árbol
        structure = self._build_tree_structure(df_h2, df_h3, h3_to_h2_map)
        
        # Generar H1 óptimo
        h1_title = self._generate_h1_title(data, h1_titles, structure, model)
        structure["title"] = h1_title
        
        return structure
    
    def _extract_titles(self, data: List[Dict]) -> Tuple[List[str], List[str], List[str]]:
        """Extrae títulos H1, H2 y H3 de los datos"""
        h2_titles, h3_titles, h1_titles = [], [], []
        
        for bloque in data:
            # Si el bloque es una lista, procesarla diferente
            if isinstance(bloque, list):
                # Es una lista de resultados directamente
                resultados = bloque
            elif isinstance(bloque, dict):
                # Es un diccionario con resultados
                resultados = bloque.get("resultados", [])
            else:
                continue
            
            # Procesar cada resultado
            for resultado in resultados:
                if not isinstance(resultado, dict):
                    continue
                
                if resultado.get("status_code") == 200:
                    h1_data = resultado.get("h1", {})
                    if isinstance(h1_data, dict) and h1_data.get("titulo"):
                        h1_titles.append(h1_data["titulo"])
                    
                    # Extraer H2s y H3s
                    for h2 in h1_data.get("h2", []) if isinstance(h1_data, dict) else []:
                        if isinstance(h2, dict) and (titulo_h2 := h2.get("titulo", "").strip()):
                            h2_titles.append(titulo_h2)
                        
                        # Extraer H3s
                        for h3 in h2.get("h3", []):
                            if isinstance(h3, dict) and (titulo_h3 := h3.get("titulo", "").strip()):
                                h3_titles.append(titulo_h3)
        
        return h2_titles, h3_titles, h1_titles
    
    def _get_embedding(self, text: str) -> List[float]:
        """Obtiene el embedding de un texto"""
        try:
            client = self._get_openai_client()
            response = client.embeddings.create(
                input=[text],
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error obteniendo embedding: {e}")
            return [0.0] * 1536  # Dimensión por defecto
    
    def _cluster_titles(self, titles: List[str], n_clusters: int) -> pd.DataFrame:
        """Agrupa títulos usando KMeans clustering"""
        if not titles:
            return pd.DataFrame()
        
        # Ajustar número de clusters si hay menos títulos
        n_clusters = min(n_clusters, len(titles))
        
        # Obtener embeddings
        embeddings = [self._get_embedding(title) for title in titles]
        
        # Aplicar KMeans
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        labels = kmeans.fit_predict(embeddings)
        
        return pd.DataFrame({"titulo": titles, "cluster": labels})
    
    def _generate_cluster_titles(self, df: pd.DataFrame, level: str, model: str) -> pd.DataFrame:
        """Genera títulos representativos para cada cluster"""
        client = self._get_openai_client()
        cluster_summaries = []
        
        for cluster_id, group in df.groupby("cluster"):
            titles = group["titulo"].tolist()
            
            # Construir prompt
            prompt = f"""Genera un título representativo de máximo 10 palabras para este grupo de {level}:
- """ + "\n- ".join(titles[:10])
            
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=50,
                    temperature=0.7
                )
                summary = response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"Error generando título para cluster: {e}")
                summary = titles[0]  # Usar el primer título como fallback
            
            cluster_summaries.append((cluster_id, summary))
        
        # Agregar resúmenes al DataFrame
        df_summary = pd.DataFrame(cluster_summaries, columns=["cluster", "resumen"])
        return df.merge(df_summary, on="cluster")
    
    def _associate_h3_to_h2(self, df_h2: pd.DataFrame, df_h3: pd.DataFrame) -> Dict[int, int]:
        """Asocia clusters de H3 a clusters de H2 por similitud semántica"""
        # Obtener títulos únicos por cluster
        h2_summaries = df_h2.drop_duplicates("cluster")["resumen"].tolist()
        h3_summaries = df_h3.drop_duplicates("cluster")["resumen"].tolist()
        
        # Obtener embeddings
        h2_embeddings = [self._get_embedding(summary) for summary in h2_summaries]
        h3_embeddings = [self._get_embedding(summary) for summary in h3_summaries]
        
        # Calcular similitud coseno
        similarity_matrix = cosine_similarity(h3_embeddings, h2_embeddings)
        
        # Mapear cada H3 al H2 más similar
        h3_to_h2_map = {}
        h3_clusters = df_h3["cluster"].unique()
        h2_clusters = df_h2["cluster"].unique()
        
        for idx, row in enumerate(similarity_matrix):
            best_h2_idx = int(row.argmax())
            h3_cluster = h3_clusters[idx]
            h2_cluster = h2_clusters[best_h2_idx]
            h3_to_h2_map[h3_cluster] = h2_cluster
        
        return h3_to_h2_map
    
    def _build_tree_structure(
        self,
        df_h2: pd.DataFrame,
        df_h3: pd.DataFrame,
        h3_to_h2_map: Dict[int, int]
    ) -> Dict[str, Any]:
        """Construye la estructura de árbol H2 -> H3"""
        structure = {"title": "", "H2": []}
        
        for h2_cluster, h2_group in df_h2.groupby("cluster"):
            h2_title = h2_group["resumen"].iloc[0]
            
            # Encontrar H3s asociados
            h3_titles = []
            if not df_h3.empty:
                for h3_cluster, h3_group in df_h3.groupby("cluster"):
                    if h3_to_h2_map.get(h3_cluster) == h2_cluster:
                        h3_titles.append(h3_group["resumen"].iloc[0])
            
            structure["H2"].append({
                "titulo": h2_title,
                "H3": h3_titles
            })
        
        return structure
    
    def _generate_h1_title(
        self,
        data: List[Dict],
        h1_titles: List[str],
        structure: Dict[str, Any],
        model: str
    ) -> str:
        """Genera un título H1 óptimo basado en la competencia y estructura"""
        client = self._get_openai_client()
        
        # Obtener keyword de búsqueda
        search_query = ""
        if data and isinstance(data[0], dict):
            search_query = data[0].get("busqueda", "") or data[0].get("keyword", "")
        
        # Crear resumen de la estructura
        tree_summary = "\n".join([
            f"- {h2['titulo']} → {', '.join(h2['H3']) if h2['H3'] else 'Sin H3s'}"
            for h2 in structure["H2"]
        ])
        
        # Construir prompt
        prompt = f"""
Eres un consultor SEO experto. El usuario busca: "{search_query}".

Estos son los H1 de la competencia:
- """ + "\n- ".join(h1_titles[:10]) + f"""

Y este es el esquema jerárquico propuesto:
{tree_summary}

Genera un título H1 que:
1. Sea claro, atractivo y relevante para SEO
2. Incluya la keyword principal
3. Se diferencie de la competencia
4. Refleje el contenido del esquema propuesto

Devuelve SOLO el título H1, sin explicaciones adicionales.
"""
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generando H1: {e}")
            return search_query or "Título Principal"
    
    def get_extracted_keyword(self, data: Any) -> Optional[str]:
        """Extrae la keyword principal de los datos"""
        if isinstance(data, bytes):
            data = json.loads(data.decode("utf-8"))
        elif isinstance(data, str):
            data = json.loads(data)
        
        if isinstance(data, dict):
            return data.get("busqueda") or data.get("keyword") or data.get("query")
        elif isinstance(data, list) and data:
            return data[0].get("busqueda") or data[0].get("keyword") or data[0].get("query")
        
        return None 