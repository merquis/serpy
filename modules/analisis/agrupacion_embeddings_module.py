# modules/analisis/agrupacion_embeddings_module.py
import json
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
from modules.utils.drive_utils import obtener_contenido_archivo_drive
from modules.utils.mongo_utils import obtener_documento_mongodb


def agrupar_titulos_por_embeddings(
    api_key: str,
    source: str,
    source_id: str,
    max_titulos_h2: int,
    max_titulos_h3: int,
    n_clusters_h2: int,
    n_clusters_h3: int,
    mongo_uri: str = None,
    mongo_db: str = None,
    mongo_coll: str = "hoteles"
) -> dict:
    """Agrupa H2 y H3 y genera árbol SEO con título H1 final."""

    client = OpenAI(api_key=api_key)

    # === Cargar datos ===
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
        raise ValueError("Fuente inválida")

    data = data if isinstance(data, list) else [data]

    # === Extraer títulos ===
    h2_titles, h3_titles, h1_titles = [], [], []
    for bloque in data:
        h1_titles.extend([
            r.get("h1", {}).get("titulo")
            for r in bloque.get("resultados", [])
            if r.get("status_code") == 200 and r.get("h1", {}).get("titulo")
        ])
        for r in bloque.get("resultados", []):
            if r.get("status_code") != 200:
                continue
            for h2 in r.get("h1", {}).get("h2", []):
                if t := h2.get("titulo", "").strip():
                    h2_titles.append(t)
                for h3 in h2.get("h3", []):
                    if t3 := h3.get("titulo", "").strip():
                        h3_titles.append(t3)

    h2_titles = h2_titles[:max_titulos_h2]
    h3_titles = h3_titles[:max_titulos_h3]

    # === Embedding helper ===
    def get_embedding(text: str) -> list:
        try:
            return client.embeddings.create(input=[text], model="text-embedding-3-small").data[0].embedding
        except:
            return [0.0] * 1536

    # === Agrupar títulos por KMeans ===
    def cluster_titulos(titulos, n_clusters):
        emb = [get_embedding(t) for t in titulos]
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        etiquetas = kmeans.fit_predict(emb)
        df = pd.DataFrame({"titulo": titulos, "cluster": etiquetas})
        return df

    df_h2 = cluster_titulos(h2_titles, n_clusters_h2)
    df_h3 = cluster_titulos(h3_titles, n_clusters_h3)

    # === Generar títulos para cada grupo con OpenAI ===
    def generar_titulos_cluster(df: pd.DataFrame, nivel: str) -> pd.DataFrame:
        nuevos = []
        for i, grupo in df.groupby("cluster"):
            textos = grupo["titulo"].tolist()
            prompt = f"""Genera un título representativo de máximo 10 palabras para este grupo de {nivel}:\n- """ + "\n- ".join(textos[:10])
            try:
                rsp = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}]
                )
                resumen = rsp.choices[0].message.content.strip()
            except:
                resumen = textos[0]
            nuevos.append((i, resumen))
        df_resumen = pd.DataFrame(nuevos, columns=["cluster", "resumen"])
        return df.merge(df_resumen, on="cluster")

    df_h2 = generar_titulos_cluster(df_h2, "H2")
    df_h3 = generar_titulos_cluster(df_h3, "H3")

    # === Asociar H3 a H2 por similitud semántica ===
    def asociar_h3_a_h2(df_h2, df_h3):
        emb_h2 = df_h2.drop_duplicates("cluster")["resumen"].apply(get_embedding).tolist()
        emb_h3 = df_h3.drop_duplicates("cluster")["resumen"].apply(get_embedding).tolist()
        sim = cosine_similarity(emb_h3, emb_h2)
        h3_to_h2 = {}
        for idx, fila in enumerate(sim):
            best = int(fila.argmax())
            h3_cluster = df_h3["cluster"].unique()[idx]
            h3_to_h2[h3_cluster] = df_h2["cluster"].unique()[best]
        return h3_to_h2

    mapa_h3 = asociar_h3_a_h2(df_h2, df_h3)

    # === Construir árbol H2 → H3 ===
    estructura = {"title": "", "H2": []}
    for h2_id, grupo_h2 in df_h2.groupby("cluster"):
        h2_etiqueta = grupo_h2["resumen"].iloc[0]
        hijos_h3 = [
            h3 for cid, h3g in df_h3.groupby("cluster")
            if mapa_h3.get(cid) == h2_id
            for h3 in [h3g["resumen"].iloc[0]]
        ]
        estructura["H2"].append({"titulo": h2_etiqueta, "H3": hijos_h3})

    # === Generar H1 final ===
    resumen_arbol = "\n".join(f"- {h2['titulo']} → {', '.join(h2['H3'])}" for h2 in estructura["H2"])
    prompt_h1 = f"""
Eres un consultor SEO experto. El usuario busca: "{data[0].get('busqueda', 'Título') if data else 'Título'}".
Estos son los H1 de la competencia:
- """ + "\n- ".join(h1_titles[:10]) + f"""

Y este es el esquema jerárquico propuesto:
{resumen_arbol}

Devuelve un título H1 claro, atractivo, optimizado y relevante para SEO.
"""
    try:
        h1 = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt_h1}]
        ).choices[0].message.content.strip()
    except:
        h1 = data[0].get("busqueda", "Título")

    estructura["title"] = h1
    return estructura
