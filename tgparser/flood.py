"""Shared handling for Telegram's FloodWaitError.

Telethon auto-retries small flood waits internally (below its own
flood_sleep_threshold, ~60s by default) -- by the time *our* code sees a
FloodWaitError, Telegram is already asking for a real wait. Blindly sleeping
whatever it asks for is fine for a few seconds or minutes, but Telegram can
(and, under sustained load, will) hand back waits of tens of thousands of
seconds -- literally hours. Sleeping that out would silently hang the whole
run instead of finishing with whatever was already found.
"""
from __future__ import annotations

import asyncio
import logging

from telethon.errors import FloodWaitError

logger = logging.getLogger(__name__)


def _format_duration(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"~{hours}h{minutes}m"
    return f"~{minutes}m"


async def wait_out_flood(exc: FloodWaitError, max_wait_seconds: int, context: str) -> bool:
    """Sleep out a FloodWaitError if it's within `max_wait_seconds`; otherwise
    give up on this one request instead of blocking the run for hours.

    Returns True if it slept (caller should retry), False if the caller
    should skip/abort this request instead.
    """
    if exc.seconds > max_wait_seconds:
        logger.warning(
            "FloodWait %s on %s -- that's above the %ss cap, skipping this one "
            "instead of blocking the whole run for it",
            _format_duration(exc.seconds),
            context,
            max_wait_seconds,
        )
        return False
    logger.warning("FloodWait %ss on %s, sleeping", exc.seconds, context)
    await asyncio.sleep(exc.seconds + 1)
    return True
