import json
import pandas as pd
from tqdm import tqdm
from sklearn.cluster import KMeans
from openai import OpenAI

from modules.utils.drive_utils import obtener_contenido_archivo_drive
from modules.utils.mongo_utils import obtener_documento_mongodb

# === FUNCION PRINCIPAL PARA INTEGRAR EN SERPY ===
def agrupar_titulos_por_embeddings(
    api_key: str,
    source: str = "local",              # "local", "drive" o "mongo"
    source_id: str = None,              # path local, file_id de Drive, o ID/campo de Mongo
    mongo_uri: str = None,
    mongo_db: str = None,
    mongo_coll: str = None,
    max_titulos: int = 500,
    n_clusters: int = 10
) -> pd.DataFrame:
    """
    Carga un JSON desde local, Drive o MongoDB, obtiene embeddings de títulos H2/H3
    y los agrupa por similitud semántica usando KMeans.
    """
    client = OpenAI(api_key=api_key)

    # === Cargar datos según fuente ===
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

    # === Extraer títulos únicos ===
    titulos = set()
    for bloque in data:
        for r in bloque.get("resultados", []):
            if r.get("status_code") == 200:
                h2s = r.get("h1", {}).get("h2", [])
                if isinstance(h2s, list):
                    for h2 in h2s:
                        t2 = h2.get("titulo", "").strip()
                        if t2:
                            titulos.add(t2)
                        for h3 in h2.get("h3", []):
                            t3 = h3.get("titulo", "").strip()
                            if t3:
                                titulos.add(t3)

    titulos = list(titulos)[:max_titulos]

    # === Obtener embeddings ===
    def get_embedding(text, model="text-embedding-3-small"):
        try:
            response = client.embeddings.create(input=[text], model=model)
            return response.data[0].embedding
        except Exception as e:
            print(f"Error en: {text[:60]}... -> {e}")
            return [0.0] * 1536

    embeddings = []
    for t in tqdm(titulos, desc="Obteniendo embeddings"):
        embeddings.append(get_embedding(t))

    # === Agrupar con KMeans ===
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    labels = km.fit_predict(embeddings)

    df = pd.DataFrame({"titulo": titulos, "cluster": labels})
    df.sort_values("cluster", inplace=True)
    return df
