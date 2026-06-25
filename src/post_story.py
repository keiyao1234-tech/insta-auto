"""エントリポイント: ストーリーを1件投稿する（画像 or 動画、メディアのみ）。"""
import logging

from . import bandit, config, history, ig_client, media, notify

log = logging.getLogger("post_story")


def run():
    if not config.CONFIG["story"].get("enabled"):
        log.info("story.enabled=false のためスキップ")
        return

    posted = history.posted_hashes()
    behavior = config.CONFIG["media"]["exhaustion_behavior"]
    path, sha = media.pick_unposted(config.CONFIG["media"]["stories_dir"], posted, behavior)
    if not path:
        log.info("投稿可能なストーリー素材がありません（behavior=%s）", behavior)
        return

    k = media.kind(path)
    url = media.raw_url(path)
    bucket = bandit.current_time_bucket()
    log.info("選択: %s (%s) bucket=%s -> %s", path.name, k, bucket, url)

    if config.dry_run():
        log.info("[DRY_RUN] STORIES を投稿せず終了")
        return

    client = ig_client.IGClient()
    try:
        container_id, media_id = client.post(kind=k, media_type="STORIES", url=url)
    except Exception as e:
        raise RuntimeError(f"{path.name}: {e}") from e

    history.record({
        "asset": str(path.relative_to(config.ROOT)),
        "hash": sha,
        "channel": "story",
        "media_id": media_id,
        "container_id": container_id,
        "hashtag_set": None,
        "time_bucket": bucket,
        "posted_at": history.utcnow_iso(),
        "metrics_harvested": False,
    })
    log.info("ストーリー投稿成功 media_id=%s", media_id)
    notify.info(f"ストーリー投稿: {path.name}")


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        run()
    except Exception as e:
        notify.alert(f"ストーリー投稿失敗: {e}")
        raise


if __name__ == "__main__":
    main()
