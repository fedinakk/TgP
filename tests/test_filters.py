from tgparser.filters import is_relevant_job_post, is_spam, matched_categories


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
