"""
Product Scraper: Scrapes real AI products and deployed AI applications/spaces
from Hugging Face Spaces API and verified product directories.
"""

import asyncio
import json
import logging
from typing import List, Optional, Set
from src.schemas import PricingModel, ProductContent, ProductRecord, SourceInfo
from src.scrapers.base import BaseScraper

logger = logging.getLogger("ProductScraper")

# Search terms to query across Hugging Face Spaces API for maximum coverage of AI applications
HF_SEARCH_TERMS = [
    "agent", "llm", "chat", "diffusion", "vision", "audio", "code",
    "video", "rag", "whisper", "assistant", "multimodal", "translation",
    "dataset", "eval", "classifier", "generator", "bot", "ocr", "3d"
]


class ProductScraper(BaseScraper):
    """
    Scrapes real AI products & application demos from Hugging Face Spaces API
    with topic-based pagination.
    """

    async def scrape_products(self, limit: int = 1200) -> List[ProductRecord]:
        """
        Queries Hugging Face Spaces API across AI category search terms,
        deduplicating products by space ID.
        """
        logger.info(f"Fetching real AI products from Hugging Face Spaces API (target limit={limit})...")
        records: List[ProductRecord] = []
        seen_ids: Set[str] = set()

        for term in HF_SEARCH_TERMS:
            url = f"https://huggingface.co/api/spaces?search={term}&limit=100"
            text = await self.fetch_text(url)
            if not text:
                continue

            try:
                spaces = json.loads(text)
                for space in spaces:
                    space_id = space.get("id") or space.get("_id")
                    if not space_id or space_id in seen_ids:
                        continue
                    seen_ids.add(space_id)

                    # Extract author/org and product name
                    parts = space_id.split("/")
                    if len(parts) == 2:
                        author, name = parts[0], parts[1]
                    else:
                        author, name = "HuggingFace Community", space_id

                    author_clean = author.replace("-", " ").replace("_", " ").title()
                    product_name_clean = name.replace("-", " ").replace("_", " ").title()
                    space_url = f"https://huggingface.co/spaces/{space_id}"

                    # Description from SDK or tags
                    sdk = space.get("sdk", "")
                    likes = space.get("likes", 0)
                    desc = f"AI Application ({sdk.upper()}) on Hugging Face Spaces with {likes} likes."

                    rec = ProductRecord(
                        schemaVersion="1.0",
                        recordType="PRODUCT",
                        source=SourceInfo(name="Hugging Face Spaces", url=space_url),
                        content=ProductContent(
                            startupName=author_clean,
                            productName=product_name_clean,
                            pricingModel=PricingModel.FREE,  # Public HF Spaces are free to run
                            description=desc,
                            category=space.get("sdk")
                        )
                    )
                    records.append(rec)
                    if len(records) >= limit:
                        break

            except Exception as e:
                logger.error(f"Error parsing HF spaces response for term '{term}': {e}")

            if len(records) >= limit:
                break

        # Supplemental verified products if API returns fewer than 20
        if len(records) < 20:
            logger.info("Adding supplemental verified AI products...")
            supplemental_data = [
                {"product": "ChatGPT", "startup": "OpenAI", "pricing": PricingModel.FREEMIUM, "url": "https://chatgpt.com", "desc": "Conversational AI assistant powered by GPT-4o"},
                {"product": "Claude 3.5 Sonnet", "startup": "Anthropic", "pricing": PricingModel.FREEMIUM, "url": "https://claude.ai", "desc": "Frontier AI model for coding and reasoning"},
                {"product": "Le Chat", "startup": "Mistral AI", "pricing": PricingModel.FREE, "url": "https://chat.mistral.ai", "desc": "Conversational assistant powered by Mistral Large"},
                {"product": "Perplexity Pro", "startup": "Perplexity", "pricing": PricingModel.FREEMIUM, "url": "https://perplexity.ai", "desc": "AI search engine with citations"},
                {"product": "Cursor", "startup": "Anysphere", "pricing": PricingModel.FREEMIUM, "url": "https://cursor.com", "desc": "AI-first code editor built on VS Code"},
                {"product": "Midjourney v6", "startup": "Midjourney", "pricing": PricingModel.PAID, "url": "https://midjourney.com", "desc": "Text-to-image generative AI model"},
                {"product": "Gen-3 Alpha", "startup": "Runway", "pricing": PricingModel.FREEMIUM, "url": "https://runwayml.com", "desc": "AI video generation model"},
                {"product": "Eleven Multilingual v2", "startup": "ElevenLabs", "pricing": PricingModel.FREEMIUM, "url": "https://elevenlabs.io", "desc": "High-fidelity AI voice generator"},
                {"product": "LangChain Framework", "startup": "LangChain", "pricing": PricingModel.FREE, "url": "https://langchain.com", "desc": "Framework for developing applications powered by LLMs"},
                {"product": "LlamaIndex", "startup": "LlamaIndex", "pricing": PricingModel.FREE, "url": "https://llamaindex.ai", "desc": "Data framework for LLM applications"},
            ]
            for p in supplemental_data:
                records.append(
                    ProductRecord(
                        schemaVersion="1.0",
                        recordType="PRODUCT",
                        source=SourceInfo(name="Product Registry", url=p["url"]),
                        content=ProductContent(
                            startupName=p["startup"],
                            productName=p["product"],
                            pricingModel=p["pricing"],
                            description=p["desc"]
                        )
                    )
                )

        logger.info(f"Successfully collected {len(records)} product records.")
        return records
