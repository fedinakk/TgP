"""CLI: discover, analyze and report on Telegram sources for content/SMM job orders.

Usage:
    python -m tgparser.main search [--output-dir out]
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import logging
from pathlib import Path

from telethon import TelegramClient

from .analyzer import JoinBudget, analyze_chat
from .config import Config, load_config
from .links import extract_usernames
from .models import PendingSource, SourceReport
from .report import write_reports
from .search import discover_chats, resolve_seeds, resolve_usernames
from .tg_client import build_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _split_counts(sources: dict[int, SourceReport]) -> tuple[int, int]:
    channels = sum(1 for s in sources.values() if s.kind == "channel")
    chats = sum(1 for s in sources.values() if s.kind == "chat")
    return channels, chats


async def _notify_found(client: TelegramClient, report: SourceReport) -> None:
    text = (
        f"Найден источник: {report.title}\n"
        f"{report.link}\n"
        f"Тематика: {', '.join(report.matched_categories) or '-'}"
    )
    try:
        await client.send_message("me", text)
    except Exception:
        logger.exception("Failed to notify Saved Messages about %s", report.link)


async def _notify_pending(client: TelegramClient, pending: PendingSource) -> None:
    text = (
        f"Нужно подать заявку на вступление, дальше сами:\n"
        f"{pending.title}\n{pending.link}"
    )
    try:
        await client.send_message("me", text)
    except Exception:
        logger.exception("Failed to notify Saved Messages about pending %s", pending.link)


async def _analyze_batch(
    client: TelegramClient,
    config: Config,
    candidates: dict[int, object],
    confirmed: dict[int, SourceReport],
    pending: dict[int, PendingSource],
    visited: set[int],
    join_budget: JoinBudget,
    suppress_notify_ids: frozenset[int] = frozenset(),
) -> None:
    """Analyze a batch of candidate entities concurrently (bounded by
    config.concurrency). Confirmed sources are added to `confirmed` and,
    if enabled, immediately pushed to Saved Messages so they're visible
    while the run is still going -- unless their id is in
    `suppress_notify_ids` (already-known sources being re-verified, not
    new finds). Candidates that need an approved join request go to
    `pending` instead, with their own notification.
    """
    semaphore = asyncio.Semaphore(config.concurrency)

    async def _worker(entity) -> None:
        async with semaphore:
            title = getattr(entity, "title", entity.id)
            try:
                result = await analyze_chat(client, entity, config, join_budget)
            except Exception:
                logger.exception("Failed to analyze %s, skipping", title)
                return

            is_new = entity.id not in suppress_notify_ids

            if isinstance(result, PendingSource):
                pending[entity.id] = result
                logger.info("[pending] %s -- %s (needs approved join request)", result.title, result.link)
                if config.notify_saved_messages and is_new:
                    await _notify_pending(client, result)
            elif result:
                confirmed[entity.id] = result
                logger.info(
                    "[%s]%s %s -- %s (%s)",
                    result.kind,
                    "" if is_new else " (known)",
                    result.title,
                    result.link,
                    ", ".join(result.matched_categories),
                )
                if config.notify_saved_messages and is_new:
                    await _notify_found(client, result)
            await asyncio.sleep(config.request_delay_seconds)

    to_run = [entity for cid, entity in candidates.items() if cid not in visited]
    visited.update(candidates.keys())
    if not to_run:
        return
    logger.info("Analyzing %d candidate chats...", len(to_run))
    await asyncio.gather(*(_worker(entity) for entity in to_run))


def _load_previous_report(path: Path) -> tuple[list[dict], list[dict]]:
    """Supports both the current {"sources": [...], "pending": [...]}
    schema and the older flat-list schema from earlier versions.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data.get("sources", []), data.get("pending", [])
    return data, []  # old format: a flat list of sources, no pending


async def _recheck_previous_run(
    client: TelegramClient,
    config: Config,
    confirmed: dict[int, SourceReport],
    pending: dict[int, PendingSource],
    visited: set[int],
    join_budget: JoinBudget,
) -> None:
    """If a previous run left a report.json here, re-verify those sources
    (still active? still relevant? join request approved by now?) and keep
    the ones that pass, so results accumulate across runs instead of
    resetting to zero every time. These are already-known sources, so they
    must not trigger a fresh Saved Messages notification just for being
    re-confirmed.
    """
    previous_report = config.output_dir / "report.json"
    if not previous_report.exists():
        return
    try:
        source_items, pending_items = _load_previous_report(previous_report)
    except (json.JSONDecodeError, OSError, ValueError):
        logger.warning("Could not read %s, skipping re-check", previous_report)
        return

    known_ids = frozenset(
        item["chat_id"] for item in (*source_items, *pending_items) if "chat_id" in item
    )
    usernames = {item["username"] for item in source_items if item.get("username")}
    for item in pending_items:
        usernames |= extract_usernames(item.get("link", ""))
    if not usernames:
        return

    logger.info(
        "Re-checking %d sources found in a previous run (%s)",
        len(usernames),
        previous_report,
    )
    prev_candidates = await resolve_usernames(client, usernames)
    await _analyze_batch(
        client,
        config,
        prev_candidates,
        confirmed,
        pending,
        visited,
        join_budget,
        suppress_notify_ids=known_ids,
    )


async def _pipeline(
    client: TelegramClient,
    config: Config,
    confirmed: dict[int, SourceReport],
    pending: dict[int, PendingSource],
    visited: set[int],
    join_budget: JoinBudget,
) -> None:
    await _recheck_previous_run(client, config, confirmed, pending, visited, join_budget)

    seeds = await resolve_seeds(client, config.seeds_file)
    if seeds:
        logger.info("Loaded %d seed candidates from %s", len(seeds), config.seeds_file)
        await _analyze_batch(client, config, seeds, confirmed, pending, visited, join_budget)

    discovered = await discover_chats(client, config)
    candidates = {cid: entity for cid, (entity, _cats) in discovered.items()}
    await _analyze_batch(client, config, candidates, confirmed, pending, visited, join_budget)

    for round_no in range(1, config.snowball_max_rounds + 1):
        channels_count, chats_count = _split_counts(confirmed)
        if channels_count >= config.target_channels and chats_count >= config.target_chats:
            logger.info(
                "Targets reached (%d channels, %d chats), stopping.",
                channels_count,
                chats_count,
            )
            break

        # linked_usernames comes from scanning every fetched message of
        # every confirmed source, not just the handful shown as samples --
        # that's what lets this dig into channels/chats no search query
        # would ever surface directly.
        usernames: set[str] = set()
        for report in confirmed.values():
            usernames.update(report.linked_usernames)

        if not usernames:
            logger.info("No linked usernames to follow, stopping snowball.")
            break

        logger.info(
            "Snowball round %d: resolving %d linked usernames", round_no, len(usernames)
        )
        new_candidates = await resolve_usernames(client, usernames)
        new_candidates = {cid: e for cid, e in new_candidates.items() if cid not in visited}
        if not new_candidates:
            logger.info("Snowball round %d found nothing new, stopping.", round_no)
            break
        await _analyze_batch(client, config, new_candidates, confirmed, pending, visited, join_budget)


async def run_search(output_dir: str | None) -> None:
    config = load_config()
    if output_dir:
        config = dataclasses.replace(config, output_dir=Path(output_dir))

    client = await build_client(config)
    confirmed: dict[int, SourceReport] = {}
    pending: dict[int, PendingSource] = {}
    visited: set[int] = set()
    join_budget = JoinBudget(config.max_joins_per_run)

    try:
        pipeline = _pipeline(client, config, confirmed, pending, visited, join_budget)
        if config.max_runtime_minutes:
            try:
                await asyncio.wait_for(pipeline, timeout=config.max_runtime_minutes * 60)
            except asyncio.TimeoutError:
                logger.info(
                    "MAX_RUNTIME_MINUTES (%d) reached, stopping and saving what was found so far.",
                    config.max_runtime_minutes,
                )
        else:
            await pipeline

        channels_count, chats_count = _split_counts(confirmed)
        logger.info(
            "Finished: %d channels, %d chats confirmed, %d pending approval "
            "(targets: %d channels / %d chats).",
            channels_count,
            chats_count,
            len(pending),
            config.target_channels,
            config.target_chats,
        )

        md_path, json_path = write_reports(
            list(confirmed.values()), list(pending.values()), config.output_dir
        )
        logger.info("Markdown report: %s", md_path)
        logger.info("JSON report: %s", json_path)
    finally:
        await client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="Discover and analyze sources")
    search_parser.add_argument(
        "--output-dir", default=None, help="Where to write report.md/report.json"
    )

    args = parser.parse_args()

    if args.command == "search":
        asyncio.run(run_search(args.output_dir))


if __name__ == "__main__":
    main()
