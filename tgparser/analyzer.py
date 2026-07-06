"""Per-chat analysis: activity check, message relevance filtering, report building."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient
from telethon.errors import (
    ChannelPrivateError,
    ChatAdminRequiredError,
    FloodWaitError,
    UserAlreadyParticipantError,
    UserNotParticipantError,
)
from telethon.tl.functions.channels import GetFullChannelRequest, JoinChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.types import Channel, Chat

from .config import Config
from .filters import is_relevant_job_post
from .keywords import ALL_CATEGORIES_BY_KEY
from .links import extract_usernames
from .models import PendingSource, SamplePost, SourceReport

logger = logging.getLogger(__name__)

MAX_SAMPLE_POSTS = 5
MAX_POST_CHARS = 400

# Raised by Telethon when we can read a chat's info but not its messages
# because we haven't joined it -- fixable by joining (unlike a fully
# private/invite-only chat, which we'd never have gotten an entity for).
NEEDS_JOIN_ERRORS = (ChannelPrivateError, ChatAdminRequiredError, UserNotParticipantError)


class JoinBudget:
    """Caps how many chats we auto-join in one run (account-safety guard)."""

    def __init__(self, limit: int):
        self.remaining = limit

    def try_consume(self) -> bool:
        if self.remaining <= 0:
            return False
        self.remaining -= 1
        return True


def _classify_kind(entity: Channel | Chat) -> str:
    """Modern group chats ("supergroups") are internally `Channel` objects
    with megagroup=True -- only `broadcast` channels and legacy small
    `Chat` groups are unambiguous from type alone.
    """
    if isinstance(entity, Chat) or getattr(entity, "megagroup", False):
        return "chat"
    return "channel"


def _build_link(entity: Channel | Chat) -> str:
    username = getattr(entity, "username", None)
    return f"https://t.me/{username}" if username else f"t.me/c/{entity.id}"


async def analyze_chat(
    client: TelegramClient,
    entity: Channel | Chat,
    config: Config,
    join_budget: JoinBudget,
) -> SourceReport | PendingSource | None:
    """Return a SourceReport if the chat is active and has relevant job posts,
    a PendingSource if it needs an approved join request to inspect at all,
    or None (dropped as inaccessible/inactive/irrelevant).
    """
    kind = _classify_kind(entity)
    link = _build_link(entity)

    if getattr(entity, "join_request", False):
        # We'd need the owner to approve us -- can't verify anything
        # ourselves, so just hand the link over.
        return PendingSource(
            chat_id=entity.id, title=getattr(entity, "title", "") or "", link=link, kind=kind
        )

    try:
        about, participants_count = await _fetch_about(client, entity)
    except (ChannelPrivateError, ValueError):
        return None
    except FloodWaitError as exc:
        logger.warning("FloodWait %ss fetching about info, sleeping", exc.seconds)
        await asyncio.sleep(exc.seconds + 1)
        try:
            about, participants_count = await _fetch_about(client, entity)
        except (ChannelPrivateError, ValueError):
            return None

    messages = await _get_messages(client, entity, config, join_budget)
    if not messages:
        return None

    last_activity = messages[0].date
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.active_window_hours)
    if last_activity is None or last_activity < cutoff:
        return None  # not active in the required window

    username = getattr(entity, "username", None)

    sample_posts: list[SamplePost] = []
    categories_hit: set[str] = set()
    linked_usernames: set[str] = set()
    for message in messages:
        text = message.message or ""
        linked_usernames |= extract_usernames(text)
        relevant, categories = is_relevant_job_post(text)
        if not relevant:
            continue
        categories_hit.update(categories)
        if len(sample_posts) < MAX_SAMPLE_POSTS:
            post_link = f"{link}/{message.id}" if username else None
            sample_posts.append(
                SamplePost(
                    date=message.date,
                    text=text[:MAX_POST_CHARS],
                    link=post_link,
                    categories=categories,
                )
            )

    if not sample_posts:
        return None  # active, but nothing relevant found -> drop

    return SourceReport(
        chat_id=entity.id,
        title=getattr(entity, "title", "") or "",
        username=username,
        link=link,
        kind=kind,
        about=about,
        participants_count=participants_count,
        last_activity=last_activity,
        matched_categories=sorted(
            {ALL_CATEGORIES_BY_KEY[k].label for k in categories_hit if k in ALL_CATEGORIES_BY_KEY}
        ),
        sample_posts=sample_posts,
        linked_usernames=sorted(linked_usernames - ({username} if username else set())),
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


async def _get_messages(
    client: TelegramClient,
    entity: Channel | Chat,
    config: Config,
    join_budget: JoinBudget,
) -> list | None:
    """Fetch recent messages, joining the chat first if that's the only
    reason we can't read them (and auto-join is enabled / budget allows).
    """
    try:
        return await client.get_messages(entity, limit=config.messages_per_chat)
    except FloodWaitError as exc:
        logger.warning("FloodWait %ss fetching messages, sleeping", exc.seconds)
        await asyncio.sleep(exc.seconds + 1)
        try:
            return await client.get_messages(entity, limit=config.messages_per_chat)
        except NEEDS_JOIN_ERRORS:
            pass
        except ValueError:
            return None
    except NEEDS_JOIN_ERRORS:
        pass
    except ValueError:
        return None

    if not config.auto_join_chats or not join_budget.try_consume():
        return None

    title = getattr(entity, "title", entity.id)
    try:
        await client(JoinChannelRequest(entity))
        logger.info("Joined %s to read its message history", title)
    except UserAlreadyParticipantError:
        pass
    except FloodWaitError as exc:
        logger.warning("FloodWait %ss joining %s, sleeping", exc.seconds, title)
        await asyncio.sleep(exc.seconds + 1)
        try:
            await client(JoinChannelRequest(entity))
        except UserAlreadyParticipantError:
            pass
        except Exception:
            return None
    except Exception:
        logger.info("Could not join %s, skipping", title)
        return None

    await asyncio.sleep(config.join_delay_seconds)
    try:
        return await client.get_messages(entity, limit=config.messages_per_chat)
    except Exception:
        return None
