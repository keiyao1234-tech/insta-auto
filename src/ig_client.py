"""Instagram Platform API (Instagram Login) の薄いラッパ。

エンドポイント: graph.instagram.com
コンテンツ公開は 2 ステップ:
  1) コンテナ作成   POST /{ig-user-id}/media
  2) 公開          POST /{ig-user-id}/media_publish (creation_id)
動画は処理が非同期のため、公開前に status_code を FINISHED までポーリングする。
"""
import time

import requests

from . import config

_RETRYABLE = (429, 500, 502, 503, 504)


class IGError(Exception):
    pass


class IGClient:
    def __init__(self, token=None, user_id=None):
        self.token = token or config.access_token()
        self.user_id = user_id or config.user_id(required=False)
        pub = config.CONFIG["publish"]
        self.root = pub["graph_base"].rstrip("/")
        self.base = f'{self.root}/{pub["api_version"]}'
        self.poll_interval = pub["poll_interval_seconds"]
        self.poll_max = pub["poll_max_attempts"]
        self.retries = pub["retry_attempts"]
        self.backoff = pub["retry_backoff_seconds"]

    # ---- 低レベル ----
    def _call(self, method, url, payload=None):
        payload = dict(payload or {})
        payload["access_token"] = self.token
        last_err = None
        for attempt in range(1, self.retries + 1):
            try:
                if method == "GET":
                    resp = requests.get(url, params=payload, timeout=60)
                else:
                    resp = requests.post(url, data=payload, timeout=60)
            except requests.RequestException as e:
                last_err = e
                time.sleep(self.backoff * attempt)
                continue

            try:
                body = resp.json()
            except ValueError:
                body = {}

            if resp.ok and "error" not in body:
                return body

            err = body.get("error") or {}
            msg = err.get("message", resp.text)
            detail = (f"{resp.status_code}: {msg} "
                      f"[code={err.get('code')} subcode={err.get('error_subcode')} "
                      f"type={err.get('type')} fbtrace={err.get('fbtrace_id')}]")
            if resp.status_code in _RETRYABLE:
                last_err = IGError(detail)
                time.sleep(self.backoff * attempt)
                continue
            raise IGError(detail)  # 4xx等は即時失敗
        raise IGError(f"APIリクエスト失敗 ({method} {url}): {last_err}")

    # ---- 公開フロー ----
    def create_container(self, *, kind, media_type, url, caption=None,
                         location_id=None, share_to_feed=None):
        payload = {}
        payload["image_url" if kind == "image" else "video_url"] = url
        if media_type:                       # STORIES / REELS。フィード画像は None
            payload["media_type"] = media_type
        if caption:
            payload["caption"] = caption
        if location_id:
            payload["location_id"] = location_id
        if media_type == "REELS" and share_to_feed is not None:
            payload["share_to_feed"] = "true" if share_to_feed else "false"
        body = self._call("POST", f"{self.base}/{self.user_id}/media", payload)
        return body["id"]

    def container_status(self, container_id):
        body = self._call("GET", f"{self.base}/{container_id}",
                          {"fields": "status_code,status"})
        return body.get("status_code"), body.get("status")

    def wait_until_finished(self, container_id):
        for _ in range(self.poll_max):
            code, detail = self.container_status(container_id)
            if code == "FINISHED":
                return True
            if code in ("ERROR", "EXPIRED"):
                raise IGError(f"コンテナ処理失敗: status_code={code} detail={detail}")
            time.sleep(self.poll_interval)
        raise IGError("コンテナ処理がタイムアウトしました（poll_max 到達）")

    def publish(self, creation_id):
        body = self._call("POST", f"{self.base}/{self.user_id}/media_publish",
                          {"creation_id": creation_id})
        return body["id"]

    def post(self, **kwargs):
        """create_container → wait → publish をまとめて実行し media_id を返す。"""
        container_id = self.create_container(**kwargs)
        self.wait_until_finished(container_id)
        media_id = self.publish(container_id)
        return container_id, media_id

    # ---- Insights ----
    def get_insights(self, media_id, metrics):
        """media の Insights を辞書で返す。メトリクスは一括取得→失敗時は1件ずつ。"""
        def fetch(metric_list):
            body = self._call("GET", f"{self.base}/{media_id}/insights",
                              {"metric": ",".join(metric_list)})
            out = {}
            for item in body.get("data", []):
                name = item.get("name")
                values = item.get("values")
                if values:
                    out[name] = values[0].get("value")
                elif "total_value" in item:
                    out[name] = item["total_value"].get("value")
                else:
                    out[name] = None
            return out

        try:
            return fetch(metrics)
        except IGError:
            result = {}
            for m in metrics:                # 非対応メトリクスがあっても全体は止めない
                try:
                    result.update(fetch([m]))
                except IGError:
                    result[m] = None
            return result

    # ---- アカウント / トークン ----
    def get_user_id(self):
        body = self._call("GET", f"{self.root}/me", {"fields": "user_id,username"})
        return body.get("user_id"), body.get("username")

    def refresh_long_lived_token(self):
        body = self._call("GET", f"{self.root}/refresh_access_token",
                          {"grant_type": "ig_refresh_token"})
        return body["access_token"], body.get("expires_in")
