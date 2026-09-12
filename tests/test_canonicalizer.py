"""
Unit tests for Entity Resolution Engine (Canonicalizer).
"""

from src.resolution.canonicalizer import EntityCanonicalizer


def test_normalize_string():
    assert EntityCanonicalizer.normalize_string("OpenAI, Inc.") == "openai"
    assert EntityCanonicalizer.normalize_string("Anthropic A.I. Labs LLC") == "anthropic"
    assert EntityCanonicalizer.normalize_string("Mistral AI Pte. Ltd.") == "mistral"


def test_exact_resolution():
    canonicalizer = EntityCanonicalizer(seed_entities=["OpenAI", "Anthropic", "Mistral AI"])
    canon, rec = canonicalizer.resolve("OpenAI")
    assert canon == "OpenAI"
    assert rec.match_method == "exact"
    assert rec.confidence_score == 1.0


def test_normalized_resolution():
    canonicalizer = EntityCanonicalizer(seed_entities=["OpenAI", "Anthropic", "Mistral AI"])
    canon, rec = canonicalizer.resolve("Anthropic, Inc.")
    assert canon == "Anthropic"
    assert rec.match_method == "normalized"
    assert rec.confidence_score == 0.95


def test_fuzzy_resolution():
    canonicalizer = EntityCanonicalizer(seed_entities=["Hugging Face", "Perplexity", "Pinecone"])
    canon, rec = canonicalizer.resolve("Perplexiti AI")
    assert canon == "Perplexity"
    assert rec.match_method == "fuzzy"
    assert rec.confidence_score >= 0.85


def test_unresolved_fallback():
    canonicalizer = EntityCanonicalizer(seed_entities=["OpenAI", "Anthropic"])
    canon, rec = canonicalizer.resolve("Quantum Stealth Robotics Inc.")
    assert canon == "Quantum Stealth Robotics"
    assert rec.match_method == "unresolved"
