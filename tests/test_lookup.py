from pathlib import Path

from telethon.tl.types import Channel

from tgparser.lookup import match_link, parse_queries_file, render_markdown


def _make_channel(**kwargs):
    defaults = dict(id=1, title="Test Channel", photo=None, date=None)
    defaults.update(kwargs)
    return Channel(**defaults)


class _FakeMessage:
    def __init__(self, id):
        self.id = id


def test_parse_queries_file_skips_blank_lines_and_comments(tmp_path):
    path = tmp_path / "queries.txt"
    path.write_text(
        "\n".join(
            [
                "# a comment",
                "",
                "уникальная фраза из вакансии",
                "  другая фраза с пробелами  ",
                "# ещё комментарий",
            ]
        ),
        encoding="utf-8",
    )
    queries = parse_queries_file(path)
    assert queries == ["уникальная фраза из вакансии", "другая фраза с пробелами"]


def test_parse_queries_file_missing_file_returns_empty(tmp_path):
    assert parse_queries_file(tmp_path / "nope.txt") == []


def test_match_link_uses_username_when_present():
    chat = _make_channel(username="somechannel")
    message = _FakeMessage(id=42)
    assert match_link(chat, message) == "https://t.me/somechannel/42"


def test_match_link_falls_back_to_internal_id():
    chat = _make_channel(username=None, id=777)
    message = _FakeMessage(id=42)
    assert match_link(chat, message) == "t.me/c/777/42"


def test_render_markdown_lists_matches_and_no_match_case():
    chat = _make_channel(username="somechannel", title="Some Channel")
    message = _FakeMessage(id=42)
    results = [
        ("нашлась фраза", [(chat, message)]),
        ("не нашлась фраза", []),
    ]
    md = render_markdown(results)
    assert "## нашлась фраза" in md
    assert "[Some Channel](https://t.me/somechannel/42)" in md
    assert "## не нашлась фраза" in md
    assert "Совпадений не найдено" in md
