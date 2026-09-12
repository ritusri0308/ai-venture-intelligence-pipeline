"""
Configuration management for the Venture Intelligence Data Ingestion Pipeline.
"""

import os
from pathlib import Path
from typing import List

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "venture_intelligence.db"
EXPORT_DIR = BASE_DIR / "exports"

# Concurrency & Scraper settings
DEFAULT_CONCURRENCY = 5
MAX_RETRIES = 3
REQUEST_TIMEOUT = 15.0

# GitHub API Settings
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_API_BASE = "https://api.github.com"

# LLM Provider Fallback Chain (litellm model names)
LLM_FALLBACK_CHAIN: List[str] = [
    "gemini/gemini-1.5-flash",
    "groq/llama-3.3-70b-versatile",
    "deepseek/deepseek-chat",
]

# Seed list of ~50 known AI startups for entity resolution
SEED_AI_STARTUPS: List[str] = [
    "OpenAI",
    "Anthropic",
    "Mistral AI",
    "Cohere",
    "Scale AI",
    "Hugging Face",
    "Perplexity",
    "Midjourney",
    "Runway",
    "ElevenLabs",
    "DeepL",
    "Cursor",
    "Harvey",
    "Anyscale",
    "Together AI",
    "Pinecone",
    "Qdrant",
    "Chroma",
    "LangChain",
    "LlamaIndex",
    "Synthesia",
    "HeyGen",
    "Character.ai",
    "Poolside",
    "Cognition",
    "Fireworks AI",
    "Groq",
    "Cerebras",
    "SambaNova Systems",
    "Graphcore",
    "Modal Labs",
    "Replicate",
    "Baseten",
    "Vellum",
    "Arize AI",
    "Weights & Biases",
    "Unstructured",
    "Fixie",
    "Decagon",
    "Mercor",
    "Physical Intelligence",
    "Imbue",
    "Reflection AI",
    "CoreWeave",
    "Lambda Labs",
    "Crusoe Energy",
    "Writer",
    "Glean",
    "Abridge",
    "Heuristics AI",
]

# AI News Sources (Phase II)
NEWS_SOURCES = [
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "Ars Technica AI", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab"},
    {"name": "MIT Tech Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/"},
    {"name": "Decrypt AI", "url": "https://decrypt.co/feed"},
]

# AI Job Sources (Phase II)
JOB_SOURCES = [
    {"name": "WeWorkRemotely AI", "url": "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss"},
    {"name": "RemoteOK AI", "url": "https://remoteok.com/api"},
    {"name": "HackerNews Hiring", "url": "https://news.ycombinator.com/submitted?id=whoishiring"},
    {"name": "Jobspresso AI", "url": "https://jobspresso.co/category/remote-dev-jobs/"},
    {"name": "CryptoJobsList AI", "url": "https://cryptojobslist.com/ai"},
]
