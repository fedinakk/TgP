from telethon.tl.types import Channel, Chat

from tgparser.analyzer import JoinBudget, _build_link, _classify_kind


def _make_channel(**kwargs):
    defaults = dict(id=1, title="Test", photo=None, date=None)
    defaults.update(kwargs)
    return Channel(**defaults)


def test_broadcast_channel_is_classified_as_channel():
    entity = _make_channel(broadcast=True, megagroup=False)
    assert _classify_kind(entity) == "channel"


def test_supergroup_is_classified_as_chat():
    # Modern group chats ("supergroups") are internally `Channel` objects
    # with megagroup=True -- this used to be misclassified as "channel".
    entity = _make_channel(broadcast=False, megagroup=True)
    assert _classify_kind(entity) == "chat"


def test_legacy_basic_group_is_classified_as_chat():
    entity = Chat(id=1, title="Legacy Group", photo=None, participants_count=10, date=None, version=1)
    assert _classify_kind(entity) == "chat"


def test_build_link_uses_username_when_present():
    entity = _make_channel(username="somechannel")
    assert _build_link(entity) == "https://t.me/somechannel"


def test_build_link_falls_back_to_internal_id_without_username():
    entity = _make_channel(username=None)
    assert _build_link(entity) == "t.me/c/1"


def test_join_budget_stops_at_limit():
    budget = JoinBudget(2)
    assert budget.try_consume() is True
    assert budget.try_consume() is True
    assert budget.try_consume() is False
