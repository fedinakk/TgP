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
    chats_per_keyword: int
    request_delay_seconds: float
    output_dir: Path


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

    return Config(
        api_id=api_id,
        api_hash=api_hash,
        phone=os.getenv("TG_PHONE") or None,
        password=os.getenv("TG_PASSWORD") or None,
        session_name=os.getenv("TG_SESSION_NAME", "tgp_session"),
        proxy=proxy,
        active_window_hours=_env_int("ACTIVE_WINDOW_HOURS", 24),
        messages_per_chat=_env_int("MESSAGES_PER_CHAT", 80),
        chats_per_keyword=_env_int("CHATS_PER_KEYWORD", 25),
        request_delay_seconds=float(os.getenv("REQUEST_DELAY_SECONDS", "1.5")),
        output_dir=Path(os.getenv("OUTPUT_DIR", "out")),
    )
