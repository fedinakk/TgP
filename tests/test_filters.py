from tgparser.filters import (
    has_price_signal,
    is_bot_welcome,
    is_relevant_job_post,
    is_spam,
    matched_categories,
)


def test_video_editing_job_post_is_relevant():
    text = "Ищем видеомонтажера на удаленку, заказ на неделю, оплата по договоренности"
    relevant, categories = is_relevant_job_post(text)
    assert relevant
    assert "video_editing" in categories


def test_smm_vacancy_is_relevant():
    text = "Требуется SMM менеджер для ведения соцсетей, вакансия, бюджет обсуждается"
    relevant, categories = is_relevant_job_post(text)
    assert relevant
    assert "smm" in categories


def test_reels_order_is_relevant():
    text = "Нужен монтаж reels для tiktok, ищу фрилансера, оплата сдельная"
    relevant, categories = is_relevant_job_post(text)
    assert relevant
    assert "reels_shorts" in categories


def test_plain_mention_without_job_terms_is_not_relevant():
    text = "Сегодня разбираем тренды в reels и tiktok на примере крупных блогеров"
    relevant, _ = is_relevant_job_post(text)
    assert not relevant


def test_unrelated_text_is_not_relevant():
    text = "Продаю котят, недорого, самовывоз"
    relevant, categories = is_relevant_job_post(text)
    assert not relevant
    assert categories == []


def test_spam_terms_are_flagged():
    assert is_spam("Заработок без вложений, инвестируй и получай пассивный доход")
    assert not is_spam("Ищем видеомонтажера, оплата после сдачи проекта")


def test_spam_post_is_excluded_even_if_keywords_present():
    text = "Ищем видеомонтажера! Кстати, у нас розыгрыш и заработок без вложений"
    relevant, _ = is_relevant_job_post(text)
    assert not relevant


def test_matched_categories_multiple():
    text = "Ищем SMM-менеджера и дизайнера креативов для соцсетей, вакансия"
    categories = matched_categories(text)
    assert "smm" in categories
    assert "creatives" in categories


def test_welcome_bot_message_is_detected():
    assert is_bot_welcome("Hi @shivendra_doniwal welcome to my Video Editors group")
    assert is_bot_welcome("Добро пожаловать в нашу группу, новый участник!")
    assert not is_bot_welcome("Нужен видеомонтажер, оплата 500р за ролик")


def test_welcome_bot_message_excluded_even_with_topic_words():
    text = "Hi Umar welcome to my Video Editors group Freelance Video Editors"
    relevant, _ = is_relevant_job_post(text)
    assert not relevant


def test_price_signal_counts_as_order_even_without_job_words():
    assert has_price_signal("Видеомонтажер, 500р за ролик")
    assert has_price_signal("Ищу монтажера, $50 за видео")
    # no explicit job word ("вакансия"/"ищу"/etc.) -> only the price signal
    # should make this count as an order
    relevant, categories = is_relevant_job_post("Видеомонтажер, 500р за ролик, пишите в лс")
    assert relevant
    assert "video_editing" in categories
