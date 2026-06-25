"""メディア資産の走査・ハッシュ・重複排除・選択・公開URL生成。"""
import hashlib
import random
from pathlib import Path
from urllib.parse import quote

from . import config


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _img_exts():
    return [e.lower() for e in config.CONFIG["media"]["image_extensions"]]


def _vid_exts():
    return [e.lower() for e in config.CONFIG["media"]["video_extensions"]]


def kind(path):
    """'image' | 'video' | None"""
    ext = Path(path).suffix.lower()
    if ext in _img_exts():
        return "image"
    if ext in _vid_exts():
        return "video"
    return None


def oversized(path):
    max_mb = config.CONFIG["media"]["max_file_mb"]
    return Path(path).stat().st_size > max_mb * 1024 * 1024


def scan(directory):
    """サポート対象メディアを名前順で返す（.gitkeep等は無視）。"""
    base = config.ROOT / directory
    if not base.exists():
        return []
    out = [p for p in sorted(base.iterdir()) if p.is_file() and kind(p)]
    return out


def raw_url(path):
    rel = Path(path).resolve().relative_to(config.ROOT).as_posix()
    # 日本語ファイル名などを安全にエンコード（'/' は維持）
    return f"{config.raw_base_url()}/{quote(rel)}"


def pick_unposted(directory, posted, behavior="reshuffle", rng=None):
    """未投稿メディアを1件選び (Path, sha256) を返す。なければ (None, None)。

    behavior == 'reshuffle' のとき、全て投稿済みならランダムに1件再利用する。
    behavior == 'stop' のとき、全て投稿済みなら (None, None)。
    """
    rng = rng or random
    candidates = [p for p in scan(directory) if not oversized(p)]
    if not candidates:
        return None, None

    order = candidates[:]
    rng.shuffle(order)
    for p in order:
        h = file_sha256(p)
        if h not in posted:
            return p, h

    if behavior == "reshuffle":
        p = rng.choice(candidates)
        return p, file_sha256(p)
    return None, None
