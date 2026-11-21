from watermark import decide_mode


def test_no_bookmark_means_full():
    assert decide_mode(None, 72) == "full"


def test_valid_bookmark_means_incremental():
    assert decide_mode(80, 72) == "incremental"


def test_bookmark_equal_to_min_valid_is_ok():
    assert decide_mode(72, 72) == "incremental"


def test_expired_bookmark_means_full():
    assert decide_mode(70, 72) == "full"
