from tgparser.search import _search_windows


def test_search_windows_are_five_non_overlapping_ranges_newest_first():
    windows = _search_windows()
    assert len(windows) == 5

    # Each window is (min_date, max_date); newest window's max_date is the
    # most recent, and each next window picks up exactly where the last
    # one's min_date left off.
    for i in range(len(windows) - 1):
        min_date, max_date = windows[i]
        next_min_date, next_max_date = windows[i + 1]
        assert min_date == next_max_date

    assert windows[0][1] is not None  # newest window has a concrete max_date (~now)
    assert windows[-1][0] is None  # oldest window is open-ended into the past
