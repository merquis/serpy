import requests
from bs4 import BeautifulSoup

def scrape_tags_from_url(url, etiquetas=None):
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        info = {"url": url}

        if not etiquetas:
            etiquetas = ["title", "description", "h1", "h2", "h3"]

        if "title" in etiquetas:
            info["title"] = soup.title.string.strip() if soup.title and soup.title.string else None

        if "description" in etiquetas:
            meta = soup.find("meta", attrs={"name": "description"})
            info["description"] = meta.get("content").strip() if meta and meta.has_attr("content") else None

        if "h1" in etiquetas:
            info["h1"] = [tag.get_text(strip=True) for tag in soup.find_all("h1")]

        if "h2" in etiquetas:
            info["h2"] = [tag.get_text(strip=True) for tag in soup.find_all("h2")]

        if "h3" in etiquetas:
            info["h3"] = [tag.get_text(strip=True) for tag in soup.find_all("h3")]

        return info

    except Exception as e:
        return {"url": url, "error": str(e)}
