# modules/analisis/agrupacion_embeddings_module.py
import json
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
from modules.utils.drive_utils import obtener_contenido_archivo_drive


def agrupar_titulos_por_embeddings(api_key, source, source_id, max_titulos, n_clusters):
    client = OpenAI(api_key=api_key)

    # === Cargar JSON ===
    if source == "drive":
        contenido = obtener_contenido_archivo_drive(source_id)
        data = json.loads(contenido.decode("utf-8"))
    elif source == "local":
        with open(source_id, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        raise ValueError("Fuente inválida.")

    data = [data] if isinstance(data, dict) else data

    # === Extraer títulos H2 y H3 ===
    h2, h3 = [], []
    for entrada in data:
        for r in entrada.get("resultados", []):
            if r.get("status_code") == 200:
                for h2_item in r.get("h1", {}).get("h2", []):
                    if t2 := h2_item.get("titulo", "").strip():
                        h2.append(t2)
                    for h3_item in h2_item.get("h3", []):
                        if t3 := h3_item.get("titulo", "").strip():
                            h3.append(t3)

    h2 = h2[:max_titulos]
    h3 = h3[:max_titulos]

    def embed(text):
        try:
            return client.embeddings.create(input=[text], model="text-embedding-3-small").data[0].embedding
        except Exception:
            return [0.0] * 1536

    def cluster_y_resumir(lista, nivel):
        embeddings = [embed(t) for t in lista]
        km = KMeans(n_clusters=n_clusters, n_init="auto", random_state=42)
        labels = km.fit_predict(embeddings)
        df = pd.DataFrame({"titulo": lista, "cluster": labels})

        resumenes = []
        for c_id, grupo in df.groupby("cluster"):
            textos = grupo["titulo"].tolist()
            prompt = (
                f"Genera un título representativo de máximo 10 palabras para este grupo de {nivel}: \n\n"
                + "\n".join(f"- {x}" for x in textos)
            )
            try:
                respuesta = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}]
                )
                resumen = respuesta.choices[0].message.content.strip()
            except Exception:
                resumen = textos[0]
            resumenes.append((c_id, resumen, embed(resumen)))

        df_summary = pd.DataFrame([
            {"cluster": cid, "resumen": resumen, "embedding": emb}
            for cid, resumen, emb in resumenes
        ])
        return df, df_summary

    df_h2, df_h2_summ = cluster_y_resumir(h2, "H2")
    df_h3, df_h3_summ = cluster_y_resumir(h3, "H3")

    # === Asociar H3 a H2 (por embedding del resumen) ===
    mat_h2 = np.stack(df_h2_summ.embedding.to_list())
    mat_h3 = np.stack(df_h3_summ.embedding.to_list())
    sim_matrix = cosine_similarity(mat_h3, mat_h2)

    asociaciones = []
    for idx_h3, fila in enumerate(sim_matrix):
        h3_row = df_h3_summ.iloc[idx_h3]
        best_h2_idx = int(np.argmax(fila))
        h2_row = df_h2_summ.iloc[best_h2_idx]
        asociaciones.append({
            "h3_cluster": h3_row.cluster,
            "h3_resumen": h3_row.resumen,
            "h2_cluster": h2_row.cluster,
            "h2_resumen": h2_row.resumen,
            "similaridad": float(np.max(fila))
        })

    df_asoc = pd.DataFrame(asociaciones)

    # === Obtener H1 definitivo ===
    busqueda = data[0].get("busqueda", "Título")
    h1_reales = []
    for entrada in data:
        for r in entrada.get("resultados", []):
            h1 = r.get("h1", {}).get("titulo")
            if h1:
                h1_reales.append(h1)

    resumen_arbol = "\n".join(
        f"- {h2} → " + ", ".join(df_asoc[df_asoc.h2_resumen == h2].h3_resumen.tolist())
        for h2 in df_asoc.h2_resumen.unique()
    )

    prompt_h1 = f"""
Eres un experto en SEO. La búsqueda del usuario es: "{busqueda}"

Estos son los títulos H1 usados por la competencia:
""" + "\n".join(f"- {t}" for t in h1_reales[:10]) + f"""

Además, este es el esquema del artículo:
{resumen_arbol}

Devuélveme un único título H1 que sea natural, claro, conciso y óptimo para SEO.
"""
    try:
        h1_ai = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt_h1}]
        ).choices[0].message.content.strip()
    except Exception:
        h1_ai = busqueda

    estructura = {"title": h1_ai, "H2": []}
    for h2_id, grupo_h2 in df_asoc.groupby("h2_cluster"):
        h2_titulo = grupo_h2["h2_resumen"].iloc[0]
        h3s = grupo_h2["h3_resumen"].tolist()
        estructura["H2"].append({
            "titulo": h2_titulo,
            "H3": h3s
        })

    return estructura
