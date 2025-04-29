import requests

API_KEY = 'f1b8836788c0f99bea855e4eceb23e6d'
SCRAPERAPI_SEARCH_URL = 'https://api.scraperapi.com/structured/google/search'


def search_google_scraperapi(query, max_results=10):
    """
    Realiza una búsqueda en Google usando ScraperAPI y devuelve las URLs encontradas.

    Args:
        query (str): La búsqueda que deseas realizar.
        max_results (int): Número máximo de URLs a devolver.

    Returns:
        list: Lista de URLs encontradas.
    """
    payload = {
        'api_key': API_KEY,
        'query': query,
    }

    print(f"\n🔵 Buscando en Google: {query}")

    try:
        response = requests.get(SCRAPERAPI_SEARCH_URL, params=payload)
        response.raise_for_status()
        data = response.json()

        urls = []
        organic_results = data.get('organic_results', [])

        for result in organic_results:
            link = result.get('link')
            if link:
                urls.append(link)
            if len(urls) >= max_results:
                break

        print(f"\n✅ Se encontraron {len(urls)} URLs relevantes.")
        return urls

    except requests.RequestException as e:
        print(f"\n❌ Error al conectar con ScraperAPI: {e}")
        return []
    except ValueError as e:
        print(f"\n❌ Error al interpretar la respuesta JSON: {e}")
        return []


def render():
    print("\n--- Scraping Module: Búsqueda en Google ---")
    query = input("🔍 Introduce tu búsqueda en Google: ")
    max_results = input("🔢 ¿Cuántas URLs deseas obtener (por defecto 10)?: ")

    if not max_results.strip():
        max_results = 10
    else:
        try:
            max_results = int(max_results)
        except ValueError:
            print("⚠️ Número inválido, usando 10 resultados por defecto.")
            max_results = 10

    urls = search_google_scraperapi(query, max_results)

    if urls:
        print("\n🔗 URLs encontradas:")
        for i, url in enumerate(urls, 1):
            print(f"{i}. {url}")
    else:
        print("\n⚠️ No se encontraron URLs.")


# Si quieres probar este módulo directamente, descomenta:
# if __name__ == "__main__":
#     render()
