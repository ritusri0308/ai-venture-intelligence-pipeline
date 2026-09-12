"""
Scrapers package init.
"""
from src.scrapers.base import BaseScraper
from src.scrapers.browser import PlaywrightBrowserFetcher
from src.scrapers.jobs import JobScraper
from src.scrapers.news import DateNormalizer, NewsScraper
from src.scrapers.papers import ResearchPaperScraper
from src.scrapers.products import ProductScraper
from src.scrapers.startups import StartupScraper

__all__ = [
    "BaseScraper",
    "PlaywrightBrowserFetcher",
    "ResearchPaperScraper",
    "StartupScraper",
    "ProductScraper",
    "NewsScraper",
    "JobScraper",
    "DateNormalizer",
]
