"""Discovers candidate channels/chats via Telegram's global full-text message search.

Uses messages.searchGlobal — the same API behind Telegram's in-app search —
which matches actual message text across public chats, not just chat titles.
That is what makes it possible to find real order/job posts, as opposed to
contacts.search (used previously) which only matches chat names.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import AsyncIterator

from telethon import TelegramClient
from telethon.errors import FloodWaitError, UsernameInvalidError, UsernameNotOccupiedError
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.types import Channel, Chat, InputMessagesFilterEmpty, InputPeerEmpty
from telethon.tl.types.messages import MessagesSlice

from .config import Config
from .keywords import CATEGORIES
from .links import parse_seed_line

logger = logging.getLogger(__name__)

PAGE_SIZE = 50


async def _search_query(
    client: TelegramClient,
    query: str,
    *,
    broadcasts_only: bool,
    groups_only: bool,
    max_pages: int,
    delay: float,
) -> AsyncIterator[Channel | Chat]:
    """Paginate messages.searchGlobal for one query, yielding unique chat entities."""
    seen_chat_ids: set[int] = set()
    offset_rate = 0
    offset_peer = InputPeerEmpty()
    offset_id = 0

    for _ in range(max_pages):
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
                    broadcasts_only=broadcasts_only or None,
                    groups_only=groups_only or None,
                )
            )
        except FloodWaitError as exc:
            logger.warning("FloodWait %ss on query %r, sleeping", exc.seconds, query)
            await asyncio.sleep(exc.seconds + 1)
            continue

        if not result.messages:
            break

        chats_by_id = {c.id: c for c in result.chats if isinstance(c, (Channel, Chat))}
        for message in result.messages:
            peer = message.peer_id
            chat_id = getattr(peer, "channel_id", None) or getattr(peer, "chat_id", None)
            if chat_id and chat_id in chats_by_id and chat_id not in seen_chat_ids:
                seen_chat_ids.add(chat_id)
                yield chats_by_id[chat_id]

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

        await asyncio.sleep(delay)


async def discover_chats(
    client: TelegramClient, config: Config
) -> dict[int, tuple[Channel | Chat, list[str]]]:
    """Search across every category's queries, separately for channels and
    groups, and collect unique candidate chats plus which categories'
    queries surfaced them (a chat can match several categories).
    """
    found: dict[int, tuple[Channel | Chat, list[str]]] = {}

    for category in CATEGORIES:
        for query in category.search_queries:
            for broadcasts_only, groups_only in ((True, False), (False, True)):
                async for entity in _search_query(
                    client,
                    query,
                    broadcasts_only=broadcasts_only,
                    groups_only=groups_only,
                    max_pages=config.max_pages_per_query,
                    delay=config.request_delay_seconds,
                ):
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


async def resolve_usernames(
    client: TelegramClient, usernames: set[str]
) -> dict[int, Channel | Chat]:
    """Resolve bare usernames (no @, no t.me/) to chat/channel entities,
    silently skipping ones that don't exist or aren't public chats.
    """
    resolved: dict[int, Channel | Chat] = {}
    for username in usernames:
        try:
            entity = await client.get_entity(username)
        except FloodWaitError as exc:
            logger.warning("FloodWait %ss resolving @%s, sleeping", exc.seconds, username)
            await asyncio.sleep(exc.seconds + 1)
            try:
                entity = await client.get_entity(username)
            except (UsernameInvalidError, UsernameNotOccupiedError, ValueError):
                continue
        except (UsernameInvalidError, UsernameNotOccupiedError, ValueError):
            continue
        if isinstance(entity, (Channel, Chat)):
            resolved[entity.id] = entity
    return resolved


async def resolve_seeds(
    client: TelegramClient, seeds_file: Path | None
) -> dict[int, Channel | Chat]:
    """Load user-curated candidate usernames from seeds.txt (e.g. copied
    out of TGStat/Telega.in catalog pages) and resolve them.
    """
    if not seeds_file or not seeds_file.exists():
        return {}
    usernames = {
        u
        for line in seeds_file.read_text(encoding="utf-8").splitlines()
        if (u := parse_seed_line(line))
    }
    if not usernames:
        return {}
    logger.info("Resolving %d seed usernames from %s", len(usernames), seeds_file)
    return await resolve_usernames(client, usernames)
