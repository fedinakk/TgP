import pytest
from telethon.errors import FloodWaitError

from tgparser.flood import wait_out_flood


class _FakeRequest:
    pass


def _make_flood_wait(seconds: int) -> FloodWaitError:
    return FloodWaitError(request=_FakeRequest(), capture=str(seconds))


@pytest.mark.asyncio
async def test_short_flood_wait_is_slept_out(monkeypatch):
    slept = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr("tgparser.flood.asyncio.sleep", fake_sleep)

    exc = _make_flood_wait(5)
    result = await wait_out_flood(exc, max_wait_seconds=300, context="test")

    assert result is True
    assert slept == [6]  # exc.seconds + 1


@pytest.mark.asyncio
async def test_huge_flood_wait_is_not_slept_out(monkeypatch):
    slept = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr("tgparser.flood.asyncio.sleep", fake_sleep)

    exc = _make_flood_wait(75982)  # ~21 hours
    result = await wait_out_flood(exc, max_wait_seconds=300, context="test")

    assert result is False
    assert slept == []  # must never block the run for hours
