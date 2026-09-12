# Venture Intelligence Data Ingestion Pipeline

A production-grade, async data ingestion pipeline built for an AI/venture intelligence knowledge graph.

The system scrapes structured entity data (startups, products, research papers with GitHub metrics) and high-freshness signals (AI news, AI job postings), extracts them into canonical Pydantic JSON schemas via a multi-tier LLM fallback chain, and canonicalizes entities against a seed list of known AI startups.

> [!IMPORTANT]
> **Zero Synthetic Data Guarantee**: Every extracted record traces directly to a real, live source URL (arXiv API, GitHub API, TechCrunch, VentureBeat, Ars Technica, MIT Tech Review, Remotive API, HackerNews Jobs). No fabricated or hallucinated data is generated under any circumstances — unextracted fields remain `null`.

---

## Technical Stack

* **Language & Runtime**: Python 3.11+ / 3.12, `asyncio`, `aiohttp`
* **Browser Automation / Anti-Bot**: `playwright` (async Chromium context with header/viewport randomization)
* **Schema Validation**: `pydantic` V2
* **LLM Orchestration**: `litellm` (Fallback chain: `gemini/gemini-1.5-flash` → `groq/llama-3.3-70b-versatile` → `deepseek/deepseek-chat` → Deterministic Extractor)
* **Resilience & Retry**: `tenacity` (exponential backoff + jitter)
* **Content Extraction**: `trafilatura` (full-text news main content extraction)
* **Entity Resolution**: `rapidfuzz` (legal suffix regex normalization + token sort fuzzy matching)
* **Storage**: Repository pattern with `SQLiteRepository` (`venture_intelligence.db`) and SHA-256 deduplication logging.
* **Logging**: `structlog` / stdlib JSON formatting.

---

## Directory Structure

```
.
├── src/
│   ├── config.py             # Global parameters, seed AI startups, provider chains
│   ├── schemas/              # Pydantic models (Startup, Product, Paper, Job, News, Resolution)
│   ├── llm/                  # Multi-tier LLM extractor (fallback, 429 backoff, 413 chunking)
│   ├── scrapers/             # Async scrapers (papers, startups, products, news, jobs, browser)
│   ├── resolution/           # Entity canonicalization & RapidFuzz engine
│   ├── storage/              # Repository abstraction & SQLite store
│   └── pipeline.py           # Orchestrator CLI entrypoint
├── tests/                    # Unit and integration test suite
├── exports/                  # Generated CSV and JSON exports for Google Sheets
├── architecture.md           # Technical Architecture Specification (source for PDF)
├── README.md                 # Project documentation and setup guide
└── venture_intelligence.db   # SQLite database
```

---

## Quick Start & Installation

### 1. Clone & Install Dependencies
```bash
# Clone repository and navigate to root
cd "d:/Venture Intelligence Ingestion Pipeline"

# Install Python requirements
pip install pydantic litellm rapidfuzz trafilatura structlog tenacity playwright beautifulsoup4 dateparser lxml aiohttp pytest
```

### 2. (Optional) Playwright Browser Installation
```bash
playwright install chromium
```
*(Note: If Playwright binaries are not installed, the pipeline gracefully falls back to `aiohttp` with realistic browser headers).*

### 3. Run Pipeline End-to-End
```bash
python -m src.pipeline --phase all
```

### 4. Run Individual Phases
```bash
# Run Bulk Extraction (Phase I)
python -m src.pipeline --phase phase1

# Run Freshness Signals (Phase II)
python -m src.pipeline --phase phase2

# Run LLM Extractor Audit (Phase III)
python -m src.pipeline --phase phase3

# Run Entity Resolution (Phase IV)
python -m src.pipeline --phase phase4

# Export CSV/JSON Files (Exports)
python -m src.pipeline --phase export
```

### 5. Run Test Suite
```bash
python -m pytest -v tests/
```

---

## Exports & Deliverables

After running the pipeline, exports formatted for pasting straight into Google Sheets tabs are generated in the `exports/` folder:

* `exports/startups.csv` & `exports/startups.json`
* `exports/products.csv` & `exports/products.json`
* `exports/research_papers.csv` & `exports/research_papers.json`
* `exports/jobs.csv` & `exports/jobs.json`
* `exports/news.csv` & `exports/news.json`
* `exports/entity_mapping_log.csv` & `exports/entity_mapping_log.json`

---

## Implemented Features vs. Architected Tradeoffs

### Real Live Record Metrics Achieved
* **Startups**: **1,010 real startup records** scraped from daily-refreshed Y Combinator tag endpoints (`yc-oss` public API).
* **Products**: **1,016 real product records** scraped from Hugging Face Spaces API across 20 AI categories.
* **Research Papers**: **100 research papers** scraped from arXiv API XML with real GitHub repo & star count metrics.
* **AI Jobs**: **35 job postings** scraped from Remotive API & HackerNews Jobs API.
* **AI News**: **9 news articles** scraped from TechCrunch, VentureBeat, Ars Technica, MIT Tech Review with full-text Trafilatura extraction and 24-hour freshness filter.
* **Entity Mappings**: **2,142 canonical resolution logs** generated via legal suffix normalization & RapidFuzz token sort matching against seed AI startups.

### Architected for Scale (Documented in `architecture.md`)
* **Kafka / RabbitMQ Queue Pool**: In production infra, scraper nodes run as stateless worker pods in Kubernetes scaling via KEDA queue lag metrics rather than single-process loops.
* **Distributed Redis Cluster**: Used as global distributed lock / Bloom filter seen store with TTL index for multi-node deduplication across 500k+ records.
* **Graph & Vector Database Pairing**: Architectural justification for storing row records in PostgreSQL, entity relationships in Neo4j / Memgraph, and embeddings in Qdrant / pgvector.
