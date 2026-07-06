"""Discovers candidate channels/chats via Telegram's global full-text message search.

Uses messages.searchGlobal — the same API behind Telegram's in-app search —
which matches actual message text across public chats, not just chat titles.
That is what makes it possible to find real order/job posts, as opposed to
contacts.search (title/name matching only).

In practice messages.searchGlobal for a given account plateaus after a
modest number of unique chats no matter how many query words you throw at
it -- this looks like a platform-side depth limit (Telegram's own global
search is known to return a shallower result set for regular accounts than
for Premium ones), not something fixable by query wording alone. Two things
help push past that ceiling without trying to bypass any actual limit:
  - contacts.search as a second, differently-indexed source (matches chat
    titles/usernames rather than message text).
  - re-running the same query across several non-overlapping time windows,
    since a plateaued single pagination chain can still surface different
    results when explicitly pointed at an older time range via min/max_date.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import AsyncIterator

from telethon import TelegramClient
from telethon.errors import FloodWaitError, UsernameInvalidError, UsernameNotOccupiedError
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.types import Channel, Chat, InputMessagesFilterEmpty, InputPeerEmpty
from telethon.tl.types.messages import MessagesSlice

from .config import Config
from .flood import wait_out_flood
from .keywords import CATEGORIES
from .links import parse_seed_line

logger = logging.getLogger(__name__)

PAGE_SIZE = 50

# Non-overlapping lookback windows for full-text search: each one starts a
# fresh pagination chain, so a chain that plateaus for "all time" can still
# turn up unseen chats once pointed at just e.g. the 30-180 day range.
_WINDOW_EDGES_DAYS = (0, 7, 30, 180, 730, None)


def _search_windows() -> list[tuple[datetime | None, datetime | None]]:
    now = datetime.now(timezone.utc)
    edges = [now - timedelta(days=d) if d is not None else None for d in _WINDOW_EDGES_DAYS]
    return list(zip(edges[1:], edges[:-1]))  # (min_date, max_date) per window, newest first


async def _search_query(
    client: TelegramClient,
    query: str,
    *,
    broadcasts_only: bool,
    groups_only: bool,
    max_pages: int,
    delay: float,
    max_flood_wait_seconds: int,
    min_date: datetime | None = None,
    max_date: datetime | None = None,
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
                    min_date=min_date,
                    max_date=max_date,
                    offset_rate=offset_rate,
                    offset_peer=offset_peer,
                    offset_id=offset_id,
                    limit=PAGE_SIZE,
                    broadcasts_only=broadcasts_only or None,
                    groups_only=groups_only or None,
                )
            )
        except FloodWaitError as exc:
            if not await wait_out_flood(exc, max_flood_wait_seconds, f"query {query!r}"):
                return
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


async def _search_contacts_once(
    client: TelegramClient, query: str, limit: int, max_flood_wait_seconds: int
) -> list[Channel | Chat]:
    """contacts.search matches chat titles/usernames -- a differently-indexed
    complement to the full-text message search above.
    """
    try:
        result = await client(SearchRequest(q=query, limit=limit))
    except FloodWaitError as exc:
        if not await wait_out_flood(exc, max_flood_wait_seconds, f"contacts.search {query!r}"):
            return []
        try:
            result = await client(SearchRequest(q=query, limit=limit))
        except FloodWaitError:
            return []
    return [c for c in result.chats if isinstance(c, (Channel, Chat)) and not getattr(c, "deactivated", False)]


async def discover_chats(
    client: TelegramClient, config: Config
) -> dict[int, tuple[Channel | Chat, list[str]]]:
    """Search across every category's queries, separately for channels and
    groups and across several time windows (see module docstring for why),
    plus a contacts.search pass, collecting unique candidate chats and which
    categories' queries surfaced them (a chat can match several).
    """
    found: dict[int, tuple[Channel | Chat, list[str]]] = {}
    windows = _search_windows()

    total_queries = sum(len(c.search_queries) for c in CATEGORIES)
    logger.info(
        "Searching Telegram: %d queries x %d time windows x 2 (channels/groups) "
        "+ contacts.search, across %d categories (runs silently for a while "
        "between log lines, that's expected)",
        total_queries,
        len(windows),
        len(CATEGORIES),
    )

    def _add(entity: Channel | Chat, category_key: str) -> None:
        existing = found.get(entity.id)
        if existing:
            _, cats = existing
            if category_key not in cats:
                cats.append(category_key)
        else:
            found[entity.id] = (entity, [category_key])

    query_no = 0
    for category in CATEGORIES:
        for query in category.search_queries:
            query_no += 1

            for entity in await _search_contacts_once(
                client, query, PAGE_SIZE, config.max_flood_wait_seconds
            ):
                _add(entity, category.key)
            await asyncio.sleep(config.request_delay_seconds)

            for min_date, max_date in windows:
                for broadcasts_only, groups_only in ((True, False), (False, True)):
                    async for entity in _search_query(
                        client,
                        query,
                        broadcasts_only=broadcasts_only,
                        groups_only=groups_only,
                        max_pages=config.max_pages_per_query,
                        delay=config.request_delay_seconds,
                        max_flood_wait_seconds=config.max_flood_wait_seconds,
                        min_date=min_date,
                        max_date=max_date,
                    ):
                        _add(entity, category.key)
                await asyncio.sleep(config.request_delay_seconds)

            logger.info(
                "[%d/%d] %r (%s) -> %d candidates so far",
                query_no,
                total_queries,
                query,
                category.label,
                len(found),
            )

    logger.info("Discovered %d unique candidate chats/channels", len(found))
    return found


async def resolve_usernames(
    client: TelegramClient, usernames: set[str], config: Config
) -> dict[int, Channel | Chat]:
    """Resolve bare usernames (no @, no t.me/) to chat/channel entities,
    silently skipping ones that don't exist or aren't public chats.

    Paced with `resolve_delay_seconds` between lookups -- hammering
    ResolveUsernameRequest back-to-back (no delay at all) is what triggers
    Telegram's flood limits on it in the first place, and those can escalate
    to waits of literal hours. If one still comes back too large to sleep
    out, the rest of this batch is abandoned rather than repeating the same
    mistake on every remaining username.
    """
    resolved: dict[int, Channel | Chat] = {}
    for username in usernames:
        try:
            entity = await client.get_entity(username)
        except FloodWaitError as exc:
            if not await wait_out_flood(
                exc, config.max_flood_wait_seconds, f"resolving @{username}"
            ):
                logger.warning(
                    "Giving up on the remaining %d usernames in this batch -- "
                    "Telegram is flood-limiting username lookups right now",
                    len(usernames) - len(resolved),
                )
                break
            try:
                entity = await client.get_entity(username)
            except (UsernameInvalidError, UsernameNotOccupiedError, ValueError):
                continue
        except (UsernameInvalidError, UsernameNotOccupiedError, ValueError):
            continue
        if isinstance(entity, (Channel, Chat)):
            resolved[entity.id] = entity
        await asyncio.sleep(config.resolve_delay_seconds)
    return resolved


async def resolve_seeds(
    client: TelegramClient, seeds_file: Path | None, config: Config
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
    return await resolve_usernames(client, usernames, config)
