"""Dependency-free safety and grounding screening checks for LLM outputs.
These heuristics are not proof that a response is safe or factually correct.
"""
from __future__ import annotations
import re

PROMPT_INJECTION_PATTERNS = [
    r"ignore (?:all )?(?:previous|prior|above) instructions",
    r"disregard (?:all )?(?:previous|prior|above) instructions",
    r"reveal (?:the )?(?:system prompt|hidden instructions)",
    r"you are now (?:a|an)\b",
    r"developer message:\s*",
    r"system prompt:\s*",
    r"do not follow (?:the )?(?:system|developer) instructions",
    r"output (?:the )?api key",
]
PII_PATTERNS = {
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "phone": re.compile(r"(?<!\d)(?:\+?91[- ]?)?[6-9]\d{9}(?!\d)"),
    "pan": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.I),
    "aadhaar_like": re.compile(r"(?<!\d)(?!000000000000)\d{12}(?!\d)"),
}


def detect_prompt_injection(text: str) -> list[str]:
    """Return indicators for common prompt-injection phrases in untrusted text."""
    if not isinstance(text, str) or not text:
        return []
    lowered = text.lower()
    return [pattern for pattern in PROMPT_INJECTION_PATTERNS if re.search(pattern, lowered)]


def detect_pii(text: str) -> list[str]:
    """Return detected PII categories, never the matched personal values."""
    if not isinstance(text, str) or not text:
        return []
    return [name for name, pattern in PII_PATTERNS.items() if pattern.search(text)]


def token_groundedness(answer: str, evidence: str) -> float:
    """Lexical evidence overlap in [0, 1]; not semantic fact verification."""
    def tokens(value: str) -> set[str]:
        return set(re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}", (value or "").lower()))
    answer_tokens, evidence_tokens = tokens(answer), tokens(evidence)
    if not answer_tokens:
        return 1.0 if not (answer or "").strip() else 0.0
    if not evidence_tokens:
        return 0.0
    return round(len(answer_tokens & evidence_tokens) / len(answer_tokens), 4)


def find_unsupported_terms(answer: str, evidence: str) -> list[str]:
    """List answer terms absent from evidence as review candidates, not hallucination verdicts."""
    def tokens(value: str) -> set[str]:
        return set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{3,}", (value or "").lower()))
    stop_words = {"this", "that", "with", "from", "were", "have", "been", "their", "there", "which", "using", "paper", "study", "results", "based", "more", "than", "also", "such", "into", "they", "these", "those", "will", "would", "could", "should", "about", "method", "model"}
    return sorted((tokens(answer) - tokens(evidence)) - stop_words)
