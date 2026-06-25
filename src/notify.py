"""Discord Webhook 通知。失敗アラートに使う（Phase2のDM中継も再利用予定）。"""
import requests

from . import config


def discord(content, success=False):
    url = config.discord_webhook()
    n = config.CONFIG["notify"]
    if not url:
        return False
    if success and not n.get("discord_on_success"):
        return False
    if not success and not n.get("discord_on_failure"):
        return False
    try:
        requests.post(url, json={"content": content[:1900]}, timeout=15)
        return True
    except requests.RequestException:
        return False


def alert(msg):
    return discord(f"⚠️ [insta-auto] {msg}", success=False)


def info(msg):
    return discord(f"✅ [insta-auto] {msg}", success=True)
