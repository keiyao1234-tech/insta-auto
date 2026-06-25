import pytest

from src import hashtags


def test_set_ids_present():
    ids = hashtags.set_ids()
    assert "balanced" in ids and len(ids) >= 1


def test_resolve_dedup_and_cap():
    tags = hashtags.resolve("balanced")
    assert tags == list(dict.fromkeys(tags))  # 重複なし・順序維持
    assert len(tags) <= hashtags.MAX_TAGS
    assert all(t.startswith("#") for t in tags)


def test_resolve_unknown_raises():
    with pytest.raises(KeyError):
        hashtags.resolve("does_not_exist")


def test_as_text():
    text = hashtags.as_text("cut_focus")
    assert "#" in text and " " in text
