
from abc import ABC, abstractmethod

class BaseScraper(ABC):
    def __init__(self, browser=None):
        self.browser = browser

    @abstractmethod
    async def scrape(self, url: str) -> dict:
        pass
