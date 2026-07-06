"""Builds a connected Telethon client, wired through the SOCKS5 VPN proxy if configured."""
from __future__ import annotations

import getpass
import logging

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from .config import Config

logger = logging.getLogger(__name__)

_VALID_PROXY_TYPES = {"socks5", "socks4", "http"}


def _proxy_tuple(config: Config):
    proxy = config.proxy
    if not proxy.enabled:
        return None
    proxy_type = proxy.type.lower()
    if proxy_type not in _VALID_PROXY_TYPES:
        raise ValueError(f"Unsupported PROXY_TYPE: {proxy.type!r} (use socks5/socks4/http)")
    # Telethon accepts the type as a plain lowercase string (it resolves the
    # actual constant itself via whichever of python-socks/PySocks is
    # installed) — (proxy_type, host, port, rdns, username, password).
    return (proxy_type, proxy.host, proxy.port, True, proxy.username, proxy.password)


async def build_client(config: Config) -> TelegramClient:
    """Create and fully authenticate a TelegramClient.

    On first run this performs the interactive Telegram login (phone number,
    SMS/app login code, and 2FA password if enabled) and caches the session
    in `<session_name>.session` so subsequent runs reuse it without
    re-authenticating.
    """
    client = TelegramClient(
        config.session_name,
        config.api_id,
        config.api_hash,
        proxy=_proxy_tuple(config),
    )

    await client.connect()

    if not await client.is_user_authorized():
        phone = config.phone or input("Enter your phone number (with country code, e.g. +7...): ")
        await client.send_code_request(phone)
        code = input("Enter the login code you received in Telegram: ")
        try:
            await client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            password = config.password or getpass.getpass("Two-factor password: ")
            await client.sign_in(password=password)

    return client
