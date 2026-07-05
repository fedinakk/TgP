"""Per-chat analysis: activity check, message relevance filtering, report building."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient
from telethon.errors import ChannelPrivateError, FloodWaitError
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.types import Channel, Chat

from .config import Config
from .filters import is_relevant_job_post
from .keywords import ALL_CATEGORIES_BY_KEY
from .models import SamplePost, SourceReport

logger = logging.getLogger(__name__)

MAX_SAMPLE_POSTS = 5
MAX_POST_CHARS = 400


async def analyze_chat(
    client: TelegramClient,
    entity: Channel | Chat,
    config: Config,
) -> SourceReport | None:
    """Return a SourceReport if the chat is active and has relevant job posts,
    otherwise None (dropped as inactive/irrelevant).
    """
    try:
        about, participants_count = await _fetch_about(client, entity)
    except (ChannelPrivateError, ValueError):
        return None
    except FloodWaitError as exc:
        logger.warning("FloodWait %ss fetching about info, sleeping", exc.seconds)
        await asyncio.sleep(exc.seconds + 1)
        about, participants_count = await _fetch_about(client, entity)

    try:
        messages = await client.get_messages(entity, limit=config.messages_per_chat)
    except FloodWaitError as exc:
        logger.warning("FloodWait %ss fetching messages, sleeping", exc.seconds)
        await asyncio.sleep(exc.seconds + 1)
        messages = await client.get_messages(entity, limit=config.messages_per_chat)
    except (ChannelPrivateError, ValueError):
        return None

    if not messages:
        return None

    last_activity = messages[0].date
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.active_window_hours)
    if last_activity is None or last_activity < cutoff:
        return None  # not active in the required window

    username = getattr(entity, "username", None)
    link = f"https://t.me/{username}" if username else f"t.me/c/{entity.id}"

    sample_posts: list[SamplePost] = []
    categories_hit: set[str] = set()
    for message in messages:
        text = message.message or ""
        relevant, categories = is_relevant_job_post(text)
        if not relevant:
            continue
        categories_hit.update(categories)
        post_link = f"{link}/{message.id}" if username else None
        sample_posts.append(
            SamplePost(
                date=message.date,
                text=text[:MAX_POST_CHARS],
                link=post_link,
                categories=categories,
            )
        )
        if len(sample_posts) >= MAX_SAMPLE_POSTS:
            break

    if not sample_posts:
        return None  # active, but nothing relevant found -> drop

    return SourceReport(
        chat_id=entity.id,
        title=getattr(entity, "title", "") or "",
        username=username,
        link=link,
        kind="channel" if isinstance(entity, Channel) else "chat",
        about=about,
        participants_count=participants_count,
        last_activity=last_activity,
        matched_categories=sorted(
            {ALL_CATEGORIES_BY_KEY[k].label for k in categories_hit if k in ALL_CATEGORIES_BY_KEY}
        ),
        sample_posts=sample_posts,
    )


async def _fetch_about(client: TelegramClient, entity: Channel | Chat) -> tuple[str, int | None]:
    if isinstance(entity, Channel):
        full = await client(GetFullChannelRequest(entity))
        about = full.full_chat.about or ""
        count = full.full_chat.participants_count
    elif isinstance(entity, Chat):
        full = await client(GetFullChatRequest(entity.id))
        about = getattr(full.full_chat, "about", "") or ""
        count = getattr(full.full_chat, "participants_count", None)
    else:
        raise ValueError(f"Unsupported entity type: {type(entity)}")
    return about, count
