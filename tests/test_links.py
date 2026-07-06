from tgparser.links import extract_usernames, parse_seed_line


def test_extract_usernames_from_public_links():
    text = "Заходите в наш канал t.me/smm_jobs_ru и чат t.me/video_editors_chat, спасибо!"
    assert extract_usernames(text) == {"smm_jobs_ru", "video_editors_chat"}


def test_extract_usernames_skips_private_invite_links():
    text = "Приватная группа: t.me/joinchat/AbCdEfGh12345 или t.me/+AbCdEfGh12345"
    assert extract_usernames(text) == set()


def test_extract_usernames_empty_text():
    assert extract_usernames("") == set()
    assert extract_usernames(None) == set()


def test_parse_seed_line_variants():
    assert parse_seed_line("@smm_jobs_ru") == "smm_jobs_ru"
    assert parse_seed_line("https://t.me/smm_jobs_ru") == "smm_jobs_ru"
    assert parse_seed_line("smm_jobs_ru") == "smm_jobs_ru"
    assert parse_seed_line("# a comment") is None
    assert parse_seed_line("   ") is None
