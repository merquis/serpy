# modules/analisis/agrupacion_embeddings_module.py
import json
import pandas as pd
import numpy as np
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
    mongo_coll: str = None
) -> dict:
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
        raise ValueError("Fuente inválida. Usa 'local', 'drive' o 'mongo'.")

    # === Recolectar H2 y H3 ===
    h2_titulos = set()
    h3_titulos = set()
    h1_titulos = []
    busqueda = None

    for bloque in data:
        busqueda = busqueda or bloque.get("busqueda")
        for r in bloque.get("resultados", []):
            if r.get("status_code") == 200:
                h1 = r.get("h1", {}).get("titulo")
                if h1: h1_titulos.append(h1.strip())
                for h2 in r.get("h1", {}).get("h2", []):
                    t2 = h2.get("titulo", "").strip()
                    if t2:
                        h2_titulos.add(t2)
                        for h3 in h2.get("h3", []):
                            t3 = h3.get("titulo", "").strip()
                            if t3:
                                h3_titulos.add(t3)

    def get_embeddings(titulos):
        embeddings = []
        for t in titulos:
            try:
                rsp = client.embeddings.create(input=[t], model="text-embedding-3-small")
                embeddings.append(rsp.data[0].embedding)
            except:
                embeddings.append([0.0]*1536)
        return embeddings

    # === Clustering por nivel ===
    def agrupar_y_generar_nombres(titulos, n_clusters, nivel):
        textos = list(titulos)[:max_titulos_h2 if nivel == "H2" else max_titulos_h3]
        embeddings = get_embeddings(textos)
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        labels = km.fit_predict(embeddings)
        df = pd.DataFrame({"titulo": textos, "cluster": labels, "embedding": embeddings})

        resumenes = []
        for i in range(n_clusters):
            grupo = df[df.cluster == i]
            muestra = grupo["titulo"].tolist()
            prompt = f"""
Eres un experto SEO y copywriter.
Genera un título representativo de máximo 10 palabras para este grupo de {nivel}:

"""
            prompt += "\n".join(f"- {t}" for t in muestra[:10])
            prompt += "\n\nDevuelve solo el título."
            try:
                rsp = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}]
                )
                resumen = rsp.choices[0].message.content.strip()
            except:
                resumen = muestra[0] if muestra else f"Grupo {i}"
            resumenes.append((i, resumen, np.mean(grupo.embedding.tolist(), axis=0)))

        return df, resumenes

    df_h2, resumenes_h2 = agrupar_y_generar_nombres(h2_titulos, n_clusters_h2, "H2")
    df_h3, resumenes_h3 = agrupar_y_generar_nombres(h3_titulos, n_clusters_h3, "H3")

    # === Asociación H3 → H2 ===
    matrix_h2 = np.array([x[2] for x in resumenes_h2])
    matrix_h3 = np.array([x[2] for x in resumenes_h3])
    sim = cosine_similarity(matrix_h3, matrix_h2)

    estructura = {"title": "", "H2": []}
    for idx_h2, (cluster_h2, nombre_h2, _) in enumerate(resumenes_h2):
        h3_asignados = [resumenes_h3[i][1] for i in range(len(resumenes_h3)) if np.argmax(sim[i]) == idx_h2]
        estructura["H2"].append({"titulo": nombre_h2, "H3": h3_asignados})

    # === Generar H1 final ===
    resumen_arbol = "\n".join(f"- {h2['titulo']} → {', '.join(h2['H3'])}" for h2 in estructura["H2"])
    prompt_h1 = f"""
Eres un experto SEO. El usuario busca: "{busqueda}".
Estos son los H1 de la competencia:
""" + "\n".join(f"- {h}" for h in h1_titulos[:10]) + f"""

Este es el esquema H2 → H3 generado:
{resumen_arbol}

Devuelve el mejor título H1 posible para un artículo SEO.
"""
    try:
        h1 = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt_h1}]
        ).choices[0].message.content.strip()
    except:
        h1 = busqueda

    estructura["title"] = h1
    return estructura
