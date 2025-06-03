import asyncio

from rebrowser_playwright.async_api import async_playwright

async def main() -> None:
    async with async_playwright() as p:
        for browser_type in [p.chromium, p.firefox, p.webkit]:
            browser = await browser_type.launch()
            page = await browser.new_page()
            assert await page.evaluate("() => 11 * 11") == 121
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
