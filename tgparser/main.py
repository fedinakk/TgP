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

from .analyzer import analyze_chat
from .config import Config, load_config
from .links import extract_usernames
from .models import SourceReport
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


async def _analyze_batch(
    client: TelegramClient,
    config: Config,
    candidates: dict[int, object],
    confirmed: dict[int, SourceReport],
    visited: set[int],
    suppress_notify_ids: frozenset[int] = frozenset(),
) -> None:
    """Analyze a batch of candidate entities concurrently (bounded by
    config.concurrency). Confirmed sources are added to `confirmed` and,
    if enabled, immediately pushed to Saved Messages so they're visible
    while the run is still going -- unless their id is in
    `suppress_notify_ids` (already-known sources being re-verified, not
    new finds).
    """
    semaphore = asyncio.Semaphore(config.concurrency)

    async def _worker(entity) -> None:
        async with semaphore:
            title = getattr(entity, "title", entity.id)
            try:
                report = await analyze_chat(client, entity, config)
            except Exception:
                logger.exception("Failed to analyze %s, skipping", title)
                return
            if report:
                confirmed[entity.id] = report
                is_new = entity.id not in suppress_notify_ids
                logger.info(
                    "[%s]%s %s -- %s (%s)",
                    report.kind,
                    "" if is_new else " (known)",
                    report.title,
                    report.link,
                    ", ".join(report.matched_categories),
                )
                if config.notify_saved_messages and is_new:
                    await _notify_found(client, report)
            await asyncio.sleep(config.request_delay_seconds)

    to_run = [entity for cid, entity in candidates.items() if cid not in visited]
    visited.update(candidates.keys())
    if not to_run:
        return
    logger.info("Analyzing %d candidate chats...", len(to_run))
    await asyncio.gather(*(_worker(entity) for entity in to_run))


async def _recheck_previous_run(
    client: TelegramClient,
    config: Config,
    confirmed: dict[int, SourceReport],
    visited: set[int],
) -> None:
    """If a previous run left a report.json here, re-verify those sources
    (still active? still relevant?) and keep the ones that pass, so results
    accumulate across runs instead of resetting to zero every time. These
    are already-known sources, so they must not trigger a fresh Saved
    Messages notification just for being re-confirmed.
    """
    previous_report = config.output_dir / "report.json"
    if not previous_report.exists():
        return
    try:
        items = json.loads(previous_report.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Could not read %s, skipping re-check", previous_report)
        return

    known_ids = frozenset(item["chat_id"] for item in items if "chat_id" in item)
    usernames = {item["username"] for item in items if item.get("username")}
    if not usernames:
        return

    logger.info(
        "Re-checking %d sources found in a previous run (%s)",
        len(usernames),
        previous_report,
    )
    prev_candidates = await resolve_usernames(client, usernames)
    await _analyze_batch(
        client, config, prev_candidates, confirmed, visited, suppress_notify_ids=known_ids
    )


async def _pipeline(
    client: TelegramClient,
    config: Config,
    confirmed: dict[int, SourceReport],
    visited: set[int],
) -> None:
    await _recheck_previous_run(client, config, confirmed, visited)

    seeds = await resolve_seeds(client, config.seeds_file)
    if seeds:
        logger.info("Loaded %d seed candidates from %s", len(seeds), config.seeds_file)
        await _analyze_batch(client, config, seeds, confirmed, visited)

    discovered = await discover_chats(client, config)
    candidates = {cid: entity for cid, (entity, _cats) in discovered.items()}
    await _analyze_batch(client, config, candidates, confirmed, visited)

    for round_no in range(1, config.snowball_max_rounds + 1):
        channels_count, chats_count = _split_counts(confirmed)
        if channels_count >= config.target_channels and chats_count >= config.target_chats:
            logger.info(
                "Targets reached (%d channels, %d chats), stopping.",
                channels_count,
                chats_count,
            )
            break

        usernames: set[str] = set()
        for report in confirmed.values():
            usernames |= extract_usernames(report.about)
            for post in report.sample_posts:
                usernames |= extract_usernames(post.text)

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
        await _analyze_batch(client, config, new_candidates, confirmed, visited)


async def run_search(output_dir: str | None) -> None:
    config = load_config()
    if output_dir:
        config = dataclasses.replace(config, output_dir=Path(output_dir))

    client = await build_client(config)
    confirmed: dict[int, SourceReport] = {}
    visited: set[int] = set()

    try:
        pipeline = _pipeline(client, config, confirmed, visited)
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
            "Finished: %d channels, %d chats confirmed (targets: %d channels / %d chats).",
            channels_count,
            chats_count,
            config.target_channels,
            config.target_chats,
        )

        md_path, json_path = write_reports(list(confirmed.values()), config.output_dir)
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
