# Phase 2: DM → Discord 通知（設計確定・実装は後追い）

Instagram の DM を受信したら Discord に通知する Cloudflare Worker。**受信購読のみ**で自動返信はしないため、メッセージ送信権限や24時間ルールは不要（最小権限）。

## 仕組み
- `GET`  … Meta の Webhook 検証（`hub.challenge` を返す）
- `POST` … `messages` イベントを受け取り、送信者IDと本文を Discord Webhook へ転送

## デプロイ手順（無料枠で完結）
1. Cloudflare アカウント作成（無料）。
2. `cd webhook && npm i -g wrangler`（または `npx wrangler`）。
3. Secrets を登録:
   ```bash
   npx wrangler secret put IG_VERIFY_TOKEN      # 任意の文字列（Meta側と一致させる）
   npx wrangler secret put DISCORD_WEBHOOK_URL  # 通知先 Discord Webhook
   npx wrangler secret put IG_APP_SECRET        # 任意（署名検証する場合）
   ```
4. `npx wrangler deploy` → 払い出された `https://insta-dm-discord.<account>.workers.dev` を控える。
5. Meta アプリ → Webhooks → Instagram → Callback URL に上記 URL、Verify Token に `IG_VERIFY_TOKEN` を設定し、`messages` を購読。
6. アプリに `instagram_business_manage_messages`（受信）を付与し、自分のIGアカウントを購読対象にする。

## 無料枠
Cloudflare Workers 無料プラン = **100,000 リクエスト/日**。個人サロンのDM量では到底届かない。
