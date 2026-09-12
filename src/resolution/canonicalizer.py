"""
Entity Canonicalization and Resolution Module.
Normalizes legal suffixes/punctuation and performs deterministic & fuzzy matching
against a seed list of known AI startups.
"""

import re
from typing import List, Optional, Tuple
from rapidfuzz import fuzz, process

from src.config import SEED_AI_STARTUPS
from src.schemas import EntityMappingRecord


class EntityCanonicalizer:
    """
    Entity Resolution Engine.
    Resolves raw entity names (startups, products, vendors) to canonical names
    using legal suffix stripping and rapidfuzz matching against seed entities.
    """

    # Common corporate legal suffixes to strip
    LEGAL_SUFFIX_REGEX = re.compile(
        r"\b(?:Inc\.?|Ltd\.?|LLC|Corp\.?|Corporation|Pte\.?\s*Ltd\.?|GmbH|Co\.?|Company|Holdings|Technologies|Labs|A\.I\.|AI)\b",
        re.IGNORECASE,
    )

    def __init__(self, seed_entities: Optional[List[str]] = None, fuzzy_threshold: float = 85.0):
        self.seed_entities = seed_entities or SEED_AI_STARTUPS
        self.fuzzy_threshold = fuzzy_threshold
        
        # Pre-build normalized lookup map for seed entities
        self.seed_normalized_map = {
            self.normalize_string(name): name for name in self.seed_entities
        }

    @classmethod
    def normalize_string(cls, name: str) -> str:
        """
        Strips legal suffixes, punctuation, normalizes spacing and case.
        Example: "OpenAI, Inc." -> "openai"
        "Anthropic A.I. Labs LLC" -> "anthropic"
        """
        if not name:
            return ""
        
        # Standardize A.I. -> AI first
        cleaned = re.sub(r"\bA\.I\.", "AI", name, flags=re.IGNORECASE)

        # Strip legal suffixes repeatedly to catch compound suffixes (e.g. "AI Labs LLC")
        for _ in range(3):
            cleaned = cls.LEGAL_SUFFIX_REGEX.sub("", cleaned)

        cleaned = re.sub(r"[,\.\-\:]", " ", cleaned)
        
        # Remove non-alphanumeric except spaces
        cleaned = re.sub(r"[^\w\s]", "", cleaned)
        
        # Collapse whitespace & lowercase
        cleaned = " ".join(cleaned.split()).lower()
        return cleaned

    def resolve(self, raw_name: str, entity_type: str = "STARTUP") -> Tuple[str, EntityMappingRecord]:
        """
        Resolves a raw entity name to a canonical name.
        Returns tuple of (canonical_name, EntityMappingRecord).
        """
        if not raw_name or not raw_name.strip():
            rec = EntityMappingRecord(
                raw_name=raw_name or "Unknown",
                canonical_name="Unknown",
                match_method="unresolved",
                confidence_score=0.0,
                entity_type=entity_type
            )
            return "Unknown", rec

        clean_raw = raw_name.strip()

        # Step 1: Exact match check against seed entities (case-insensitive)
        for seed in self.seed_entities:
            if clean_raw.lower() == seed.lower():
                rec = EntityMappingRecord(
                    raw_name=clean_raw,
                    canonical_name=seed,
                    match_method="exact",
                    confidence_score=1.0,
                    entity_type=entity_type
                )
                return seed, rec

        # Step 2: Normalized match check
        norm_raw = self.normalize_string(clean_raw)
        if norm_raw in self.seed_normalized_map:
            canonical = self.seed_normalized_map[norm_raw]
            rec = EntityMappingRecord(
                raw_name=clean_raw,
                canonical_name=canonical,
                match_method="normalized",
                confidence_score=0.95,
                entity_type=entity_type
            )
            return canonical, rec

        # Step 3: Fuzzy matching using RapidFuzz token_sort_ratio
        best_match = process.extractOne(
            norm_raw,
            self.seed_normalized_map.keys(),
            scorer=fuzz.token_sort_ratio
        )

        if best_match and best_match[1] >= self.fuzzy_threshold:
            matched_norm = best_match[0]
            confidence = round(best_match[1] / 100.0, 3)
            canonical = self.seed_normalized_map[matched_norm]
            rec = EntityMappingRecord(
                raw_name=clean_raw,
                canonical_name=canonical,
                match_method="fuzzy",
                confidence_score=confidence,
                entity_type=entity_type
            )
            return canonical, rec

        # Step 4: Unresolved fallback (Cleaned title-cased name)
        canonical_fallback = norm_raw.title() if norm_raw else clean_raw.title()
        rec = EntityMappingRecord(
            raw_name=clean_raw,
            canonical_name=canonical_fallback,
            match_method="unresolved",
            confidence_score=0.5,
            entity_type=entity_type
        )
        return canonical_fallback, rec
