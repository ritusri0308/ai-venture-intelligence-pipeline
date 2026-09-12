"""
Storage abstraction and SQLite repository implementation.
"""

from abc import ABC, abstractmethod
import hashlib
import json
import sqlite3
from typing import Any, Dict, List, Optional
import structlog

from src.schemas import (
    EntityMappingRecord,
    JobRecord,
    NewsRecord,
    ProductRecord,
    ResearchPaperRecord,
    StartupRecord,
)

logger = structlog.get_logger(__name__)


class RepositoryInterface(ABC):
    """
    Abstract repository interface for entity persistence & deduplication.
    Allows easy swapping between SQLite, PostgreSQL, or Graph databases.
    """

    @abstractmethod
    def save_startup(self, record: StartupRecord) -> bool:
        pass

    @abstractmethod
    def save_product(self, record: ProductRecord) -> bool:
        pass

    @abstractmethod
    def save_research_paper(self, record: ResearchPaperRecord) -> bool:
        pass

    @abstractmethod
    def save_job(self, record: JobRecord) -> bool:
        pass

    @abstractmethod
    def save_news(self, record: NewsRecord) -> bool:
        pass

    @abstractmethod
    def save_entity_mapping(self, record: EntityMappingRecord) -> bool:
        pass

    @abstractmethod
    def is_duplicate(self, url_or_key: str) -> bool:
        pass

    @abstractmethod
    def get_all_records(self, table_name: str) -> List[Dict[str, Any]]:
        pass


class SQLiteRepository(RepositoryInterface):
    """
    SQLite implementation of RepositoryInterface with SHA-256 deduplication logging.
    """

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Deduplication Log Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dedupe_log (
                    idempotency_key TEXT PRIMARY KEY,
                    url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Startups Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS startups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_name TEXT NOT NULL,
                    employee_count INTEGER,
                    description TEXT,
                    source_name TEXT NOT NULL,
                    source_url TEXT NOT NULL UNIQUE,
                    collected_at TEXT NOT NULL,
                    raw_json TEXT NOT NULL
                );
            """)

            # Products Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    startup_name TEXT NOT NULL,
                    product_name TEXT,
                    pricing_model TEXT,
                    source_name TEXT NOT NULL,
                    source_url TEXT NOT NULL UNIQUE,
                    collected_at TEXT NOT NULL,
                    raw_json TEXT NOT NULL
                );
            """)

            # Research Papers Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS research_papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    authors TEXT NOT NULL,
                    paper_url TEXT NOT NULL UNIQUE,
                    github_url TEXT,
                    github_stars INTEGER,
                    published_date TEXT NOT NULL,
                    collected_at TEXT NOT NULL,
                    raw_json TEXT NOT NULL
                );
            """)

            # Jobs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    title TEXT,
                    job_date TEXT NOT NULL,
                    is_remote INTEGER NOT NULL,
                    role_family TEXT NOT NULL,
                    job_url TEXT UNIQUE,
                    collected_at TEXT NOT NULL,
                    raw_json TEXT NOT NULL
                );
            """)

            # News Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    published_date TEXT NOT NULL,
                    date_confidence TEXT NOT NULL,
                    article_url TEXT NOT NULL UNIQUE,
                    summary TEXT,
                    collected_at TEXT NOT NULL,
                    raw_json TEXT NOT NULL
                );
            """)

            # Entity Mapping Log Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entity_mapping_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_name TEXT NOT NULL,
                    canonical_name TEXT NOT NULL,
                    match_method TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    entity_type TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)

            conn.commit()

    def _compute_key(self, url: str) -> str:
        return hashlib.sha256(url.strip().lower().encode("utf-8")).hexdigest()

    def is_duplicate(self, url_or_key: str) -> bool:
        key = self._compute_key(url_or_key)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM dedupe_log WHERE idempotency_key = ?", (key,))
            return cursor.fetchone() is not None

    def _mark_seen(self, cursor: sqlite3.Cursor, url: str):
        key = self._compute_key(url)
        cursor.execute(
            "INSERT OR IGNORE INTO dedupe_log (idempotency_key, url) VALUES (?, ?)",
            (key, url),
        )

    def save_startup(self, record: StartupRecord) -> bool:
        if self.is_duplicate(record.source.url):
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO startups (entity_name, employee_count, description, source_name, source_url, collected_at, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.content.entityName,
                    record.content.data.employeeCount,
                    record.content.data.description,
                    record.source.name,
                    record.source.url,
                    record.collectedAt,
                    record.model_dump_json()
                ))
                self._mark_seen(cursor, record.source.url)
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def save_product(self, record: ProductRecord) -> bool:
        if self.is_duplicate(record.source.url):
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO products (startup_name, product_name, pricing_model, source_name, source_url, collected_at, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.content.startupName,
                    record.content.productName,
                    record.content.pricingModel.value if record.content.pricingModel else None,
                    record.source.name,
                    record.source.url,
                    record.collectedAt,
                    record.model_dump_json()
                ))
                self._mark_seen(cursor, record.source.url)
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def save_research_paper(self, record: ResearchPaperRecord) -> bool:
        if self.is_duplicate(record.content.paper_url):
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO research_papers (title, authors, paper_url, github_url, github_stars, published_date, collected_at, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.content.title,
                    json.dumps(record.content.authors),
                    record.content.paper_url,
                    record.content.github_url,
                    record.content.github_stars,
                    record.content.published_date,
                    record.collectedAt,
                    record.model_dump_json()
                ))
                self._mark_seen(cursor, record.content.paper_url)
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def save_job(self, record: JobRecord) -> bool:
        job_url = record.content.job_url or record.source.url
        if self.is_duplicate(job_url):
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO jobs (company, title, job_date, is_remote, role_family, job_url, collected_at, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.content.company,
                    record.content.title,
                    record.content.date,
                    1 if record.content.is_remote else 0,
                    record.content.role_family,
                    job_url,
                    record.collectedAt,
                    record.model_dump_json()
                ))
                self._mark_seen(cursor, job_url)
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def save_news(self, record: NewsRecord) -> bool:
        if self.is_duplicate(record.content.article_url):
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO news (title, published_date, date_confidence, article_url, summary, collected_at, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.content.title,
                    record.content.published_date,
                    record.content.date_confidence,
                    record.content.article_url,
                    record.content.summary,
                    record.collectedAt,
                    record.model_dump_json()
                ))
                self._mark_seen(cursor, record.content.article_url)
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def save_entity_mapping(self, record: EntityMappingRecord) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO entity_mapping_log (raw_name, canonical_name, match_method, confidence_score, entity_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                record.raw_name,
                record.canonical_name,
                record.match_method,
                record.confidence_score,
                record.entity_type,
                record.created_at
            ))
            conn.commit()
            return True

    def get_all_records(self, table_name: str) -> List[Dict[str, Any]]:
        valid_tables = {"startups", "products", "research_papers", "jobs", "news", "entity_mapping_log"}
        if table_name not in valid_tables:
            raise ValueError(f"Invalid table name: {table_name}")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name}")
            return [dict(row) for row in cursor.fetchall()]
