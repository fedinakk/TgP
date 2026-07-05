"""Discovers candidate channels/chats via Telegram's global search."""
from __future__ import annotations

import asyncio
import logging

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import Channel, Chat

from .config import Config
from .keywords import CATEGORIES

logger = logging.getLogger(__name__)


async def discover_chats(
    client: TelegramClient, config: Config
) -> dict[int, tuple[Channel | Chat, list[str]]]:
    """Run every category's search queries and collect unique candidate chats.

    Returns a mapping of chat_id -> (entity, [category_key, ...]) recording
    which categories' queries surfaced that chat (a chat can match several).
    """
    found: dict[int, tuple[Channel | Chat, list[str]]] = {}

    for category in CATEGORIES:
        for query in category.search_queries:
            entities = await _search_once(client, query, config.chats_per_keyword)
            for entity in entities:
                existing = found.get(entity.id)
                if existing:
                    _, cats = existing
                    if category.key not in cats:
                        cats.append(category.key)
                else:
                    found[entity.id] = (entity, [category.key])
            await asyncio.sleep(config.request_delay_seconds)

    logger.info("Discovered %d unique candidate chats/channels", len(found))
    return found


async def _search_once(client: TelegramClient, query: str, limit: int):
    try:
        result = await client(SearchRequest(q=query, limit=limit))
    except FloodWaitError as exc:
        logger.warning("FloodWait %ss while searching %r, sleeping", exc.seconds, query)
        await asyncio.sleep(exc.seconds + 1)
        result = await client(SearchRequest(q=query, limit=limit))

    return [
        c
        for c in result.chats
        if isinstance(c, (Channel, Chat)) and not getattr(c, "deactivated", False)
    ]
