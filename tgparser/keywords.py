"""Keyword sets used to search Telegram and to score/filter results.

Each category has:
  - search_queries: phrases fed into Telegram's full-text global message
    search (messages.searchGlobal), used to *discover* candidate posts (and,
    through them, the channels/chats that published them).
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
            "видеомонтаж вакансия",
            "видеомонтажер заказ",
            "видеомонтажер удаленно",
            "монтажер видео удаленно",
            "ищу видеомонтажера",
            "нужен видеомонтажер",
            "требуется видеомонтажер",
            "видеомонтажер фриланс",
            "video editor freelance",
            "video editor hiring",
            "монтаж видео за оплату",
            "монтажер на постоянку",
            "видеомонтажер подработка",
            "видеомонтажер резюме портфолио",
            "ищем монтажера",
            "нужен монтаж ролика",
            "видеомонтаж на удаленке",
            "видеооператор монтажер вакансия",
            "premiere pro монтажер вакансия",
            "davinci resolve монтажер заказ",
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
            "монтажер reels удаленно",
            "tiktok монтажер",
            "shorts монтаж вакансия",
            "нарезка видео тикток",
            "нужен монтажер reels",
            "ищу монтажера shorts",
            "reels editor freelance",
            "клипмейкер вакансия",
            "монтаж коротких видео заказ",
            "нарезка рилс вакансия",
            "монтаж тикток видео заказ",
            "нужен монтажер shorts",
            "клипы для тикток заказ",
            "reels editor hiring",
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
            "моушн дизайнер удаленно",
            "аниматор 2d вакансия",
            "нужен моушн дизайнер",
            "ищу моушн дизайнера",
            "motion design freelance",
            "after effects аниматор вакансия",
            "2d аниматор заказ",
            "моушн дизайнер подработка",
            "требуется моушн дизайнер",
            "аниматор фриланс заказ",
            "motion designer hiring",
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
            "требуется smm менеджер",
            "нужен smm менеджер",
            "ищу smm специалиста",
            "smm specialist freelance",
            "контент менеджер вакансия удаленно",
            "smm менеджер удаленно оплата",
            "ведение инстаграм вакансия",
            "smm менеджер подработка",
            "нужен smm специалист",
            "smm manager hiring",
            "продвижение соцсетей вакансия",
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
            "нужен дизайнер креативов",
            "ищу креативщика",
            "creative designer ads freelance",
            "баннеры для рекламы вакансия",
            "статичные креативы заказ",
            "дизайнер рекламных креативов подработка",
            "требуется дизайнер креативов",
            "креатив для рекламы фриланс",
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
