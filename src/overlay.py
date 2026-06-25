"""ストーリー画像に「場所/ラベル」を焼き込むローカル前処理ユーティリティ。

なぜ前処理か:
  API公開ストーリーには場所スタンプもテキストも付与できない（Meta公式制約）。
  さらに投稿は「コミット済みファイルの raw URL」を Meta が取得する方式のため、
  実行時に新しい画像を生成しても GitHub 上に存在せず取得できない。
  よって場所表示が必要なら、投稿前にこのツールで画像へ焼き込み、commit しておく。

使い方（ローカル）:
  python -m src.overlay assets/stories/foo.jpg --text "渋谷 · YourSalon"
  → assets/stories/foo.jpg を上書き（--out で別名保存も可）
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_MARGIN = 36


def _load_font(size):
    for name in (
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",  # macOS 日本語
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
        "/Library/Fonts/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _xy(position, img_w, img_h, text_w, text_h):
    if position == "bottom-left":
        return _MARGIN, img_h - text_h - _MARGIN
    if position == "top-left":
        return _MARGIN, _MARGIN
    if position == "top-right":
        return img_w - text_w - _MARGIN, _MARGIN
    return img_w - text_w - _MARGIN, img_h - text_h - _MARGIN  # bottom-right


def overlay_image(in_path, text, out_path=None, position="bottom-right"):
    in_path = Path(in_path)
    out_path = Path(out_path) if out_path else in_path
    img = Image.open(in_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    font = _load_font(max(int(img.height * 0.035), 22))

    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = _xy(position, img.width, img.height, tw, th)

    # 半透明の下地 + 影 + 本文で可読性を確保
    pad = 16
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.rounded_rectangle(
        [x - pad, y - pad, x + tw + pad, y + th + pad], radius=14, fill=(0, 0, 0, 120)
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.text((x, y), text, font=font, fill=(255, 255, 255))

    img.save(out_path, quality=92)
    return out_path


def main():
    ap = argparse.ArgumentParser(description="ストーリー画像に場所ラベルを焼き込む")
    ap.add_argument("image")
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--position", default="bottom-right")
    args = ap.parse_args()
    out = overlay_image(args.image, args.text, args.out, args.position)
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
