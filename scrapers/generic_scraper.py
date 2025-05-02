import requests
from bs4 import BeautifulSoup

def scrape_generic(urls, etiquetas):
    resultados = []
    for url in urls:
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")
            info = {"url": url}

            if "title" in etiquetas:
                info["title"] = soup.title.string.strip() if soup.title and soup.title.string else None
            if "description" in etiquetas:
                tag = soup.find("meta", attrs={"name": "description"})
                info["description"] = tag["content"].strip() if tag and tag.get("content") else None
            if "h1" in etiquetas:
                info["h1"] = [h.get_text(strip=True) for h in soup.find_all("h1")]
            if "h2" in etiquetas:
                info["h2"] = [h.get_text(strip=True) for h in soup.find_all("h2")]
            if "h3" in etiquetas:
                info["h3"] = [h.get_text(strip=True) for h in soup.find_all("h3")]

            resultados.append(info)
        except Exception as e:
            resultados.append({"url": url, "error": str(e)})
    return resultados
