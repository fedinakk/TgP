"""Renders analysis results as Markdown and JSON reports."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import SourceReport


def sort_sources(sources: list[SourceReport]) -> list[SourceReport]:
    return sorted(sources, key=lambda s: s.score, reverse=True)


def to_json(sources: list[SourceReport]) -> str:
    def default(value):
        if isinstance(value, datetime):
            return value.isoformat()
        raise TypeError(f"Not serializable: {value!r}")

    return json.dumps([asdict(s) for s in sources], default=default, ensure_ascii=False, indent=2)


def _render_source(source: SourceReport) -> list[str]:
    lines = [f"## {source.title}", ""]
    lines.append(f"- **Ссылка:** {source.link}")
    lines.append(f"- **Тип:** {'канал' if source.kind == 'channel' else 'чат'}")
    if source.participants_count:
        lines.append(f"- **Подписчиков/участников:** {source.participants_count}")
    if source.last_activity:
        lines.append(f"- **Последняя активность:** {source.last_activity.isoformat()}")
    if source.matched_categories:
        lines.append(f"- **Тематика:** {', '.join(source.matched_categories)}")
    if source.about:
        about = source.about.replace("\n", " ").strip()
        lines.append(f"- **Описание:** {about[:300]}")
    lines.append("")
    lines.append("**Примеры релевантных постов:**")
    lines.append("")
    for post in source.sample_posts:
        date_str = post.date.isoformat() if post.date else "?"
        snippet = post.text.replace("\n", " ").strip()
        link_part = f" ([пост]({post.link}))" if post.link else ""
        lines.append(f"- `{date_str}`{link_part}: {snippet}")
    lines.append("")
    return lines


def to_markdown(sources: list[SourceReport]) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    channels = [s for s in sources if s.kind == "channel"]
    chats = [s for s in sources if s.kind == "chat"]

    lines = [
        "# Telegram-источники заказов: видеомонтаж / reels / motion / SMM / креативы",
        "",
        f"_Сформировано: {generated_at}. Найдено каналов: {len(channels)}, чатов: {len(chats)}._",
        "",
    ]

    lines.append(f"# Каналы ({len(channels)})")
    lines.append("")
    for source in channels:
        lines.extend(_render_source(source))

    lines.append(f"# Чаты ({len(chats)})")
    lines.append("")
    for source in chats:
        lines.extend(_render_source(source))

    return "\n".join(lines)


def write_reports(sources: list[SourceReport], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    sources = sort_sources(sources)

    md_path = output_dir / "report.md"
    json_path = output_dir / "report.json"

    md_path.write_text(to_markdown(sources), encoding="utf-8")
    json_path.write_text(to_json(sources), encoding="utf-8")

    return md_path, json_path
