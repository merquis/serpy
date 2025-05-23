
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from modules.scrapers.base_scraper import BaseScraper

class EtiquetasScraper(BaseScraper):
    async def scrape(self, url: str) -> dict:
        resultado = await self.scrape_tags_with_httpx(url)
        if resultado.get("status_code") == 200:
            return resultado

        # Fallback con Playwright
        resultado = {"url": url}
        page = None
        context = None

        try:
            context = await self.browser.new_context(
                ignore_https_errors=True,
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await page.set_extra_http_headers({
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
            })
            await page.goto(url, timeout=60000, wait_until="load")
            await page.mouse.move(100, 100)
            await page.keyboard.press("PageDown")
            await page.wait_for_timeout(2000)

            html = await page.content()
            resultado["status_code"] = 200
            resultado.update(self.parse_html_content(html))

        except Exception as e:
            resultado["status_code"] = "error"
            resultado["error"] = str(e)

        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context:
                try:
                    await context.close()
                except Exception:
                    pass

        return resultado

    async def scrape_tags_with_httpx(self, url: str) -> dict:
        resultado = {"url": url}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0, headers=headers, follow_redirects=True) as client:
                response = await client.get(url)
                resultado["status_code"] = response.status_code

                if response.status_code != 200:
                    return resultado

                resultado.update(self.parse_html_content(response.text))
        except Exception as e:
            resultado["status_code"] = "error"
            resultado["error"] = str(e)

        return resultado

    def parse_html_content(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        result = {}

        if soup.title and soup.title.string:
            result["title"] = soup.title.string.strip()

        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and meta_tag.get("content"):
            result["description"] = meta_tag["content"].strip()

        contenido = []
        current_h1 = {"titulo": "", "texto": "", "h2": []}
        current_h2 = None

        body = soup.body
        if not body:
            return result

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
                current_h1["texto"] = self.extraer_texto_bajo(el)
            elif tag == "h2":
                current_h2 = {
                    "titulo": el.get_text(strip=True),
                    "texto": self.extraer_texto_bajo(el),
                    "h3": []
                }
                current_h1["h2"].append(current_h2)
            elif tag == "h3" and current_h2 is not None:
                current_h2["h3"].append({
                    "titulo": el.get_text(strip=True),
                    "texto": self.extraer_texto_bajo(el)
                })
            i += 1

        if current_h1["titulo"]:
            contenido.append(current_h1)
        if contenido:
            result["h1"] = contenido[0]

        return result

    def extraer_texto_bajo(self, tag):
        contenido = []
        for sibling in tag.find_next_siblings():
            if sibling.name and sibling.name.lower() in ["h1", "h2", "h3"]:
                break
            texto = sibling.get_text(" ", strip=True)
            if texto:
                contenido.append(texto)
        return " ".join(contenido)
