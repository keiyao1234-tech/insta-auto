"""エントリポイント: フィード/Reel を1件投稿する（キャプション＋ハッシュタグ）。

画像 → 通常フィード投稿、動画 → Reel。
bandit が (hashtagセット × 時間帯) を選び、harvest で成績を学習する。
"""
import logging

from . import bandit, caption, config, history, ig_client, media, notify

log = logging.getLogger("post_feed")


def run():
    cfg = config.CONFIG["feed"]
    if not cfg.get("enabled"):
        log.info("feed.enabled=false のためスキップ")
        return

    posted = history.posted_hashes()
    behavior = config.CONFIG["media"]["exhaustion_behavior"]["feed"]
    path, sha = media.pick_unposted(config.CONFIG["media"]["feed_dir"], posted, behavior)
    if not path:
        log.info("投稿可能なフィード素材がありません（behavior=%s）", behavior)
        return

    k = media.kind(path)
    url = media.raw_url(path)
    bucket = bandit.current_time_bucket()
    set_id = bandit.select(bucket)
    cap = caption.build(set_id)
    media_type = "REELS" if k == "video" else None
    channel = "reel" if k == "video" else "feed"
    location_id = cfg.get("location_id") or None

    log.info("選択: %s (%s) channel=%s set=%s bucket=%s", path.name, k, channel, set_id, bucket)
    log.info("caption:\n%s", cap)

    if config.dry_run():
        log.info("[DRY_RUN] %s を投稿せず終了", channel)
        return

    client = ig_client.IGClient()
    try:
        container_id, media_id = client.post(
            kind=k, media_type=media_type, url=url, caption=cap,
            location_id=location_id, share_to_feed=cfg.get("reel_share_to_feed", True),
        )
    except Exception as e:
        raise RuntimeError(f"{path.name}: {e}") from e

    history.record({
        "asset": str(path.relative_to(config.ROOT)),
        "hash": sha,
        "channel": channel,
        "media_id": media_id,
        "container_id": container_id,
        "hashtag_set": set_id,
        "time_bucket": bucket,
        "posted_at": history.utcnow_iso(),
        "metrics_harvested": False,
    })
    log.info("%s 投稿成功 media_id=%s set=%s", channel, media_id, set_id)
    notify.info(f"{channel} 投稿: {path.name} (set={set_id})")


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        run()
    except Exception as e:
        notify.alert(f"フィード投稿失敗: {e}")
        raise


if __name__ == "__main__":
    main()
