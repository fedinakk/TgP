"""CLI: discover, analyze and report on Telegram sources for content/SMM job orders.

Usage:
    python -m tgparser.main search [--output-dir out]
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import logging
from pathlib import Path

from .analyzer import analyze_chat
from .config import load_config
from .report import write_reports
from .search import discover_chats
from .tg_client import build_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def run_search(output_dir: str | None) -> None:
    config = load_config()
    if output_dir:
        config = dataclasses.replace(config, output_dir=Path(output_dir))

    client = await build_client(config)
    try:
        candidates = await discover_chats(client, config)
        logger.info("Analyzing %d candidate chats...", len(candidates))

        sources = []
        for i, (entity, _matched_via) in enumerate(candidates.values(), start=1):
            title = getattr(entity, "title", entity.id)
            logger.info("[%d/%d] Analyzing %s", i, len(candidates), title)
            try:
                report = await analyze_chat(client, entity, config)
            except Exception:
                logger.exception("Failed to analyze %s, skipping", title)
                continue
            if report:
                sources.append(report)
            await asyncio.sleep(config.request_delay_seconds)

        md_path, json_path = write_reports(sources, config.output_dir)
        logger.info("Done. %d relevant active sources found.", len(sources))
        logger.info("Markdown report: %s", md_path)
        logger.info("JSON report: %s", json_path)
    finally:
        await client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="Discover and analyze sources")
    search_parser.add_argument("--output-dir", default=None, help="Where to write report.md/report.json")

    args = parser.parse_args()

    if args.command == "search":
        asyncio.run(run_search(args.output_dir))


if __name__ == "__main__":
    main()
