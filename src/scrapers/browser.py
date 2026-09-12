"""
Phase V - Anti-Bot Strategy & Playwright Async Browser Automation Module.
"""

import asyncio
import logging
import random
from typing import Optional

logger = logging.getLogger("BrowserFetcher")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]


class PlaywrightBrowserFetcher:
    """
    Playwright-based fetcher for Cloudflare-protected or heavily JS-rendered sources.
    Implements realistic header spoofing, viewport randomization, stealth scripts,
    and randomized delays to emulate human behavior.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless

    async def fetch_html(self, url: str, wait_selector: Optional[str] = None) -> Optional[str]:
        """
        Launches Playwright Chromium context, navigates to target URL with randomized delay,
        and retrieves fully rendered DOM HTML.
        """
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                    ]
                )
                user_agent = random.choice(USER_AGENTS)
                context = await browser.new_context(
                    user_agent=user_agent,
                    viewport={"width": random.randint(1280, 1920), "height": random.randint(800, 1080)},
                    locale="en-US",
                    timezone_id="America/New_York"
                )

                page = await context.new_page()
                
                # Stealth injection: override navigator.webdriver
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)

                logger.info(f"[Playwright] Navigating to JS-rendered URL: {url}")
                await page.goto(url, wait_until="networkidle", timeout=30000)

                # Emulate human delay
                delay = random.uniform(1.5, 3.5)
                await asyncio.sleep(delay)

                if wait_selector:
                    await page.wait_for_selector(wait_selector, timeout=10000)

                content = await page.content()
                await browser.close()
                return content

        except Exception as e:
            logger.warning(f"[Playwright] Playwright fetch failed or browser binaries not installed for {url}: {e}")
            logger.info("Falling back to aiohttp HTTP fetch.")
            return await self._fallback_aiohttp_fetch(url)

    async def _fallback_aiohttp_fetch(self, url: str) -> Optional[str]:
        import aiohttp
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        return await resp.text()
        except Exception as err:
            logger.error(f"Fallback fetch error for {url}: {err}")
        return None
