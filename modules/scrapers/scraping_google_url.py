
import httpx
from bs4 import BeautifulSoup
from modules.scrapers.base_scraper import BaseScraper
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

class GenericScraper(BaseScraper):
    async def scrape(self, url: str) -> dict:
        resultado = {"url": url}

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    html = response.text
                    resultado["html"] = html[:1000]  # solo para depurar
                    return resultado
        except Exception as e:
            resultado["httpx_error"] = str(e)

        # Fallback a Playwright si httpx falla o devuelve otro status
        try:
            context = await self.browser.new_context()
            page = await context.new_page()
            await page.goto(url, timeout=30000)
            html = await page.content()
            resultado["html"] = html[:1000]  # solo para depurar
            await context.close()
        except PlaywrightTimeoutError:
            resultado["error"] = "TimeoutError (Playwright)"
        except Exception as e:
            resultado["error"] = str(e)

        return resultado
