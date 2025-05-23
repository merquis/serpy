
import httpx
from bs4 import BeautifulSoup
from modules.scrapers.base_scraper import BaseScraper
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

class BookingScraper(BaseScraper):
    async def scrape(self, url: str) -> dict:
        resultado = {"url": url}

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    resultado.update(self.parse_html(response.text))
                    return resultado
        except Exception as e:
            resultado["httpx_error"] = str(e)

        try:
            context = await self.browser.new_context()
            page = await context.new_page()
            await page.goto(url, timeout=30000)
            html = await page.content()
            resultado.update(self.parse_html(html))
            await context.close()
        except PlaywrightTimeoutError:
            resultado["error"] = "TimeoutError (Playwright)"
        except Exception as e:
            resultado["error"] = str(e)

        return resultado

    def parse_html(self, html):
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string if soup.title else None
        return {
            "title": title,
            "meta_description": soup.find("meta", attrs={"name": "description"}).get("content", "") if soup.find("meta", attrs={"name": "description"}) else None
        }
