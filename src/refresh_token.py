"""エントリポイント: 長期アクセストークンをリフレッシュする（週次）。

新トークンは GitHub Actions のステップから `gh secret set` で Secret に保存する。
ログ漏洩を防ぐため ::add-mask:: で伏字化し、GITHUB_ENV 経由で次ステップへ渡す。
ローカル実行時は stdout に出力する。
"""
import logging
import os

from . import config, ig_client, notify

log = logging.getLogger("refresh_token")


def run():
    client = ig_client.IGClient()
    new_token, expires_in = client.refresh_long_lived_token()
    days = round((expires_in or 0) / 86400, 1)
    log.info("トークンをリフレッシュしました。expires_in=%ss (約%s日)", expires_in, days)

    gh_env = os.environ.get("GITHUB_ENV")
    if gh_env:
        # ログ上で伏字化し、後続ステップ用に環境変数として渡す
        print(f"::add-mask::{new_token}")
        with open(gh_env, "a", encoding="utf-8") as f:
            f.write(f"NEW_IG_TOKEN={new_token}\n")
            f.write(f"IG_TOKEN_EXPIRES_IN={expires_in}\n")
    else:
        # ローカル確認用（CIではこの分岐に入らない）
        print(new_token)


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        run()
    except Exception as e:
        notify.alert(f"トークンリフレッシュ失敗（手動再認証が必要かもしれません）: {e}")
        raise


if __name__ == "__main__":
    main()
