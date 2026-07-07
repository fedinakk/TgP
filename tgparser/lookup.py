"""Reverse-lookup: given a snippet of a post's text, find which public
channel/chat it was posted in, by searching Telegram's global full-text
index (messages.searchGlobal) for that exact snippet.

The same job post is very often reposted verbatim across several
"vacancy board" channels at once -- so a snippet can legitimately turn up
more than one match. There's no way to tell which one is the "original"
from text alone; all of them are reported.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.types import Channel, Chat, InputMessagesFilterEmpty, InputPeerEmpty, Message
from telethon.tl.types.messages import MessagesSlice

from .config import Config
from .flood import wait_out_flood

logger = logging.getLogger(__name__)

PAGE_SIZE = 20
DEFAULT_QUERIES_FILE = "queries.txt"


def parse_queries_file(path: Path) -> list[str]:
    """One search snippet per line; blank lines and '#' comments are skipped."""
    if not path.exists():
        return []
    queries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        queries.append(line)
    return queries


async def find_source(
    client: TelegramClient, query: str, config: Config, max_results: int = 10
) -> list[tuple[Channel | Chat, Message]]:
    """Search Telegram's global full-text index for this exact snippet,
    returning (chat, message) pairs for every match found.
    """
    matches: list[tuple[Channel | Chat, Message]] = []
    offset_rate = 0
    offset_peer = InputPeerEmpty()
    offset_id = 0
    raw_seen = 0
    unmatched = 0

    for _ in range(config.max_pages_per_query):
        try:
            result = await client(
                SearchGlobalRequest(
                    q=query,
                    filter=InputMessagesFilterEmpty(),
                    min_date=None,
                    max_date=None,
                    offset_rate=offset_rate,
                    offset_peer=offset_peer,
                    offset_id=offset_id,
                    limit=PAGE_SIZE,
                    broadcasts_only=None,
                    groups_only=None,
                )
            )
        except FloodWaitError as exc:
            if not await wait_out_flood(exc, config.max_flood_wait_seconds, f"lookup {query!r}"):
                break
            continue

        if not result.messages:
            break

        raw_seen += len(result.messages)
        chats_by_id = {c.id: c for c in result.chats if isinstance(c, (Channel, Chat))}
        for message in result.messages:
            peer = message.peer_id
            chat_id = getattr(peer, "channel_id", None) or getattr(peer, "chat_id", None)
            chat = chats_by_id.get(chat_id)
            if chat is not None:
                matches.append((chat, message))
                if len(matches) >= max_results:
                    logger.info(
                        "  (Telegram returned %d raw hits for this snippet, %d matched to a chat)",
                        raw_seen,
                        len(matches),
                    )
                    return matches
            else:
                unmatched += 1

        next_rate = getattr(result, "next_rate", None)
        if not next_rate or not isinstance(result, MessagesSlice):
            break

        offset_rate = next_rate
        last_message = result.messages[-1]
        offset_id = last_message.id
        try:
            offset_peer = await client.get_input_entity(last_message.peer_id)
        except (ValueError, TypeError):
            break

        await asyncio.sleep(config.request_delay_seconds)

    if raw_seen:
        logger.info(
            "  (Telegram returned %d raw hits for this snippet, %d matched to a chat, "
            "%d couldn't be linked to one)",
            raw_seen,
            len(matches),
            unmatched,
        )
    return matches


def match_link(chat: Channel | Chat, message: Message) -> str:
    username = getattr(chat, "username", None)
    if username:
        return f"https://t.me/{username}/{message.id}"
    return f"t.me/c/{chat.id}/{message.id}"


def render_markdown(results: list[tuple[str, list[tuple[Channel | Chat, Message]]]]) -> str:
    lines = ["# Поиск источников по фрагментам текста", ""]
    for query, matches in results:
        lines.append(f"## {query}")
        lines.append("")
        if not matches:
            lines.append("_Совпадений не найдено._")
        else:
            for chat, message in matches:
                title = getattr(chat, "title", "") or str(chat.id)
                lines.append(f"- [{title}]({match_link(chat, message)})")
        lines.append("")
    return "\n".join(lines)
