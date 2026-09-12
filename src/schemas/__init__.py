"""
Pydantic Schemas for Venture Intelligence Pipeline Entities
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


def current_iso_time() -> str:
    return datetime.now(timezone.utc).isoformat()


class SourceInfo(BaseModel):
    name: str = Field(..., description="Name of the data source e.g. arXiv, TechCrunch")
    url: str = Field(..., description="Live source URL from which record was extracted")


class PricingModel(str, Enum):
    FREE = "FREE"
    FREEMIUM = "FREEMIUM"
    PAID = "PAID"
    ENTERPRISE = "ENTERPRISE"


# 1. STARTUP
class StartupData(BaseModel):
    employeeCount: Optional[int] = Field(None, description="Number of employees if available")
    foundingYear: Optional[int] = Field(None, description="Year founded if available")
    location: Optional[str] = Field(None, description="Headquarters location")
    description: Optional[str] = Field(None, description="Short company summary")


class StartupContent(BaseModel):
    entityName: str = Field(..., description="Name of the startup entity")
    data: StartupData = Field(default_factory=StartupData)


class StartupRecord(BaseModel):
    schemaVersion: str = Field("1.0", description="Schema version tag")
    recordType: Literal["STARTUP"] = "STARTUP"
    source: SourceInfo
    content: StartupContent
    collectedAt: str = Field(default_factory=current_iso_time)


# 2. PRODUCT
class ProductContent(BaseModel):
    startupName: str = Field(..., description="Associated startup or organization name")
    productName: Optional[str] = Field(None, description="Name of the product")
    pricingModel: Optional[PricingModel] = Field(None, description="Pricing tier enum")
    description: Optional[str] = Field(None, description="Product summary")
    category: Optional[str] = Field(None, description="Product category/tag")


class ProductRecord(BaseModel):
    schemaVersion: str = Field("1.0", description="Schema version tag")
    recordType: Literal["PRODUCT"] = "PRODUCT"
    source: SourceInfo
    content: ProductContent
    collectedAt: str = Field(default_factory=current_iso_time)


# 3. RESEARCH PAPER
class ResearchPaperContent(BaseModel):
    title: str = Field(..., description="Title of the paper")
    authors: List[str] = Field(default_factory=list, description="Authors of the paper")
    paper_url: str = Field(..., description="Direct paper URL (arXiv / PDF / webpage)")
    github_url: Optional[str] = Field(None, description="Associated GitHub repo URL")
    github_stars: Optional[int] = Field(None, description="Current GitHub star count")
    published_date: str = Field(..., description="Date of paper publication")
    abstract: Optional[str] = Field(None, description="Paper abstract snippet")


class ResearchPaperRecord(BaseModel):
    schemaVersion: str = Field("1.0", description="Schema version tag")
    recordType: Literal["RESEARCH_PAPER"] = "RESEARCH_PAPER"
    source: SourceInfo
    content: ResearchPaperContent
    collectedAt: str = Field(default_factory=current_iso_time)


# 4. JOB
class JobContent(BaseModel):
    company: str = Field(..., description="Hiring company name")
    date: str = Field(..., description="Job posting date (ISO date)")
    is_remote: bool = Field(False, description="Whether position is remote")
    role_family: str = Field(..., description="Category: ML, Backend, Research, Product, Data, etc.")
    title: Optional[str] = Field(None, description="Job title")
    job_url: Optional[str] = Field(None, description="Direct job application link")
    location: Optional[str] = Field(None, description="Location description")


class JobRecord(BaseModel):
    schemaVersion: str = Field("1.0", description="Schema version tag")
    recordType: Literal["JOB"] = "JOB"
    source: SourceInfo
    content: JobContent
    collectedAt: str = Field(default_factory=current_iso_time)


# 5. NEWS
class NewsContent(BaseModel):
    title: str = Field(..., description="Headline or title")
    published_date: str = Field(..., description="Normalized publication ISO date")
    date_confidence: Literal["exact", "heuristic"] = Field("exact", description="Confidence level of date parsing")
    article_url: str = Field(..., description="Live news article URL")
    summary: Optional[str] = Field(None, description="Main article summary / snippet")
    company_mentions: List[str] = Field(default_factory=list, description="Extracted startup/company names")


class NewsRecord(BaseModel):
    schemaVersion: str = Field("1.0", description="Schema version tag")
    recordType: Literal["NEWS"] = "NEWS"
    source: SourceInfo
    content: NewsContent
    collectedAt: str = Field(default_factory=current_iso_time)


# 6. ENTITY MAPPING LOG
class EntityMappingRecord(BaseModel):
    raw_name: str = Field(..., description="Raw extracted entity name")
    canonical_name: str = Field(..., description="Resolved canonical name")
    match_method: Literal["exact", "normalized", "fuzzy", "unresolved"] = Field(..., description="Resolution algorithm used")
    confidence_score: float = Field(..., description="Match confidence score between 0.0 and 1.0")
    entity_type: str = Field(..., description="Entity type: STARTUP, PRODUCT, COMPANY, etc.")
    created_at: str = Field(default_factory=current_iso_time)
