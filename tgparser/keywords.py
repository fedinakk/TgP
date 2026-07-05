"""Keyword sets used to search Telegram and to score/filter results.

Each category has:
  - search_queries: short phrases fed into Telegram's global chat search
    (contacts.search), used to *discover* candidate channels/chats.
  - content_terms: words/phrases that must appear in a message for it to be
    considered "about this niche" (case-insensitive, word-boundary aware).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    search_queries: tuple[str, ...]
    content_terms: tuple[str, ...]


CATEGORIES: tuple[Category, ...] = (
    Category(
        key="video_editing",
        label="Видеомонтаж",
        search_queries=(
            "видеомонтаж вакансия",
            "видеомонтажер заказ",
            "монтажер видео удаленно",
            "ищу видеомонтажера",
            "video editor freelance",
        ),
        content_terms=(
            "видеомонтаж", "видеомонтажер", "монтажер", "монтаж видео",
            "видеоредактор", "premiere pro", "davinci resolve", "video editor",
            "video editing",
        ),
    ),
    Category(
        key="reels_shorts",
        label="Reels / TikTok / Shorts",
        search_queries=(
            "монтаж reels заказ",
            "tiktok монтажер",
            "shorts монтаж вакансия",
            "нарезка видео тикток",
            "reels editor",
        ),
        content_terms=(
            "reels", "рилс", "рилсы", "tiktok", "тикток", "shorts", "шортс",
            "нарезк", "клипмейкер", "клипы для",
        ),
    ),
    Category(
        key="motion_design",
        label="Motion design",
        search_queries=(
            "motion designer вакансия",
            "моушн дизайнер заказ",
            "аниматор 2d вакансия",
            "moldon design freelance",
            "after effects аниматор",
        ),
        content_terms=(
            "motion design", "моушн дизайн", "моушен дизайн", "моушн-дизайнер",
            "2d анимация", "аниматор", "after effects", "ae аниматор",
        ),
    ),
    Category(
        key="smm",
        label="SMM / ведение соцсетей",
        search_queries=(
            "smm вакансия удаленно",
            "smm менеджер заказ",
            "ведение соцсетей вакансия",
            "smm specialist freelance",
            "требуется smm",
        ),
        content_terms=(
            "smm", "смм", "ведение соцсетей", "ведение социальных сетей",
            "контент-менеджер", "контент менеджер", "smm-менеджер",
            "smm менеджер", "social media manager",
        ),
    ),
    Category(
        key="creatives",
        label="Креативы для соцсетей",
        search_queries=(
            "креативы для таргета заказ",
            "дизайнер креативов вакансия",
            "креативщик соцсети",
            "creative designer ads freelance",
            "баннеры для рекламы вакансия",
        ),
        content_terms=(
            "креатив", "креативы", "креативщик", "дизайнер креативов",
            "баннер для рекламы", "рекламный креатив", "ad creative",
        ),
    ),
)

# A message must also look like an order/job post, not just mention the niche.
JOB_TERMS: tuple[str, ...] = (
    "вакансия", "вакансии", "ищем", "ищу", "в поиске", "требуется", "требуются",
    "нужен", "нужна", "нужны", "заказ", "закажу", "фриланс", "удаленно",
    "удалённо", "подработка", "сотрудничество", "оплата", "бюджет", "гонорар",
    "резюме", "портфолио", "отклик", "тз на", "техническое задание",
    "job", "hiring", "freelance", "budget", "paid",
)

# Phrases that flag spam / unrelated channel-growth noise so we can drop them.
SPAM_TERMS: tuple[str, ...] = (
    "заработок без вложений", "пассивный доход", "инвестици", "казино",
    "ставки на спорт", "криптовалют", "быстрый заработок", "розыгрыш",
    "giveaway", "подпишись и получи", "заработок в интернете",
    "курс по заработку", "arbitrage", "forex", "бинарные опционы",
    "р2р", "obnal", "обнал",
)

ALL_CATEGORIES_BY_KEY = {c.key: c for c in CATEGORIES}
