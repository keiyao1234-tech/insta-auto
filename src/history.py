"""投稿履歴（state/post_history.json）の読み書き。

重複防止のため、投稿したメディアの SHA256 ハッシュを記録する。
各エントリは harvest（Insights回収）でも使うメタ情報を保持する。
"""
import json
from datetime import datetime, timezone

from . import config


def load():
    with open(config.POST_HISTORY, encoding="utf-8") as f:
        return json.load(f)


def save(history):
    with open(config.POST_HISTORY, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
        f.write("\n")


def posted_hashes(history=None):
    history = history or load()
    return {p["hash"] for p in history["posts"]}


def record(entry, history=None):
    history = history or load()
    history["posts"].append(entry)
    save(history)
    return entry


def update_entry(media_id, changes):
    """media_id に一致するエントリを部分更新して保存。"""
    history = load()
    for p in history["posts"]:
        if p.get("media_id") == media_id:
            p.update(changes)
    save(history)
    return history


def utcnow_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
