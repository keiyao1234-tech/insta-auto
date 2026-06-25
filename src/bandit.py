"""多腕バンディットによるハッシュタグセット選択。

arm = (hashtag_set_id, time_bucket)。報酬は harvest が Insights を
config.bandit.reward_weights で合成した値。

- epsilon_greedy: 未試行の arm を優先探索 → ε で探索 → それ以外は最良平均を活用
- thompson:       ガウス近似のトンプソン抽出（未試行は強制探索）
"""
import json
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from . import config, hashtags


def load():
    with open(config.BANDIT_STATE, encoding="utf-8") as f:
        return json.load(f)


def save(state):
    with open(config.BANDIT_STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


def arm_key(set_id, bucket):
    return f"{set_id}|{bucket}"


def _bcfg():
    return config.CONFIG["bandit"]


def time_buckets():
    return _bcfg()["time_buckets"]


def current_time_bucket(dt=None):
    tz = ZoneInfo(config.CONFIG["account"]["timezone"])
    dt = (dt or datetime.now(tz)).astimezone(tz)
    hour = dt.hour
    for b in time_buckets():
        lo, hi = (int(x) for x in b.split("-"))
        if lo <= hour < hi:
            return b
    # バケット範囲外（深夜など）は最後のバケットに寄せる
    return time_buckets()[-1]


def _mean(arm):
    return arm["reward_sum"] / arm["n"] if arm and arm["n"] else 0.0


def select(time_bucket, set_ids=None, state=None, rng=None):
    rng = rng or random
    set_ids = set_ids or hashtags.set_ids()
    state = state or load()
    arms = state.get("arms", {})
    algo = _bcfg().get("algorithm", "epsilon_greedy")

    if algo == "thompson":
        return _thompson(set_ids, time_bucket, arms, rng)

    # epsilon-greedy
    unseen = [s for s in set_ids if arms.get(arm_key(s, time_bucket), {}).get("n", 0) == 0]
    if unseen:
        return rng.choice(unseen)
    if rng.random() < _bcfg().get("epsilon", 0.2):
        return rng.choice(set_ids)
    return max(set_ids, key=lambda s: _mean(arms.get(arm_key(s, time_bucket))))


def _thompson(set_ids, bucket, arms, rng):
    order = set_ids[:]
    rng.shuffle(order)  # 未試行が複数ある場合の偏りを避ける
    best, best_sample = order[0], float("-inf")
    for s in order:
        a = arms.get(arm_key(s, bucket))
        if not a or a["n"] == 0:
            sample = float("inf")
        else:
            n = a["n"]
            mean = a["reward_sum"] / n
            var = max(a.get("reward_sq", 0.0) / n - mean * mean, 1e-6)
            sample = rng.gauss(mean, (var / n) ** 0.5)
        if sample > best_sample:
            best, best_sample = s, sample
    return best


def update(set_id, time_bucket, reward, state=None, persist=True):
    state = state if state is not None else load()
    arms = state.setdefault("arms", {})
    a = arms.setdefault(arm_key(set_id, time_bucket), {"n": 0, "reward_sum": 0.0, "reward_sq": 0.0})
    a["n"] += 1
    a["reward_sum"] += reward
    a["reward_sq"] += reward * reward
    if persist:
        save(state)
    return state


def compute_reward(metrics):
    """Insights 辞書を reward_weights で1つのスカラー報酬に合成する。"""
    weights = _bcfg()["reward_weights"]
    total = 0.0
    for key, w in weights.items():
        val = metrics.get(key)
        try:
            total += float(w) * float(val or 0)
        except (TypeError, ValueError):
            continue
    return total
