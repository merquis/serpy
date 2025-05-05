from bs4 import BeautifulSoup
import requests

def scrape_tags_from_url(url, etiquetas):
    resultado = {"url": url}

    try:
        response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resultado["status_code"] = response.status_code

        if response.status_code != 200:
            return resultado

        soup = BeautifulSoup(response.text, "html.parser")

        if "title" in etiquetas:
            resultado["title"] = soup.title.string.strip() if soup.title and soup.title.string else ""

        if "description" in etiquetas:
            descripcion = ""
            try:
                meta_tag = soup.find("meta", attrs={"name": "description"})
                if meta_tag and meta_tag.get("content"):
                    descripcion = meta_tag["content"].strip()
            except Exception as e:
                descripcion = f"(Error al extraer descripción: {e})"
            resultado["description"] = descripcion

        if "h1" in etiquetas:
            h1_tag = soup.find("h1")
            resultado["h1"] = h1_tag.get_text(strip=True) if h1_tag else ""

        if "h2" in etiquetas:
            resultado["h2"] = [tag.get_text(strip=True) for tag in soup.find_all("h2")]

        if "h3" in etiquetas:
            resultado["h3"] = [tag.get_text(strip=True) for tag in soup.find_all("h3")]

    except Exception as e:
        resultado["status_code"] = "error"
        resultado["error"] = str(e)

    return resultado
