"""hashtags.yaml のプール/セットを解決する。

set（名前付きの組み合わせ）が bandit の arm になる。
解決結果は重複除去のうえ最大30件に丸める（Instagramの上限）。
"""
from . import config

MAX_TAGS = 30


def _sets():
    return config.HASHTAGS.get("sets", [])


def _pools():
    return config.HASHTAGS.get("pools", {})


def set_ids():
    return [s["id"] for s in _sets()]


def resolve(set_id, limit=MAX_TAGS):
    spec = next((s for s in _sets() if s["id"] == set_id), None)
    if spec is None:
        raise KeyError(f"未知のハッシュタグセット: {set_id}")
    pools = _pools()
    tags, seen = [], set()
    for pool_name in spec["pools"]:
        for tag in pools.get(pool_name, []):
            if tag not in seen:
                seen.add(tag)
                tags.append(tag)
    return tags[:limit]


def as_text(set_id, limit=MAX_TAGS):
    return " ".join(resolve(set_id, limit))
