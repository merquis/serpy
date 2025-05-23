
import asyncio

async def run_scrapers(scraper_class, urls, browser=None, max_concurrent=5):
    semaphore = asyncio.Semaphore(max_concurrent)

    async def safe_scrape(url):
        async with semaphore:
            scraper = scraper_class(browser)
            try:
                return await scraper.scrape(url)
            except Exception as e:
                return {"url": url, "error": str(e)}

    return await asyncio.gather(*[safe_scrape(u) for u in urls])
