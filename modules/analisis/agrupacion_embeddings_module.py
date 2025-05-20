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
) -> dict:
    """
    Agrupa títulos H2 y H3 por separado, genera etiquetas IA por clúster,
    asigna H3 a H2 por similitud, y genera estructura jerárquica con título H1 final.
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
    h1_candidatos = []

    for bloque in data:
        for r in bloque.get("resultados", []):
            if r.get("status_code") == 200:
                h1 = r.get("h1", {}).get("titulo")
                if h1:
                    h1_candidatos.append(h1)
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
            print(f"Error embedding en: {text[:60]}... -> {e}")
            return [0.0] * 1536

    def generar_titulos_y_embeddings(df, nivel):
        out = []
        for cluster_id, grupo in df.groupby("cluster"):
            titulos = grupo["titulo"].tolist()
            prompt = f"Genera un título representativo de máximo 10 palabras para este grupo de {nivel}:
" + "\n".join(f"- {t}" for t in titulos)
            try:
                resp = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}]
                )
                resumen = resp.choices[0].message.content.strip()
            except:
                resumen = titulos[0] if titulos else f"{nivel} Cluster {cluster_id}"
            emb = get_embedding(resumen)
            out.append({"cluster": cluster_id, "titulo": resumen, "embedding": emb})
        return out

    def agrupar_lista(titulos):
        titulos = list(titulos)[:max_titulos]
        if not titulos:
            return pd.DataFrame(columns=["titulo", "cluster"])
        n_validos = max(2, min(n_clusters, len(titulos)))
        embeddings = [get_embedding(t) for t in tqdm(titulos, desc="Embed")] 
        km = KMeans(n_clusters=n_validos, random_state=42, n_init="auto")
        labels = km.fit_predict(embeddings)
        return pd.DataFrame({"titulo": titulos, "cluster": labels}).sort_values("cluster")

    df_h2 = agrupar_lista(h2_titulos)
    df_h3 = agrupar_lista(h3_titulos)

    resumen_h2 = generar_titulos_y_embeddings(df_h2, "H2")
    resumen_h3 = generar_titulos_y_embeddings(df_h3, "H3")

    # Asignación H3 → H2 por similitud
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np

    matrix_h2 = np.array([r["embedding"] for r in resumen_h2])
    matrix_h3 = np.array([r["embedding"] for r in resumen_h3])

    sim = cosine_similarity(matrix_h3, matrix_h2)

    estructura = {"title": "", "H2": []}
    h2_index_map = {r["cluster"]: {"titulo": r["titulo"], "H3": []} for r in resumen_h2}

    for idx_h3, fila in enumerate(sim):
        h3_resumen = resumen_h3[idx_h3]["titulo"]
        best_h2_idx = int(np.argmax(fila))
        h2_cluster = resumen_h2[best_h2_idx]["cluster"]
        h2_index_map[h2_cluster]["H3"].append(h3_resumen)

    estructura["H2"] = list(h2_index_map.values())

    busqueda = data[0].get("busqueda") if isinstance(data, list) else data.get("busqueda", "")
    resumen_arbol = "\n".join("- " + h2["titulo"] + " → " + ", ".join(h2["H3"]) for h2 in estructura["H2"])

    prompt_h1 = f"""
Eres experto en SEO. El usuario busca: "{busqueda}".
Estos son títulos H1 encontrados en la competencia:
- """ + "\n- ".join(h1_candidatos[:10]) + f"""

Y este es el esquema jerárquico del artículo:
{resumen_arbol}

Genera un único título H1 potente y SEO-friendly que represente todo el artículo.
"""
    try:
        h1_ai = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt_h1}]
        ).choices[0].message.content.strip()
    except:
        h1_ai = busqueda or "Título principal"

    estructura["title"] = h1_ai
    return estructura
