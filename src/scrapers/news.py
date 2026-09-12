"""
AI News Signal Scraper with Trafilatura Main-Content Extraction,
Date Normalization Module, Date Confidence Heuristics, and 24-Hour Filter.
"""

from datetime import datetime, timedelta, timezone
import logging
import re
from typing import List, Optional, Tuple
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import trafilatura

from src.config import NEWS_SOURCES
from src.schemas import NewsContent, NewsRecord, SourceInfo
from src.scrapers.base import BaseScraper

logger = logging.getLogger("NewsScraper")


class DateNormalizer:
    """
    Date Normalization Engine.
    Parses absolute ISO dates, RFC dates, relative strings ('2 hours ago', 'yesterday'),
    and handles heuristic fallbacks (HTTP headers, current timestamp).
    """

    @classmethod
    def parse_date(cls, raw_date: Optional[str], http_last_modified: Optional[str] = None) -> Tuple[datetime, str]:
        """
        Returns (parsed_datetime, confidence_label).
        confidence_label: "exact" if explicit date parsed, "heuristic" if inferred.
        """
        now = datetime.now(timezone.utc)

        if not raw_date or not raw_date.strip():
            if http_last_modified:
                parsed_http = cls._parse_rfc2822(http_last_modified)
                if parsed_http:
                    return parsed_http, "heuristic"
            return now, "heuristic"

        clean_str = raw_date.strip()

        # 1. Check relative date formats ("2 hours ago", "15 minutes ago", "yesterday")
        rel_dt = cls._parse_relative_date(clean_str, now)
        if rel_dt:
            return rel_dt, "exact"

        # 2. Check ISO 8601 & RFC 2822 standard dates
        iso_dt = cls._parse_standard_date(clean_str)
        if iso_dt:
            return iso_dt, "exact"

        # 3. Fallback to HTTP Last-Modified header if present
        if http_last_modified:
            parsed_http = cls._parse_rfc2822(http_last_modified)
            if parsed_http:
                return parsed_http, "heuristic"

        # 4. Final heuristic fallback: first seen by crawler
        return now, "heuristic"

    @classmethod
    def _parse_relative_date(cls, text: str, reference_now: datetime) -> Optional[datetime]:
        lower = text.lower()
        if "yesterday" in lower:
            return reference_now - timedelta(days=1)
        
        match = re.search(r"(\d+)\s*(hour|hr|minute|min|day|sec)s?\s*ago", lower)
        if match:
            num = int(match.group(1))
            unit = match.group(2)
            if "hour" in unit or "hr" in unit:
                return reference_now - timedelta(hours=num)
            elif "min" in unit:
                return reference_now - timedelta(minutes=num)
            elif "day" in unit:
                return reference_now - timedelta(days=num)
            elif "sec" in unit:
                return reference_now - timedelta(seconds=num)
        return None

    @classmethod
    def _parse_rfc2822(cls, text: str) -> Optional[datetime]:
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(text).astimezone(timezone.utc)
        except Exception:
            return None

    @classmethod
    def _parse_standard_date(cls, text: str) -> Optional[datetime]:
        if not text:
            return None
        
        # 1. Try RFC 2822
        rfc_dt = cls._parse_rfc2822(text)
        if rfc_dt:
            return rfc_dt

        # 2. Try ISO 8601 / datetime.fromisoformat
        clean_text = text.strip()
        if clean_text.endswith("Z"):
            clean_text = clean_text[:-1] + "+00:00"

        try:
            return datetime.fromisoformat(clean_text).astimezone(timezone.utc)
        except Exception:
            pass

        # 3. Fallback strptime loops
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(text[:19], fmt[:len(text[:19])])
                return dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue

        return None


class NewsScraper(BaseScraper):
    """
    Crawls 5 AI news RSS & web sources, extracts full text via Trafilatura,
    normalizes dates, and applies a strict 24-hour filter.
    """

    async def scrape_recent_news(self, sources: Optional[List[dict]] = None) -> List[NewsRecord]:
        sources_to_scrape = sources or NEWS_SOURCES
        logger.info(f"Crawling {len(sources_to_scrape)} AI news sources...")
        
        all_articles: List[NewsRecord] = []
        now = datetime.now(timezone.utc)
        cutoff_24h = now - timedelta(hours=24)

        for source in sources_to_scrape:
            source_name = source["name"]
            feed_url = source["url"]
            logger.info(f"Scraping news feed for {source_name}: {feed_url}")

            feed_xml = await self.fetch_text(feed_url)
            if not feed_xml:
                continue

            parsed_items = self._parse_rss_items(feed_xml, source_name)
            
            for item in parsed_items[:10]:  # Up to 10 articles per source
                title = item["title"]
                article_url = item["link"]
                raw_pub_date = item.get("pubDate")

                # Fetch full text via Trafilatura
                full_html = await self.fetch_text(article_url)
                summary = None
                if full_html:
                    extracted_text = trafilatura.extract(full_html)
                    if extracted_text:
                        summary = extracted_text[:400]

                if not summary:
                    summary = item.get("description", "")[:400]

                # Date Normalization
                pub_dt, date_confidence = DateNormalizer.parse_date(raw_pub_date)

                # Hard Filter: Only emit records within the last 24 hours
                if pub_dt >= cutoff_24h or pub_dt.date() == now.date():
                    rec = NewsRecord(
                        schemaVersion="1.0",
                        recordType="NEWS",
                        source=SourceInfo(name=source_name, url=article_url),
                        content=NewsContent(
                            title=title,
                            published_date=pub_dt.isoformat(),
                            date_confidence=date_confidence,
                            article_url=article_url,
                            summary=summary,
                            company_mentions=[]
                        )
                    )
                    all_articles.append(rec)

        logger.info(f"Successfully collected {len(all_articles)} news records published within 24h.")
        return all_articles

    def _parse_rss_items(self, xml_content: str, source_name: str) -> List[dict]:
        items = []
        try:
            root = ET.fromstring(xml_content)
            channel = root.find("channel")
            if channel is not None:
                for item in channel.findall("item"):
                    title_el = item.find("title")
                    link_el = item.find("link")
                    pub_el = item.find("pubDate")
                    desc_el = item.find("description")

                    if title_el is not None and link_el is not None:
                        items.append({
                            "title": title_el.text.strip() if title_el.text else "AI News",
                            "link": link_el.text.strip() if link_el.text else feed_url,
                            "pubDate": pub_el.text.strip() if pub_el is not None and pub_el.text else None,
                            "description": desc_el.text.strip() if desc_el is not None and desc_el.text else ""
                        })
        except Exception as e:
            logger.debug(f"RSS XML parse failed for {source_name}, using BeautifulSoup fallback: {e}")
            soup = BeautifulSoup(xml_content, "xml")
            for item in soup.find_all("item"):
                t = item.find("title")
                l = item.find("link")
                d = item.find("pubDate")
                if t and l:
                    items.append({
                        "title": t.get_text(strip=True),
                        "link": l.get_text(strip=True),
                        "pubDate": d.get_text(strip=True) if d else None,
                        "description": ""
                    })
        return items
