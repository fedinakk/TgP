"""Pure helpers for spotting Telegram usernames in free text (no network)."""
from __future__ import annotations

import re

_TME_LINK_RE = re.compile(r"t\.me/(?!joinchat/|\+)([a-zA-Z][a-zA-Z0-9_]{3,31})\b")


def extract_usernames(text: str) -> set[str]:
    """Public t.me/<username> links found in text. Private invite links
    (t.me/joinchat/... or t.me/+...) are skipped: they can't be resolved
    without joining, which this tool never does automatically.
    """
    if not text:
        return set()
    return {m.group(1) for m in _TME_LINK_RE.finditer(text)}


def parse_seed_line(line: str) -> str | None:
    """A line from seeds.txt -> a bare username, or None if blank/comment."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("@"):
        return line[1:]
    match = _TME_LINK_RE.search(line)
    if match:
        return match.group(1)
    return line
