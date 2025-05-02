from scrapers.generic_scraper import scrape_generic
from scrapers.booking_scraper import scrape_booking
from scrapers.amazon_scraper import scrape_amazon
from scrapers.expedia_scraper import scrape_expedia

def get_scraper(source_type):
    if source_type == "generic":
        return scrape_generic
    elif source_type == "booking":
        return scrape_booking
    elif source_type == "amazon":
        return scrape_amazon
    elif source_type == "expedia":
        return scrape_expedia
    else:
        raise ValueError(f"Scraper no implementado para: {source_type}")
