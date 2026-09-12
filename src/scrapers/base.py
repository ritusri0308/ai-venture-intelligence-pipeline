"""
Base Async Scraper with Concurrency Control & Resilience.
"""

import asyncio
import logging
import random
from typing import Dict, Optional
import aiohttp
from src.config import DEFAULT_CONCURRENCY, REQUEST_TIMEOUT

logger = logging.getLogger("BaseScraper")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
]


class BaseScraper:
    """
    Base Scraper with concurrency limiting (semaphore bound), user-agent rotation,
    retry backoff, and standard HTTP headers.
    """

    def __init__(self, concurrency: int = DEFAULT_CONCURRENCY):
        self.semaphore = asyncio.Semaphore(concurrency)
        self.session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    def get_random_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
        }

    async def fetch_text(self, url: str, retries: int = 3) -> Optional[str]:
        async with self.semaphore:
            session = await self.get_session()
            headers = self.get_random_headers()

            for attempt in range(1, retries + 1):
                try:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            return await response.text()
                        elif response.status == 429:
                            backoff = (2 ** attempt) + random.uniform(0.1, 0.5)
                            logger.warning(f"HTTP 429 Rate Limit for {url}. Retrying in {backoff:.2f}s...")
                            await asyncio.sleep(backoff)
                        else:
                            logger.warning(f"HTTP {response.status} for {url}")
                            return None
                except Exception as e:
                    logger.debug(f"Fetch attempt {attempt} failed for {url}: {e}")
                    await asyncio.sleep(1.0 * attempt)

            logger.error(f"Failed to fetch {url} after {retries} retries.")
            return None

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
