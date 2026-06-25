"""フィード/Reel 用キャプションの生成。

既定はテンプレ + 選択されたハッシュタグセットで完全無料。
config.caption.llm.enabled を true にすると _llm_rewrite フックが呼ばれる
（任意・課金の可能性あり → COST_REPORT.md 参照）。
"""
import random

from . import config, hashtags


def build(set_id, rng=None):
    rng = rng or random
    templates = config.CONFIG["caption"]["templates"]
    template = rng.choice(templates)
    text = template.format(hashtags=hashtags.as_text(set_id))

    llm = config.CONFIG["caption"].get("llm", {})
    if llm.get("enabled"):
        text = _llm_rewrite(text, llm)
    return text


def _llm_rewrite(text, llm):
    """任意の LLM 文章生成フック。既定OFF。

    ここに anthropic SDK 等の呼び出しを差し込める。未実装でもシステム全体は
    テンプレ生成で動作する。有効化する場合の注意は COST_REPORT.md を参照。
    """
    return text
