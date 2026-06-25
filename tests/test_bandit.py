import random
from datetime import datetime
from zoneinfo import ZoneInfo

from src import bandit, config

TZ = ZoneInfo("Asia/Tokyo")


def test_current_time_bucket():
    assert bandit.current_time_bucket(datetime(2026, 1, 1, 8, tzinfo=TZ)) == "07-10"
    assert bandit.current_time_bucket(datetime(2026, 1, 1, 18, tzinfo=TZ)) == "17-20"
    assert bandit.current_time_bucket(datetime(2026, 1, 1, 21, tzinfo=TZ)) == "20-23"
    # バケット範囲外（深夜）→ 最後のバケットに寄せる
    assert bandit.current_time_bucket(datetime(2026, 1, 1, 3, tzinfo=TZ)) == "20-23"


def test_select_prefers_unseen():
    state = {"arms": {}}
    choice = bandit.select("17-20", set_ids=["a", "b", "c"], state=state, rng=random.Random(1))
    assert choice in {"a", "b", "c"}


def test_update_then_exploit(monkeypatch):
    monkeypatch.setitem(config.CONFIG["bandit"], "algorithm", "epsilon_greedy")
    monkeypatch.setitem(config.CONFIG["bandit"], "epsilon", 0.0)  # 常に活用
    state = {"arms": {}}
    for s in ["a", "b", "c"]:           # 全 arm を試行済みにする
        bandit.update(s, "17-20", 1.0, state=state, persist=False)
    bandit.update("b", "17-20", 100.0, state=state, persist=False)  # b を最良に
    choice = bandit.select("17-20", set_ids=["a", "b", "c"], state=state, rng=random.Random(0))
    assert choice == "b"


def test_update_accumulates():
    state = {"arms": {}}
    bandit.update("x", "10-13", 3.0, state=state, persist=False)
    bandit.update("x", "10-13", 5.0, state=state, persist=False)
    arm = state["arms"][bandit.arm_key("x", "10-13")]
    assert arm["n"] == 2
    assert arm["reward_sum"] == 8.0
    assert arm["reward_sq"] == 34.0


def test_compute_reward():
    # weights: reach1, likes2, comments4, saved6, shares6
    r = bandit.compute_reward({"reach": 10, "likes": 2, "comments": 1, "saved": 0, "shares": 0})
    assert r == 10 + 4 + 4


def test_compute_reward_handles_none():
    r = bandit.compute_reward({"reach": None, "likes": "bad", "comments": 1})
    assert r == 4.0
