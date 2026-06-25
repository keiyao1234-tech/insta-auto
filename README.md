# insta-auto — 美容室Instagram 自動運用システム（完全無料・放置運用・規約準拠）

Instagram プロアカウント（美容室）を、**Instagram 公式 Graph API のみ**を使って自動運用する自己完結システム。非公式自動化（instagrapi / Selenium 等）は **一切使わない**（規約違反・BANリスクのため）。

- 毎日 **ストーリー**を自動投稿（画像/短尺動画・メディアのみ）
- **フィード/Reel** を定期投稿し、キャプション＋ハッシュタグを付与
- Insights の実績で「勝ちパターン（ハッシュタグセット × 投稿時間帯）」を **多腕バンディット**で自己学習
- 同一メディアの**重複投稿を防止**（SHA256）
- 長期アクセストークンを**週次で自動リフレッシュ**
- 失敗時は **Discord** にアラート
- DM → Discord 通知は **Phase 2**（`webhook/` に設計確定済み・後追い実装）

すべて **GitHub の公開リポジトリ + GitHub Actions** で動き、サーバー常時稼働は不要。コスト詳細は [COST_REPORT.md](COST_REPORT.md)。

---

## ⚠️ 最初に知っておくべき公式APIの制約（重要）

| 事項 | 内容 | 本システムの対応 |
|---|---|---|
| ストーリーにタグ不可 | API公開のストーリーは **メディアのみ**。ハッシュタグ・**場所**・スタンプ・キャプション・メンションは付与不可 | ハッシュタグは**フィード/Reel**に付与。場所は必要なら画像に**焼き込み**（`src/overlay.py`） |
| 投稿上限 | **25投稿/24時間**（Story+Feed+Reel 合算） | 1日 数投稿のため余裕 |
| ハッシュタグ検索上限 | **30ユニーク/7日**。リアルタイム流行タグの大量取得は公式無料では不可 | **キュレーション済みプール**（`hashtags.yaml`）＋バンディットで代替 |
| トークン失効 | 長期トークンは**約60日**（24h経過後リフレッシュ可） | `refresh-token` ワークフローで**週次自動更新** |
| メディアは公開URL必須 | Meta が cURL で取得するため、画像/動画は**公開URL**である必要 | 公開GitHubリポの **raw URL** を使用 |
| App Review | 他人のアカウント操作にはフルApp Review（数週間）が必要 | **自分のアカウントのみ**なら tester/admin 登録で **Standard Access** のまま運用可（審査不要） |

---

## アーキテクチャ

```
[GitHub 公開リポ]  ── raw URL ──▶  Meta API (cURL取得)
  ├ assets/stories  画像/動画（ストーリー）
  ├ assets/feed     画像→フィード / 動画→Reel
  ├ state/          履歴・バンディット・metrics（Actionが都度コミット）
  └ .github/workflows
        ├ post-story   毎日       → STORIES（メディアのみ）
        ├ post-feed    月水金      → IMAGE/REELS（caption+hashtags）
        ├ harvest      毎日       → Insights回収 → bandit/metrics 更新
        └ refresh-token 毎週      → トークン更新 → Secret 上書き
  失敗時 → Discord Webhook にアラート
```

state をコミットで戻すことが、GitHub Actions の「60日無活動でcron停止」を防ぐ **keepalive** も兼ねる。

---

## セットアップ手順

### 0. 前提
- Instagram アカウントが **プロアカウント（ビジネス or クリエイター）** であること（個人アカウントはAPI不可）。
  - Instagramアプリ → 設定 → アカウントの種類とツール → プロアカウントに切り替え。
- **Instagram Login 方式**を使うため **Facebookページは不要**。

### 1. Meta アプリを作成し Instagram 製品を追加
1. https://developers.facebook.com/ → My Apps → Create App。
2. ユースケースは「**Instagram**」（Instagram API setup with Instagram login）を選択。
3. アプリに **Instagram** プロダクトを追加。
4. **App roles → Roles** で、自分の Instagram/Meta アカウントを **Tester（または Admin）** として追加し、承認する。
   - これにより **Standard Access** のまま自分のアカウントへ投稿でき、**フルApp Reviewは不要**。

### 2. 必要な権限（スコープ）
Phase 1（本実装）で必要:
- `instagram_business_basic`
- `instagram_business_content_publish`
- `instagram_business_manage_insights`

Phase 2（DM通知）で追加:
- `instagram_business_manage_messages`（受信のみ）

> 注: 2025/01/27 に旧スコープ（`business_*`）が新スコープ（`instagram_business_*`）へ移行済み。最新の公式ドキュメントで名称を必ず確認すること。

### 3. 長期アクセストークンを取得
**かんたん版（推奨）**: アプリdashboard の「Instagram → API setup with Instagram login」に、追加した IG アカウントごとに **トークン生成ボタン**がある。生成して控える（これは長期トークン）。

**OAuth 手動版**:
1. 認可URLをブラウザで開く:
   ```
   https://www.instagram.com/oauth/authorize?client_id={IG_APP_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=instagram_business_basic,instagram_business_content_publish,instagram_business_manage_insights
   ```
2. 戻ってきた `code` を短期トークンに交換:
   ```bash
   curl -X POST https://api.instagram.com/oauth/access_token \
     -d client_id={IG_APP_ID} -d client_secret={IG_APP_SECRET} \
     -d grant_type=authorization_code -d redirect_uri={REDIRECT_URI} -d code={CODE}
   ```
3. 短期 → 長期（約60日）に交換:
   ```bash
   curl "https://graph.instagram.com/access_token?grant_type=ig_exchange_token&client_secret={IG_APP_SECRET}&access_token={SHORT_TOKEN}"
   ```

### 4. IG_USER_ID を取得
```bash
curl "https://graph.instagram.com/me?fields=user_id,username&access_token={LONG_TOKEN}"
```
返ってくる `user_id` を控える。

### 5. GitHub に公開リポジトリを作成して push
```bash
cd ~/insta-auto
git add . && git commit -m "init"
gh repo create insta-auto --public --source=. --push   # または GitHub UI で作成して push
```
> メディアを raw URL 配信するため **公開** にする必要がある（コードや metrics も公開される点に留意。気にする場合は [COST_REPORT.md](COST_REPORT.md) の代替案参照）。

### 6. GitHub Secrets を設定
リポジトリ → Settings → Secrets and variables → Actions → New repository secret:

| Secret | 値 |
|---|---|
| `IG_ACCESS_TOKEN` | 手順3の長期トークン |
| `IG_USER_ID` | 手順4の user_id |
| `IG_APP_ID` | Meta アプリ ID |
| `IG_APP_SECRET` | Meta アプリ シークレット |
| `DISCORD_WEBHOOK_URL` | 通知先 Discord Webhook（任意） |
| `GH_PAT` | トークン自動更新用の Fine-grained PAT（下記） |

**`GH_PAT`（Fine-grained Personal Access Token）の作り方:**
GitHub → Settings → Developer settings → Fine-grained tokens → Generate new token。
- Repository access: このリポのみ
- Permissions: **Secrets → Read and write**、**Contents → Read**
これが `refresh-token` ワークフローで新トークンを Secret に書き戻すために必要。

### 7. メディアを投入
- `assets/stories/` … ストーリー用 画像(.jpg/.png)・動画(.mp4/.mov)
- `assets/feed/` … フィード用 画像 / Reel用 動画
- 推奨: 9:16（1080×1920）。動画 ≤60〜90秒。
- **1ファイル ≤100MB**、**Git LFS は使わない**（LFSだと raw URL がポインタになり Meta が取得できない）。

### 8. hashtags.yaml を自店向けに編集
特に `pools.area`（地域タグ）を自店の地域に変更すると新規発見に最も効く。`sets` の組み合わせも自由に追加可。

### 9. 動作確認
- **ローカルでテスト**: `pip install -r requirements.txt && pytest`
- **ローカルでドライラン**（実投稿なし）:
  ```bash
  cp .env.example .env   # 値を埋める。GITHUB_REPO=yourname/insta-auto, DRY_RUN=1
  python -m src.post_story
  python -m src.post_feed
  ```
- **本番1回**: GitHub → Actions → `post-story` → **Run workflow**（workflow_dispatch）で手動実行 → アカウントにストーリーが出るか確認 → `state/` への更新コミットを確認。
- 同様に `post-feed` / `harvest` / `refresh-token` も手動実行で確認。

---

## 運用・カスタマイズ

| やりたいこと | 場所 |
|---|---|
| 投稿時刻/頻度を変える | `.github/workflows/*.yml` の `cron`（**UTC**。JST = UTC+9） |
| 画像を使い切った後の挙動 | `config.yaml` `media.exhaustion_behavior`: `reshuffle`(再利用) / `stop`(停止) |
| バンディットの探索率・報酬重み | `config.yaml` `bandit.epsilon` / `reward_weights` |
| 投稿時間帯の区切り | `config.yaml` `bandit.time_buckets`（JST時） |
| ハッシュタグ群 | `hashtags.yaml` |
| キャプション文面 | `config.yaml` `caption.templates` |
| ストーリーに場所を焼き込む | `python -m src.overlay assets/stories/foo.jpg --text "渋谷 · YourSalon"`（投稿前にローカルで実行→commit） |
| 改善ログを見る | `state/metrics.csv`（CSV）/ `state/bandit.json`（arm別成績） |

---

## トラブルシュート
- **`GITHUB_REPO が未設定`**: ローカル実行時は `.env` に `GITHUB_REPO=owner/repo` を設定。Actions上では自動で入る。
- **トークン期限切れ**: 60日以上リフレッシュされないと失効し再リフレッシュ不可 → 手順3で再取得し Secret を更新。週次ジョブが動いていれば起きない。
- **動画が `ERROR` / タイムアウト**: 形式（MP4/MOV・9:16・長さ・コーデック H.264/AAC）と100MB上限を確認。`config.yaml` `publish.poll_max_attempts` を増やす。
- **location_id でエラー**: Instagram Login では場所タグ非対応の可能性。`config.yaml` `feed.location_id` を空にする（既定）。
- **cron が動かない**: GitHub Actions の schedule は UTC・数分〜遅延あり・60日無活動で停止。state コミットが keepalive になるが、長期停止時は手動 dispatch で復帰。

---

## 注意（規約・コンプライアンス）
- 公式 Graph API のみ使用。スクレイピングや非公式ライブラリは使わない。
- 自分（自店）のアカウントのみを運用する前提。他人のアカウントを操作する場合はフルApp Reviewが必要。
- シークレットは **Secrets のみ**。`.env` はコミットしない（`.gitignore` 済み）。
