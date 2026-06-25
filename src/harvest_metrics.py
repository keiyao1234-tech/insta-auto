"""エントリポイント: 直近投稿の Insights を回収し、bandit と metrics.csv を更新する。

- story : Insights は約24hで消えるため、未回収なら今すぐ回収して確定する
- feed/reel : Insights は永続。feed_maturity_days 経過後に1回だけ回収して
              bandit を更新する（重複加算を避けるため成熟後の1回のみ）
"""
import csv
import logging
from datetime import datetime, timedelta, timezone

from . import bandit, config, history, ig_client, notify

log = logging.getLogger("harvest")

CSV_FIELDS = ["harvested_at", "media_id", "channel", "asset", "hashtag_set",
              "time_bucket", "reach", "likes", "comments", "saved", "shares",
              "replies", "views", "reward"]


def _safe_insights(client, media_id, metrics):
    try:
        return client.get_insights(media_id, metrics) or {}
    except ig_client.IGError as e:
        log.warning("Insights取得失敗 media_id=%s: %s", media_id, e)
        return {}


def _row(now_iso, post, metrics, reward=""):
    return {
        "harvested_at": now_iso,
        "media_id": post.get("media_id"),
        "channel": post.get("channel"),
        "asset": post.get("asset"),
        "hashtag_set": post.get("hashtag_set") or "",
        "time_bucket": post.get("time_bucket") or "",
        "reach": metrics.get("reach", ""),
        "likes": metrics.get("likes", ""),
        "comments": metrics.get("comments", ""),
        "saved": metrics.get("saved", ""),
        "shares": metrics.get("shares", ""),
        "replies": metrics.get("replies", ""),
        "views": metrics.get("views", ""),
        "reward": reward,
    }


def _append_csv(rows):
    if not rows:
        return
    exists = config.METRICS_CSV.exists() and config.METRICS_CSV.stat().st_size > 0
    with open(config.METRICS_CSV, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not exists:
            writer.writeheader()
        for r in rows:
            writer.writerow(r)


def run():
    icfg = config.CONFIG["insights"]
    maturity = timedelta(days=icfg["feed_maturity_days"])
    now = datetime.now(timezone.utc)
    now_iso = history.utcnow_iso()

    hist = history.load()
    pending = [p for p in hist["posts"] if not p.get("metrics_harvested")]
    if not pending:
        log.info("回収対象なし")
        return

    if config.dry_run():
        for p in pending:
            log.info("[DRY_RUN] 回収対象: %s media_id=%s", p["channel"], p.get("media_id"))
        return

    client = ig_client.IGClient()
    bandit_state = bandit.load()
    bandit_changed = False
    rows = []

    for p in pending:
        age = now - history.parse_iso(p["posted_at"])
        channel = p["channel"]

        if channel == "story":
            metrics = _safe_insights(client, p["media_id"], icfg["story_metrics"])
            p["metrics_harvested"] = True
            rows.append(_row(now_iso, p, metrics))
            log.info("story回収 media_id=%s metrics=%s", p["media_id"], metrics)
            continue

        # feed / reel
        if age < maturity:
            log.info("未成熟のため次回へ media_id=%s age=%s", p["media_id"], age)
            continue
        metric_names = icfg["reel_metrics"] if channel == "reel" else icfg["feed_metrics"]
        metrics = _safe_insights(client, p["media_id"], metric_names)
        reward = bandit.compute_reward(metrics)
        if p.get("hashtag_set") and p.get("time_bucket"):
            bandit.update(p["hashtag_set"], p["time_bucket"], reward,
                          state=bandit_state, persist=False)
            bandit_changed = True
        p["metrics_harvested"] = True
        rows.append(_row(now_iso, p, metrics, reward))
        log.info("%s回収 media_id=%s reward=%.2f set=%s", channel, p["media_id"],
                 reward, p.get("hashtag_set"))

    if bandit_changed:
        bandit.save(bandit_state)
    history.save(hist)
    _append_csv(rows)
    log.info("回収完了 rows=%d bandit_updated=%s", len(rows), bandit_changed)


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        run()
    except Exception as e:
        notify.alert(f"Insights回収失敗: {e}")
        raise


if __name__ == "__main__":
    main()
