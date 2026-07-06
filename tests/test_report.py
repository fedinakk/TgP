from datetime import datetime, timezone

from tgparser.models import SamplePost, SourceReport
from tgparser.report import sort_sources, to_markdown


def _make_source(kind: str, title: str, n_posts: int) -> SourceReport:
    return SourceReport(
        chat_id=hash(title) % 10_000,
        title=title,
        username=title.lower(),
        link=f"https://t.me/{title.lower()}",
        kind=kind,
        about="Тестовое описание",
        participants_count=100,
        last_activity=datetime.now(timezone.utc),
        matched_categories=["SMM"],
        sample_posts=[
            SamplePost(date=datetime.now(timezone.utc), text="Ищем SMM менеджера", link=None, categories=["smm"])
            for _ in range(n_posts)
        ],
    )


def test_markdown_splits_channels_and_chats_into_sections():
    sources = [
        _make_source("channel", "ChannelA", 2),
        _make_source("chat", "ChatA", 1),
        _make_source("channel", "ChannelB", 1),
    ]
    md = to_markdown(sources)
    assert "# Каналы (2)" in md
    assert "# Чаты (1)" in md
    assert md.index("# Каналы (2)") < md.index("# Чаты (1)")
    assert "ChannelA" in md and "ChannelB" in md and "ChatA" in md


def test_sort_sources_orders_by_score_descending():
    low = _make_source("channel", "Low", 1)
    high = _make_source("channel", "High", 5)
    result = sort_sources([low, high])
    assert result[0].title == "High"
