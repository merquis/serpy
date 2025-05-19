import json
import openai
import pandas as pd
from sklearn.cluster import KMeans
from tqdm import tqdm

# === FUNCION PRINCIPAL PARA INTEGRAR EN SERPY ===
def agrupar_titulos_por_embeddings(
    json_path: str,
    api_key: str,
    max_titulos: int = 500,
    n_clusters: int = 10
) -> pd.DataFrame:
    """
    Carga un JSON con resultados scrapeados, obtiene los embeddings de títulos H2/H3
    y los agrupa por similitud semántica usando KMeans.

    Args:
        json_path (str): Ruta al archivo JSON.
        api_key (str): Clave de API de OpenAI.
        max_titulos (int): Máximo de títulos a procesar.
        n_clusters (int): Número de clústeres para KMeans.

    Returns:
        pd.DataFrame: DataFrame con 'titulo' y 'cluster'
    """
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extraer títulos únicos
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

    # Obtener embeddings
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

    # Agrupar con KMeans
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    labels = km.fit_predict(embeddings)

    df = pd.DataFrame({"titulo": titulos, "cluster": labels})
    df.sort_values("cluster", inplace=True)
    return df

# === USO DE EJEMPLO (opcional para pruebas locales) ===
if __name__ == "__main__":
    API_KEY = "sk-..."
    JSON_PATH = "hotelesss.json"
    df_resultado = agrupar_titulos_por_embeddings(JSON_PATH, API_KEY)
    df_resultado.to_csv("clusters_titulos.csv", index=False, encoding="utf-8")
    print("Listo. Clusters exportados a clusters_titulos.csv")
