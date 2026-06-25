#!/bin/bash
# 写真を assets/ に入れたあと、このファイルをダブルクリックするだけで
# GitHubにアップロード（commit & push）され、次回の予定時刻に自動投稿されます。
cd "$(dirname "$0")" || exit 1
echo "================================"
echo " insta-auto : 写真アップロード"
echo "================================"
echo ""
git add -A
if git diff --cached --quiet; then
  echo "→ 新しい変更はありませんでした。"
else
  git commit -q -m "写真/設定を更新"
  echo "→ 変更を記録しました。アップロード中..."
  git pull --rebase --autostash -q 2>/dev/null
  if git push -q origin main; then
    echo ""
    echo "✓ アップロード完了！次回の予定時刻に自動投稿されます。"
  else
    echo ""
    echo "⚠️ アップロードに失敗しました。ネット接続を確認して再度ダブルクリックしてください。"
  fi
fi
echo ""
read -n 1 -s -r -p "このウィンドウは閉じてOKです（何かキーを押すと閉じます）..."
echo ""
