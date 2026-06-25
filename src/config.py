"""設定とシークレットの読み込み。

- config.yaml / hashtags.yaml を読み込む
- 環境変数（ローカルは .env、本番は GitHub Actions Secrets）を参照する
- メディアの公開 raw URL のベースを組み立てる

シークレットは決してファイルに書かない。すべて環境変数経由で受け取る。
"""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent

# ローカル実行時のみ .env を読む。GitHub Actions では env が直接渡るため無害。
load_dotenv(ROOT / ".env")


def _load_yaml(name):
    with open(ROOT / name, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


CONFIG = _load_yaml("config.yaml")
HASHTAGS = _load_yaml("hashtags.yaml")

# --- state ファイルのパス ---
STATE_DIR = ROOT / "state"
POST_HISTORY = STATE_DIR / "post_history.json"
BANDIT_STATE = STATE_DIR / "bandit.json"
METRICS_CSV = STATE_DIR / "metrics.csv"


# --- env アクセサ ---
def env(key, default=None, required=False):
    val = os.environ.get(key, default)
    if required and not val:
        raise RuntimeError(f"必須の環境変数が未設定です: {key}")
    return val


def access_token(required=True):
    return env("IG_ACCESS_TOKEN", required=required)


def user_id(required=True):
    return env("IG_USER_ID", required=required)


def app_id():
    return env("IG_APP_ID")


def app_secret():
    return env("IG_APP_SECRET")


def discord_webhook():
    return env("DISCORD_WEBHOOK_URL")


def dry_run():
    return str(env("DRY_RUN", "0")).lower() in ("1", "true", "yes")


def github_repo():
    # GitHub Actions では GITHUB_REPOSITORY が自動設定される
    return env("GITHUB_REPO") or env("GITHUB_REPOSITORY")


def github_branch():
    return env("GITHUB_BRANCH") or env("GITHUB_REF_NAME") or "main"


def raw_base_url():
    repo = github_repo()
    if not repo:
        raise RuntimeError(
            "GITHUB_REPO（または GITHUB_REPOSITORY）が未設定です。メディアの raw URL を生成できません。"
        )
    return f"https://raw.githubusercontent.com/{repo}/{github_branch()}"
