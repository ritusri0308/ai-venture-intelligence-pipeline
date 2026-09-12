"""
Research Paper Scraper: Scrapes arXiv listings with multi-category pagination,
parses GitHub repositories, and fetches GitHub star metrics.
"""

import asyncio
import logging
import re
from typing import List, Optional, Set, Tuple
import xml.etree.ElementTree as ET
import aiohttp

from src.config import GITHUB_API_BASE, GITHUB_TOKEN
from src.schemas import ResearchPaperContent, ResearchPaperRecord, SourceInfo
from src.scrapers.base import BaseScraper

logger = logging.getLogger("ResearchPaperScraper")

# arXiv OAI Namespace
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

# Categories to query across arXiv API for comprehensive AI coverage
ARXIV_CATEGORIES = ["cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.NE", "stat.ML"]


class ResearchPaperScraper(BaseScraper):
    """
    Scrapes AI research papers from arXiv API across multiple CS & Stat categories
    with pagination support to reach 1,000+ unique paper records.
    """

    def __init__(self, concurrency: int = 5):
        super().__init__(concurrency=concurrency)
        self.github_semaphore = asyncio.Semaphore(2)

    async def scrape_arxiv_papers(self, target_count: int = 1000) -> List[ResearchPaperRecord]:
        """
        Queries arXiv API with pagination (`start` & `max_results`) across categories,
        deduplicating papers by paper URL.
        """
        logger.info(f"Paginating arXiv API across {len(ARXIV_CATEGORIES)} categories to reach target={target_count} papers...")
        papers: List[ResearchPaperRecord] = []
        seen_urls: Set[str] = set()
        page_size = 100

        for cat in ARXIV_CATEGORIES:
            for start in range(0, 500, page_size):
                url = f"http://export.arxiv.org/api/query?search_query=cat:{cat}&sortBy=submittedDate&sortOrder=descending&start={start}&max_results={page_size}"
                logger.info(f"Fetching arXiv [{cat}] start={start} limit={page_size}...")

                xml_data = await self.fetch_text(url)
                if not xml_data:
                    logger.warning(f"Empty or failed response for arXiv [{cat}] start={start}.")
                    break

                entries_found = 0
                try:
                    root = ET.fromstring(xml_data)
                    entries = root.findall("atom:entry", ARXIV_NS)
                    entries_found = len(entries)

                    for entry in entries:
                        # Paper URL & ID
                        id_elem = entry.find("atom:id", ARXIV_NS)
                        paper_url = id_elem.text.strip() if id_elem is not None and id_elem.text else ""
                        if not paper_url or paper_url in seen_urls:
                            continue
                        seen_urls.add(paper_url)

                        title_elem = entry.find("atom:title", ARXIV_NS)
                        title = " ".join(title_elem.text.split()) if title_elem is not None and title_elem.text else "Untitled Paper"

                        # Authors
                        author_elems = entry.findall("atom:author", ARXIV_NS)
                        authors = [
                            a.find("atom:name", ARXIV_NS).text.strip()
                            for a in author_elems
                            if a.find("atom:name", ARXIV_NS) is not None and a.find("atom:name", ARXIV_NS).text
                        ]

                        # Published date
                        pub_elem = entry.find("atom:published", ARXIV_NS)
                        pub_date = pub_elem.text.strip()[:10] if pub_elem is not None and pub_elem.text else "2026-09-11"

                        # Abstract
                        summary_elem = entry.find("atom:summary", ARXIV_NS)
                        abstract = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ""

                        # Correlate GitHub repo from abstract
                        github_url = self._extract_github_url(abstract)
                        github_stars = None

                        if github_url and len(papers) < 150:  # Fetch stars for initial subset to preserve rate limits
                            github_stars = await self._fetch_github_stars(github_url)

                        rec = ResearchPaperRecord(
                            schemaVersion="1.0",
                            recordType="RESEARCH_PAPER",
                            source=SourceInfo(name="arXiv", url=paper_url),
                            content=ResearchPaperContent(
                                title=title,
                                authors=authors,
                                paper_url=paper_url,
                                github_url=github_url,
                                github_stars=github_stars,
                                published_date=pub_date,
                                abstract=abstract[:300]
                            )
                        )
                        papers.append(rec)
                        if len(papers) >= target_count:
                            break

                except Exception as e:
                    logger.error(f"Error parsing arXiv XML for category {cat}: {e}")

                # Stop if no more entries or target reached
                if entries_found < page_size or len(papers) >= target_count:
                    break

                # Respect arXiv rate-limit guidance (~1 request per 0.5 - 1.0 sec)
                await asyncio.sleep(0.5)

            if len(papers) >= target_count:
                break

        logger.info(f"Successfully collected {len(papers)} unique research papers from arXiv.")
        return papers

    def _extract_github_url(self, text: str) -> Optional[str]:
        """Parses text/abstract for GitHub repository URLs."""
        match = re.search(r"https?://github\.com/([\w-]+)/([\w-]+)", text)
        if match:
            owner, repo = match.group(1), match.group(2)
            if owner.lower() not in ["sponsors", "topics", "features", "pricing", "about"]:
                return f"https://github.com/{owner}/{repo.rstrip('.')}"
        return None

    async def _fetch_github_stars(self, github_url: str) -> Optional[int]:
        """
        Fetches star count for a repository using GitHub REST API.
        Handles unauthenticated 60 req/hr rate limits gracefully with skip-and-log.
        """
        match = re.search(r"github\.com/([\w-]+)/([\w-]+)", github_url)
        if not match:
            return None

        owner, repo = match.group(1), match.group(2)
        api_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"

        async with self.github_semaphore:
            session = await self.get_session()
            headers = {"User-Agent": "Venture-Intelligence-Pipeline/1.0"}
            if GITHUB_TOKEN:
                headers["Authorization"] = f"token {GITHUB_TOKEN}"

            try:
                async with session.get(api_url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("stargazers_count")
                    elif resp.status in (403, 429):
                        logger.warning(f"GitHub API Rate Limit hit for {api_url} (HTTP {resp.status}). Gracefully skipping star count.")
                        return None
                    else:
                        return None
            except Exception as e:
                logger.debug(f"Error fetching GitHub stars for {github_url}: {e}")
                return None
