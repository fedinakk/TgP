"""Pure text-matching helpers: no network, easy to unit test."""
from __future__ import annotations

import re

from .keywords import CATEGORIES, JOB_TERMS, SPAM_TERMS


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


def matched_job_terms(text: str) -> list[str]:
    return _contains_any(text, JOB_TERMS)


def is_relevant_job_post(text: str) -> tuple[bool, list[str]]:
    """A post counts as a relevant order/job post if it names the niche,
    looks like a job/order (has a hiring/offer term), and isn't spam.
    """
    if not text or is_spam(text):
        return False, []
    categories = matched_categories(text)
    if not categories:
        return False, []
    if not matched_job_terms(text):
        return False, []
    return True, categories
