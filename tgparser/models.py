"""Data structures produced by the analyzer and consumed by the report writer."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SamplePost(object):
    date: datetime
    text: str
    link: str | None
    categories: list[str]


@dataclass
class SourceReport(object):
    chat_id: int
    title: str
    username: str | None
    link: str
    kind: str  # "channel" or "chat"
    about: str
    participants_count: int | None
    last_activity: datetime | None
    matched_categories: list[str] = field(default_factory=list)
    sample_posts: list[SamplePost] = field(default_factory=list)

    @property
    def score(self) -> float:
        if not self.sample_posts:
            return 0.0
        return len(self.sample_posts) + 0.1 * len(self.matched_categories)
