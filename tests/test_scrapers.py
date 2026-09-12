"""
Unit tests for Scrapers and Date Normalizer.
"""

from datetime import datetime, timedelta, timezone
from src.scrapers.news import DateNormalizer


def test_date_normalizer_relative():
    now = datetime.now(timezone.utc)
    dt, conf = DateNormalizer.parse_date("2 hours ago")
    assert conf == "exact"
    assert abs((now - dt).total_seconds() - 7200) < 60


def test_date_normalizer_iso():
    dt, conf = DateNormalizer.parse_date("2026-09-11T14:30:00Z")
    assert conf == "exact"
    assert dt.year == 2026
    assert dt.month == 9
    assert dt.day == 11


def test_date_normalizer_heuristic_fallback():
    now = datetime.now(timezone.utc)
    dt, conf = DateNormalizer.parse_date(None, http_last_modified="Thu, 11 Sep 2026 14:00:00 GMT")
    assert conf == "heuristic"
    assert dt.year == 2026
