"""Configuration loaded from environment variables / .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env_int(name: str, default: int | None = None) -> int | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class ProxyConfig:
    type: str | None
    host: str | None
    port: int | None
    username: str | None = None
    password: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.type and self.host and self.port)


@dataclass(frozen=True)
class Config:
    api_id: int
    api_hash: str
    phone: str | None
    password: str | None
    session_name: str
    proxy: ProxyConfig

    active_window_hours: int
    messages_per_chat: int
    max_pages_per_query: int
    request_delay_seconds: float
    output_dir: Path

    target_channels: int
    target_chats: int
    concurrency: int
    snowball_max_rounds: int
    max_runtime_minutes: int | None
    seeds_file: Path | None
    notify_saved_messages: bool

    auto_join_chats: bool
    join_delay_seconds: float
    max_joins_per_run: int


def load_config() -> Config:
    api_id = _env_int("TG_API_ID")
    api_hash = os.getenv("TG_API_HASH")
    if not api_id or not api_hash:
        raise RuntimeError(
            "TG_API_ID / TG_API_HASH is not set. Get them at https://my.telegram.org "
            "and put them into a .env file (see .env.example)."
        )

    proxy = ProxyConfig(
        type=os.getenv("PROXY_TYPE") or None,
        host=os.getenv("PROXY_HOST") or None,
        port=_env_int("PROXY_PORT"),
        username=os.getenv("PROXY_USERNAME") or None,
        password=os.getenv("PROXY_PASSWORD") or None,
    )

    seeds_file_raw = os.getenv("SEEDS_FILE", "seeds.txt")
    seeds_path = Path(seeds_file_raw) if seeds_file_raw else None
    if seeds_path and not seeds_path.exists():
        seeds_path = None

    return Config(
        api_id=api_id,
        api_hash=api_hash,
        phone=os.getenv("TG_PHONE") or None,
        password=os.getenv("TG_PASSWORD") or None,
        session_name=os.getenv("TG_SESSION_NAME", "tgp_session"),
        proxy=proxy,
        active_window_hours=_env_int("ACTIVE_WINDOW_HOURS", 24),
        messages_per_chat=_env_int("MESSAGES_PER_CHAT", 150),
        max_pages_per_query=_env_int("MAX_PAGES_PER_QUERY", 10),
        request_delay_seconds=float(os.getenv("REQUEST_DELAY_SECONDS", "1.5")),
        output_dir=Path(os.getenv("OUTPUT_DIR", "out")),
        target_channels=_env_int("TARGET_CHANNELS", 150),
        target_chats=_env_int("TARGET_CHATS", 30),
        concurrency=_env_int("CONCURRENCY", 5),
        snowball_max_rounds=_env_int("SNOWBALL_MAX_ROUNDS", 25),
        max_runtime_minutes=_env_int("MAX_RUNTIME_MINUTES", 360),
        seeds_file=seeds_path,
        notify_saved_messages=_env_bool("NOTIFY_SAVED_MESSAGES", True),
        auto_join_chats=_env_bool("AUTO_JOIN_CHATS", True),
        join_delay_seconds=float(os.getenv("JOIN_DELAY_SECONDS", "8")),
        max_joins_per_run=_env_int("MAX_JOINS_PER_RUN", 150),
    )
