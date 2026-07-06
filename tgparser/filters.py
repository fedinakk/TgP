"""Pure text-matching helpers: no network, easy to unit test."""
from __future__ import annotations

import re

from .keywords import CATEGORIES, JOB_TERMS, PRICE_PATTERN, SPAM_TERMS, WELCOME_PATTERNS

_WELCOME_RE = [re.compile(p, re.IGNORECASE) for p in WELCOME_PATTERNS]
_PRICE_RE = re.compile(PRICE_PATTERN, re.IGNORECASE)


def _contains_any(text: str, terms: tuple[str, ...]) -> list[str]:
    """Match terms as word-starts, not whole words: Russian noun/verb endings
    (видеомонтажер -> видеомонтажера, креатив -> креативов) mean the tail of
    a term is a stem, not a complete word.
    """
    lowered = text.lower()
    hits = []
    for term in terms:
        pattern = r"(?<![a-zа-я0-9])" + re.escape(term.lower())
        if re.search(pattern, lowered):
            hits.append(term)
    return hits


def matched_categories(text: str) -> list[str]:
    """Category keys whose content_terms appear in the text."""
    return [cat.key for cat in CATEGORIES if _contains_any(text, cat.content_terms)]


def is_spam(text: str) -> bool:
    return bool(_contains_any(text, SPAM_TERMS))


def is_bot_welcome(text: str) -> bool:
    """Auto-generated "new member joined" greetings, not real posts."""
    return any(p.search(text) for p in _WELCOME_RE)


def matched_job_terms(text: str) -> list[str]:
    return _contains_any(text, JOB_TERMS)


def has_price_signal(text: str) -> bool:
    return bool(_PRICE_RE.search(text.lower()))


def is_relevant_job_post(text: str) -> tuple[bool, list[str]]:
    """A post counts as a relevant order/job post if it names the niche,
    looks like a job/order (hiring term or a price/currency mention), and
    isn't spam or an auto-generated welcome message.
    """
    if not text or is_spam(text) or is_bot_welcome(text):
        return False, []
    categories = matched_categories(text)
    if not categories:
        return False, []
    if not matched_job_terms(text) and not has_price_signal(text):
        return False, []
    return True, categories
