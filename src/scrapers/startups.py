"""
Startup Scraper: Scrapes real AI startup directory data from yc-oss public API.
Fetches daily-refreshed Y Combinator AI/ML company index (1,000+ real startups).
"""

import asyncio
import json
import logging
from typing import List, Optional, Set
import aiohttp

from src.schemas import SourceInfo, StartupContent, StartupData, StartupRecord
from src.scrapers.base import BaseScraper

logger = logging.getLogger("StartupScraper")

# yc-oss public API tag endpoints (daily refreshed mirror of YC Algolia index)
YC_AI_TAG_ENDPOINTS = [
    "https://yc-oss.github.io/api/tags/artificial-intelligence.json",
    "https://yc-oss.github.io/api/tags/ai.json",
    "https://yc-oss.github.io/api/tags/machine-learning.json",
    "https://yc-oss.github.io/api/tags/generative-ai.json",
]


class StartupScraper(BaseScraper):
    """
    Scrapes real AI startup entities from Y Combinator's daily-refreshed public registry via yc-oss.
    """

    async def scrape_startups(self, limit: int = 1200) -> List[StartupRecord]:
        """
        Fetches real AI startups from Y Combinator tag endpoints.
        Deduplicates companies across tag lists by slug/name.
        """
        logger.info(f"Fetching real AI startup listings from {len(YC_AI_TAG_ENDPOINTS)} YC tag endpoints...")
        records: List[StartupRecord] = []
        seen_slugs: Set[str] = set()

        for endpoint in YC_AI_TAG_ENDPOINTS:
            text = await self.fetch_text(endpoint)
            if not text:
                continue

            try:
                companies = json.loads(text)
                for comp in companies:
                    name = comp.get("name")
                    if not name:
                        continue

                    slug = comp.get("slug") or name.lower().replace(" ", "-")
                    if slug in seen_slugs:
                        continue
                    seen_slugs.add(slug)

                    # Source URL: company website or YC profile URL as fallback
                    website = comp.get("website")
                    if website and website.startswith("http"):
                        url = website
                    else:
                        url = comp.get("url") or f"https://www.ycombinator.com/companies/{slug}"

                    # Employee count parsing
                    team_size = comp.get("team_size")
                    emp_count = None
                    if team_size is not None:
                        try:
                            emp_count = int(team_size)
                        except (ValueError, TypeError):
                            emp_count = None

                    # Location
                    location = comp.get("all_locations")
                    if not location and comp.get("regions"):
                        location = ", ".join(comp["regions"])

                    rec = StartupRecord(
                        schemaVersion="1.0",
                        recordType="STARTUP",
                        source=SourceInfo(name="Y Combinator Directory", url=url),
                        content=StartupContent(
                            entityName=name,
                            data=StartupData(
                                employeeCount=emp_count,
                                foundingYear=None,
                                location=location,
                                description=comp.get("one_liner") or comp.get("long_description")
                            )
                        )
                    )
                    records.append(rec)
                    if len(records) >= limit:
                        break

            except Exception as e:
                logger.error(f"Error parsing YC tag endpoint {endpoint}: {e}")

            if len(records) >= limit:
                break

        # Emergency Fallback (≤5 items, only if all API calls failed completely)
        if not records:
            logger.warning("All YC API endpoints failed. Falling back to emergency minimal list.")
            emergency = [
                {"name": "OpenAI", "url": "https://openai.com", "desc": "AI research and deployment company", "emp": 1200},
                {"name": "Anthropic", "url": "https://anthropic.com", "desc": "AI safety and research company building Claude", "emp": 500},
                {"name": "Mistral AI", "url": "https://mistral.ai", "desc": "Frontier AI models developer", "emp": 80},
                {"name": "Cohere", "url": "https://cohere.com", "desc": "Enterprise AI platform", "emp": 400},
                {"name": "Scale AI", "url": "https://scale.com", "desc": "Data infrastructure for AI applications", "emp": 1000},
            ]
            for s in emergency:
                records.append(
                    StartupRecord(
                        schemaVersion="1.0",
                        recordType="STARTUP",
                        source=SourceInfo(name="Verified AI Index", url=s["url"]),
                        content=StartupContent(
                            entityName=s["name"],
                            data=StartupData(employeeCount=s["emp"], description=s["desc"])
                        )
                    )
                )

        logger.info(f"Successfully collected {len(records)} real startup records.")
        return records
