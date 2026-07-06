"""Keyword sets used to search Telegram and to score/filter results.

Each category has:
  - search_queries: broad terms for the role/niche itself (not "topic + job
    word" combinations) fed into Telegram's full-text global message search
    (messages.searchGlobal) to *discover* candidate posts. A bare term like
    "видеомонтажер" already matches every message containing that word --
    narrowing it to "видеомонтажер вакансия" would only return a subset of
    that, so there's no need to enumerate job-word combinations here.
    Whether a matched post is actually an order/job post is decided later,
    per-message, by filters.is_relevant_job_post (topic term + a hiring/price
    signal) -- that's what keeps the results relevant, not the query itself.
  - content_terms: words/phrases that must appear in a message for it to be
    considered "about this niche" (word-start match, Cyrillic-aware).
"""
from __future__ import annotations

from dataclasses import dataclass


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
            "видеомонтажер",
            "видеомонтаж",
            "монтажер видео",
            "монтаж роликов",
            "видеоредактор",
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
            "монтаж reels",
            "монтаж shorts",
            "монтаж тикток",
            "нарезка роликов",
            "клипмейкер",
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
            "моушн дизайнер",
            "моушн дизайн",
            "2d аниматор",
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
            "smm менеджер",
            "ведение соцсетей",
            "вести соцсети",
            "контент менеджер соцсети",
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
            "дизайнер креативов",
            "креативы для рекламы",
            "рекламный креатив",
            "баннеры для таргета",
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

# Currency/price mentions count as an order signal even without an explicit
# job word above (e.g. "нужен монтаж, 500р за ролик" has no "вакансия"/"заказ").
PRICE_PATTERN = r"(\d+[\s\d]*(?:₽|руб|rub|\$|usd|€|eur)\b|за\s+(?:ролик|видео|минуту|рилс))"

# Phrases that flag spam / unrelated channel-growth noise so we can drop them.
SPAM_TERMS: tuple[str, ...] = (
    "заработок без вложений", "пассивный доход", "инвестици", "казино",
    "ставки на спорт", "криптовалют", "быстрый заработок", "розыгрыш",
    "giveaway", "подпишись и получи", "заработок в интернете",
    "курс по заработку", "arbitrage", "forex", "бинарные опционы",
    "р2р", "obnal", "обнал",
)

# Auto-generated "new member" / bot-greeting messages: they often repeat a
# channel's own name/niche words, which used to trip the content-term match
# even though they carry no actual order.
WELCOME_PATTERNS: tuple[str, ...] = (
    r"welcome to (my|this|our|the) .*(group|channel)",
    r"^hi\s+@?\w+[,!]?\s+welcome",
    r"добро пожаловать в (наш|нашу|группу|канал|чат)",
    r"новый участник",
    r"поприветствуем",
)

ALL_CATEGORIES_BY_KEY = {c.key: c for c in CATEGORIES}
