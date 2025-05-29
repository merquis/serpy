import asyncio
from typing import Optional, Tuple
from rebrowser_playwright.async_api import async_playwright

async def get_html_with_playwright(
    url: str,
    browser_type: str = "chromium"
) -> Tuple[Optional[str], Optional[str]]:
    """
    Abre la URL con rebrowser-playwright y devuelve el HTML y el título de la página.
    Usa la configuración por defecto de rebrowser-playwright, sin parámetros de ofuscación ni personalización.
    Args:
        url: URL a scrapear.
        browser_type: "chromium", "firefox" o "webkit".
    Returns:
        (html, title) o (None, None) si falla.
    """
    try:
        async with async_playwright() as p:
            browser_launcher = {
                "chromium": p.chromium,
                "firefox": p.firefox,
                "webkit": p.webkit
            }.get(browser_type, p.chromium)
            browser = await browser_launcher.launch()
            page = await browser.new_page()
            await page.goto(url)
            html = await page.content()
            title = await page.title()
            await browser.close()
            return html, title
    except Exception as e:
        return None, None

# Ejemplo de uso/test manual
if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    async def test():
        html, title = await get_html_with_playwright(url)
        print("Título:", title)
        print("Longitud HTML:", len(html) if html else "Error")
    asyncio.run(test())
