import random

from src import config, media


def test_kind():
    assert media.kind("a.jpg") == "image"
    assert media.kind("a.JPEG") == "image"
    assert media.kind("a.MP4") == "video"
    assert media.kind("a.mov") == "video"
    assert media.kind("note.txt") is None


def test_scan_ignores_unsupported(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"aaa")
    (tmp_path / "b.png").write_bytes(b"bbb")
    (tmp_path / ".gitkeep").write_bytes(b"# keep")
    (tmp_path / "note.txt").write_bytes(b"x")
    names = {p.name for p in media.scan(str(tmp_path))}
    assert names == {"a.jpg", "b.png"}


def test_pick_dedup_then_stop(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"aaa")
    (tmp_path / "b.jpg").write_bytes(b"bbb")
    rng = random.Random(0)
    posted = set()

    _, h1 = media.pick_unposted(str(tmp_path), posted, "stop", rng=rng)
    posted.add(h1)
    _, h2 = media.pick_unposted(str(tmp_path), posted, "stop", rng=rng)
    posted.add(h2)
    assert h1 != h2

    # 全て投稿済み & stop → None
    p3, h3 = media.pick_unposted(str(tmp_path), posted, "stop", rng=rng)
    assert p3 is None and h3 is None


def test_pick_reshuffle_when_exhausted(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"aaa")
    rng = random.Random(0)
    _, h1 = media.pick_unposted(str(tmp_path), set(), "reshuffle", rng=rng)
    p2, h2 = media.pick_unposted(str(tmp_path), {h1}, "reshuffle", rng=rng)
    assert p2 is not None and h2 == h1  # 再利用される


def test_oversized(tmp_path, monkeypatch):
    f = tmp_path / "big.jpg"
    f.write_bytes(b"0" * 2048)
    monkeypatch.setitem(config.CONFIG["media"], "max_file_mb", 0)
    assert media.oversized(f) is True


def test_raw_url_encodes(monkeypatch):
    monkeypatch.setenv("GITHUB_REPO", "owner/repo")
    monkeypatch.setenv("GITHUB_BRANCH", "main")
    p = config.ROOT / "assets" / "stories" / "テスト 画像.jpg"
    url = media.raw_url(p)
    assert url.startswith("https://raw.githubusercontent.com/owner/repo/main/assets/stories/")
    assert "%20" in url  # 空白がエンコードされている
