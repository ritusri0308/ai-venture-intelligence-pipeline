"""
Venture Intelligence Data Ingestion Pipeline - Main Entrypoint & Orchestrator.

Usage:
    python -m src.pipeline [--phase {all,phase1,phase2,phase3,phase4,phase5,export}]
"""

import argparse
import asyncio
import csv
import json
import logging
from pathlib import Path
import sys
from typing import List

from src.config import DB_PATH, EXPORT_DIR
from src.llm.extractor import LLMExtractor
from src.resolution.canonicalizer import EntityCanonicalizer
from src.schemas import (
    EntityMappingRecord,
    JobRecord,
    NewsRecord,
    ProductRecord,
    ResearchPaperRecord,
    StartupRecord,
)
from src.scrapers.browser import PlaywrightBrowserFetcher
from src.scrapers.jobs import JobScraper
from src.scrapers.news import NewsScraper
from src.scrapers.papers import ResearchPaperScraper
from src.scrapers.products import ProductScraper
from src.scrapers.startups import StartupScraper
from src.storage.repository import SQLiteRepository

# Setup Logging
logger = logging.getLogger("Pipeline")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class IngestionPipeline:
    """
    Orchestrates the 6-phase Venture Intelligence Data Ingestion Pipeline.
    """

    def __init__(self, db_path: Path = DB_PATH, export_dir: Path = EXPORT_DIR):
        self.db_path = db_path
        self.export_dir = export_dir
        self.repo = SQLiteRepository(str(db_path))
        self.llm_extractor = LLMExtractor()
        self.canonicalizer = EntityCanonicalizer()
        
        # Ensure export directory exists
        self.export_dir.mkdir(parents=True, exist_ok=True)

    async def run_phase_1(self):
        """Phase I: Bulk Extraction (Research Papers, Startups, Products)."""
        logger.info("=== Starting Phase I: Bulk Extraction ===")

        # 1. Research Papers with GitHub Metrics & Multi-Category arXiv Pagination
        paper_scraper = ResearchPaperScraper()
        papers = await paper_scraper.scrape_arxiv_papers(target_count=1000)
        await paper_scraper.close()
        for p in papers:
            self.repo.save_research_paper(p)
        logger.info(f"Phase I: Saved {len(papers)} research papers to store.")

        # 2. Real Startups (YC public API 1,000+ companies)
        startup_scraper = StartupScraper()
        startups = await startup_scraper.scrape_startups(limit=1000)
        await startup_scraper.close()
        for s in startups:
            canon_name, map_rec = self.canonicalizer.resolve(s.content.entityName, entity_type="STARTUP")
            self.repo.save_entity_mapping(map_rec)
            s.content.entityName = canon_name
            self.repo.save_startup(s)
        logger.info(f"Phase I: Saved {len(startups)} startups to store.")

        # 3. Real Products (Hugging Face Spaces API 1,000+ products)
        product_scraper = ProductScraper()
        products = await product_scraper.scrape_products(limit=1000)
        await product_scraper.close()
        for pr in products:
            canon_name, map_rec = self.canonicalizer.resolve(pr.content.startupName, entity_type="PRODUCT_STARTUP")
            self.repo.save_entity_mapping(map_rec)
            pr.content.startupName = canon_name
            self.repo.save_product(pr)
        logger.info(f"Phase I: Saved {len(products)} products to store.")

    async def run_phase_2(self):
        """Phase II: Freshness-Critical Signals (AI News & AI Jobs within 24 hours)."""
        logger.info("=== Starting Phase II: Freshness-Critical Signals ===")

        # 1. AI News (5 sources, 24h filter, full text via Trafilatura, LLMExtractor per-article enrichment)
        news_scraper = NewsScraper(extractor=self.llm_extractor)
        news_items = await news_scraper.scrape_recent_news()
        await news_scraper.close()
        for n in news_items:
            self.repo.save_news(n)
        logger.info(f"Phase II: Saved {len(news_items)} 24h news items to store.")

        # 2. AI Jobs (5 sources, 24h filter, LLMExtractor per-job enrichment)
        job_scraper = JobScraper(extractor=self.llm_extractor)
        job_items = await job_scraper.scrape_recent_jobs()
        await job_scraper.close()
        for j in job_items:
            canon_company, map_rec = self.canonicalizer.resolve(j.content.company, entity_type="JOB_COMPANY")
            self.repo.save_entity_mapping(map_rec)
            j.content.company = canon_company
            self.repo.save_job(j)
        logger.info(f"Phase II: Saved {len(job_items)} 24h job postings to store.")

    def run_phase_3(self):
        """Phase III: LLM Extraction Audit & Test Run."""
        logger.info("=== Starting Phase III: LLM Extraction Chain Validation ===")
        sample_text = (
            "OpenAI, Inc. is an artificial intelligence research laboratory based in San Francisco, CA. "
            "It has approximately 1200 employees and focuses on frontier multimodal models like GPT-4o."
        )
        extracted = self.llm_extractor.extract(sample_text, StartupRecord, system_prompt="Extract startup data.")
        if extracted:
            logger.info(f"Phase III LLM Extraction Sample Output: {extracted.content.entityName} (Employees: {extracted.content.data.employeeCount})")

    def run_phase_4(self):
        """Phase IV: Entity Resolution Engine Audit."""
        logger.info("=== Starting Phase IV: Entity Resolution ===")
        sample_names = ["Anthropic A.I. Labs LLC", "OpenAI Inc.", "Mistral AI Corp.", "Unknown AI Startup LLC"]
        for name in sample_names:
            canon, map_rec = self.canonicalizer.resolve(name)
            self.repo.save_entity_mapping(map_rec)
            logger.info(f"Resolved '{name}' -> '{canon}' ({map_rec.match_method}, confidence: {map_rec.confidence_score})")

    async def run_phase_5(self):
        """Phase V: Anti-Bot Strategy Execution with Playwright."""
        logger.info("=== Starting Phase V: Playwright Anti-Bot Web Automation ===")
        target_url = "https://techcrunch.com/category/artificial-intelligence/"
        fetcher = PlaywrightBrowserFetcher()
        html = await fetcher.fetch_html(target_url)
        if html:
            logger.info(f"[Phase V Playwright Success] Successfully rendered JS DOM for {target_url} ({len(html)} bytes returned).")
        else:
            logger.warning(f"[Phase V Playwright Note] Playwright fetch fallback completed for {target_url}.")

    def export_csv_and_json(self):
        """Phase Exports: Produces CSV and JSON files formatted for Google Sheets tabs."""
        logger.info("=== Generating CSV and JSON Exports ===")

        tables = ["startups", "products", "research_papers", "jobs", "news", "entity_mapping_log"]
        
        for table in tables:
            records = self.repo.get_all_records(table)
            
            # JSON Export
            json_file = self.export_dir / f"{table}.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, ensure_ascii=False)

            # CSV Export
            csv_file = self.export_dir / f"{table}.csv"
            if records:
                fieldnames = list(records[0].keys())
                with open(csv_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(records)

            logger.info(f"Exported {len(records)} records to {csv_file.name} & {json_file.name}")

    async def run_pipeline(self, phase: str = "all"):
        if phase in ("all", "phase1"):
            await self.run_phase_1()
        if phase in ("all", "phase2"):
            await self.run_phase_2()
        if phase in ("all", "phase3"):
            self.run_phase_3()
        if phase in ("all", "phase4"):
            self.run_phase_4()
        if phase in ("all", "phase5"):
            await self.run_phase_5()
        if phase in ("all", "export"):
            self.export_csv_and_json()

        # LLM Telemetry Provider Summary Report
        summary = self.llm_extractor.get_provider_summary()
        logger.info("==================================================")
        logger.info(f"LLM Provider Call Breakdown Summary: {summary}")
        logger.info("==================================================")
        logger.info("=== Pipeline Execution Complete ===")


def main():
    parser = argparse.ArgumentParser(description="Venture Intelligence Data Ingestion Pipeline")
    parser.add_argument(
        "--phase",
        choices=["all", "phase1", "phase2", "phase3", "phase4", "phase5", "export"],
        default="all",
        help="Specify individual phase to run or 'all' for complete pipeline.",
    )
    args = parser.parse_args()

    pipeline = IngestionPipeline()
    asyncio.run(pipeline.run_pipeline(phase=args.phase))


if __name__ == "__main__":
    main()
