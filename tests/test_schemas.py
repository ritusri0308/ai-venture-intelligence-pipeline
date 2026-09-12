"""
Unit tests for Pydantic V2 Schemas.
"""

from pydantic import ValidationError
import pytest

from src.schemas import (
    EntityMappingRecord,
    JobContent,
    JobRecord,
    NewsContent,
    NewsRecord,
    PricingModel,
    ProductContent,
    ProductRecord,
    ResearchPaperContent,
    ResearchPaperRecord,
    SourceInfo,
    StartupContent,
    StartupData,
    StartupRecord,
)


def test_startup_schema():
    record = StartupRecord(
        schemaVersion="1.0",
        recordType="STARTUP",
        source=SourceInfo(name="YC", url="https://ycombinator.com/companies/openai"),
        content=StartupContent(
            entityName="OpenAI",
            data=StartupData(employeeCount=1200, foundingYear=2015, location="San Francisco, CA")
        )
    )
    assert record.recordType == "STARTUP"
    assert record.content.entityName == "OpenAI"
    assert record.content.data.employeeCount == 1200


def test_product_schema():
    record = ProductRecord(
        schemaVersion="1.0",
        recordType="PRODUCT",
        source=SourceInfo(name="ProductHunt", url="https://chatgpt.com"),
        content=ProductContent(
            startupName="OpenAI",
            productName="ChatGPT",
            pricingModel=PricingModel.FREEMIUM,
            description="Conversational AI Assistant"
        )
    )
    assert record.recordType == "PRODUCT"
    assert record.content.pricingModel == PricingModel.FREEMIUM


def test_research_paper_schema():
    record = ResearchPaperRecord(
        schemaVersion="1.0",
        recordType="RESEARCH_PAPER",
        source=SourceInfo(name="arXiv", url="https://arxiv.org/abs/2401.00001"),
        content=ResearchPaperContent(
            title="Attention Is All You Need",
            authors=["Vaswani et al."],
            paper_url="https://arxiv.org/abs/2401.00001",
            github_url="https://github.com/tensorflow/tensor2tensor",
            github_stars=15000,
            published_date="2017-06-12"
        )
    )
    assert record.content.github_stars == 15000


def test_job_schema():
    record = JobRecord(
        schemaVersion="1.0",
        recordType="JOB",
        source=SourceInfo(name="RemoteOK", url="https://remoteok.com/l/12345"),
        content=JobContent(
            company="Anthropic",
            date="2026-09-11",
            is_remote=True,
            role_family="Engineering",
            title="Member of Technical Staff"
        )
    )
    assert record.content.is_remote is True


def test_news_schema():
    record = NewsRecord(
        schemaVersion="1.0",
        recordType="NEWS",
        source=SourceInfo(name="TechCrunch", url="https://techcrunch.com/article"),
        content=NewsContent(
            title="AI Ingestion Breakthrough",
            published_date="2026-09-11T12:00:00Z",
            date_confidence="exact",
            article_url="https://techcrunch.com/article",
            summary="New high-freshness signal scraper launched."
        )
    )
    assert record.content.date_confidence == "exact"
