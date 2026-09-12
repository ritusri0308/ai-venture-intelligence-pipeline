"""
Unit tests for SQLite Repository & Idempotency Deduplication.
"""

from pathlib import Path
import tempfile
from src.schemas import SourceInfo, StartupContent, StartupData, StartupRecord
from src.storage.repository import SQLiteRepository


def test_sqlite_repository_idempotency():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    repo = SQLiteRepository(db_path)
    url = "https://ycombinator.com/companies/mistral-ai"

    record = StartupRecord(
        schemaVersion="1.0",
        recordType="STARTUP",
        source=SourceInfo(name="YC", url=url),
        content=StartupContent(
            entityName="Mistral AI",
            data=StartupData(employeeCount=80)
        )
    )

    # First insert -> Should succeed
    assert repo.save_startup(record) is True

    # Duplicate check -> Should return True
    assert repo.is_duplicate(url) is True

    # Second insert of identical URL -> Should be deduplicated and return False
    assert repo.save_startup(record) is False

    # Retrieve records
    startups = repo.get_all_records("startups")
    assert len(startups) == 1
    assert startups[0]["entity_name"] == "Mistral AI"
