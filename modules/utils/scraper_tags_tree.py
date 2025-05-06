import requests
from bs4 import BeautifulSoup

def scrape_tags_as_tree(url):
    resultado = {
        "url": url
    }

    try:
        response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resultado["status_code"] = response.status_code

        if response.status_code != 200:
            return resultado

        soup = BeautifulSoup(response.text, "html.parser")

        if soup.title and soup.title.string:
            resultado["title"] = soup.title.string.strip()

        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and meta_tag.get("content"):
            resultado["description"] = meta_tag["content"].strip()

        contenido = []
        current_h1 = {"titulo": "", "texto": "", "h2": []}
        current_h2 = None

        body = soup.body
        if not body:
            return resultado

        elementos = list(body.descendants)
        i = 0
        while i < len(elementos):
            el = elementos[i]
            if not getattr(el, 'name', None):
                i += 1
                continue

            tag = el.name.lower()

            if tag == "h1":
                if current_h1["titulo"]:
                    contenido.append(current_h1)
                    current_h1 = {"titulo": "", "texto": "", "h2": []}
                current_h1["titulo"] = el.get_text(strip=True)
                current_h1["texto"] = extraer_texto_bajo(el)
            elif tag == "h2":
                current_h2 = {"titulo": el.get_text(strip=True), "texto": extraer_texto_bajo(el), "h3": []}
                current_h1["h2"].append(current_h2)
            elif tag == "h3" and current_h2 is not None:
                current_h2["h3"].append({
                    "titulo": el.get_text(strip=True),
                    "texto": extraer_texto_bajo(el)
                })

            i += 1

        if current_h1["titulo"]:
            contenido.append(current_h1)

        if contenido:
            resultado["h1"] = contenido[0]  # Solo un H1 principal

    except Exception as e:
        resultado["status_code"] = "error"
        resultado["error"] = str(e)

    return resultado


def extraer_texto_bajo(tag):
    contenido = []
    for sibling in tag.find_next_siblings():
        if sibling.name and sibling.name.lower() in ["h1", "h2", "h3"]:
            break
        texto = sibling.get_text(" ", strip=True)
        if texto:
            contenido.append(texto)
    return " ".join(contenido)
