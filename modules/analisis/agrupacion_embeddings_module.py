# modules/analisis/agrupacion_embeddings_module.py
import json
import pandas as pd
from tqdm import tqdm
from sklearn.cluster import KMeans
from openai import OpenAI

from modules.utils.drive_utils import obtener_contenido_archivo_drive
from modules.utils.mongo_utils import obtener_documento_mongodb

def agrupar_titulos_por_embeddings(
    api_key: str,
    source: str = "local",
    source_id: str = None,
    mongo_uri: str = None,
    mongo_db: str = None,
    mongo_coll: str = None,
    max_titulos: int = 500,
    n_clusters: int = 10
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Agrupa títulos H2 y H3 por separado usando embeddings y KMeans.
    Devuelve dos DataFrames: uno para H2 y otro para H3.
    """
    client = OpenAI(api_key=api_key)

    if source == "local":
        with open(source_id, "r", encoding="utf-8") as f:
            data = json.load(f)
    elif source == "drive":
        contenido = obtener_contenido_archivo_drive(source_id)
        data = json.loads(contenido.decode("utf-8"))
    elif source == "mongo":
        doc = obtener_documento_mongodb(mongo_uri, mongo_db, mongo_coll, source_id, campo_nombre="busqueda")
        data = [doc] if isinstance(doc, dict) else doc
    else:
        raise ValueError("Fuente inválida. Usa 'local', 'drive' o 'mongo'.")

    h2_titulos = set()
    h3_titulos = set()

    for bloque in data:
        for r in bloque.get("resultados", []):
            if r.get("status_code") == 200:
                h2s = r.get("h1", {}).get("h2", [])
                for h2 in h2s:
                    t2 = h2.get("titulo", "").strip()
                    if t2:
                        h2_titulos.add(t2)
                    for h3 in h2.get("h3", []):
                        t3 = h3.get("titulo", "").strip()
                        if t3:
                            h3_titulos.add(t3)

    def get_embedding(text, model="text-embedding-3-small"):
        try:
            response = client.embeddings.create(input=[text], model=model)
            return response.data[0].embedding
        except Exception as e:
            print(f"Error en: {text[:60]}... -> {e}")
            return [0.0] * 1536

    def agrupar_lista(titulos):
        titulos = list(titulos)[:max_titulos]
        if not titulos:
            return pd.DataFrame(columns=["titulo", "cluster"])
        n_validos = min(n_clusters, len(titulos))
        if n_validos < 2:
            return pd.DataFrame({"titulo": titulos, "cluster": [0] * len(titulos)})
        embeddings = [get_embedding(t) for t in tqdm(titulos, desc="Embed")]
        km = KMeans(n_clusters=n_validos, random_state=42, n_init="auto")
        labels = km.fit_predict(embeddings)
        return pd.DataFrame({"titulo": titulos, "cluster": labels}).sort_values("cluster")

    df_h2 = agrupar_lista(h2_titulos)
    df_h3 = agrupar_lista(h3_titulos)

    return df_h2, df_h3
