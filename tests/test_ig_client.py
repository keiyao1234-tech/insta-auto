import pytest
import responses

from src import config, ig_client

BASE = config.CONFIG["publish"]["graph_base"]
VER = config.CONFIG["publish"]["api_version"]


@responses.activate
def test_post_flow_image_story():
    client = ig_client.IGClient(token="t", user_id="123")
    responses.add(responses.POST, f"{BASE}/{VER}/123/media",
                  json={"id": "container1"}, status=200)
    responses.add(responses.GET, f"{BASE}/{VER}/container1",
                  json={"status_code": "FINISHED"}, status=200)
    responses.add(responses.POST, f"{BASE}/{VER}/123/media_publish",
                  json={"id": "media9"}, status=200)

    cid, mid = client.post(kind="image", media_type="STORIES", url="https://x/y.jpg")
    assert cid == "container1" and mid == "media9"


@responses.activate
def test_container_error_raises():
    client = ig_client.IGClient(token="t", user_id="123")
    responses.add(responses.POST, f"{BASE}/{VER}/123/media",
                  json={"id": "c1"}, status=200)
    responses.add(responses.GET, f"{BASE}/{VER}/c1",
                  json={"status_code": "ERROR", "status": "boom"}, status=200)
    with pytest.raises(ig_client.IGError):
        client.post(kind="video", media_type="STORIES", url="https://x/y.mp4")


@responses.activate
def test_4xx_no_retry():
    client = ig_client.IGClient(token="t", user_id="123")
    responses.add(responses.POST, f"{BASE}/{VER}/123/media",
                  json={"error": {"message": "bad request"}}, status=400)
    with pytest.raises(ig_client.IGError):
        client.create_container(kind="image", media_type="STORIES", url="https://x")
    assert len(responses.calls) == 1  # リトライしていない


@responses.activate
def test_5xx_retries_then_succeeds(monkeypatch):
    monkeypatch.setitem(config.CONFIG["publish"], "retry_backoff_seconds", 0)
    client = ig_client.IGClient(token="t", user_id="123")
    responses.add(responses.POST, f"{BASE}/{VER}/123/media",
                  json={"error": {"message": "temporary"}}, status=503)
    responses.add(responses.POST, f"{BASE}/{VER}/123/media",
                  json={"id": "c2"}, status=200)
    cid = client.create_container(kind="image", media_type="STORIES", url="https://x")
    assert cid == "c2"
    assert len(responses.calls) == 2


@responses.activate
def test_insights_ok():
    client = ig_client.IGClient(token="t", user_id="123")
    responses.add(responses.GET, f"{BASE}/{VER}/m1/insights",
                  json={"data": [
                      {"name": "reach", "values": [{"value": 100}]},
                      {"name": "likes", "values": [{"value": 5}]},
                  ]}, status=200)
    out = client.get_insights("m1", ["reach", "likes"])
    assert out["reach"] == 100 and out["likes"] == 5


@responses.activate
def test_refresh_token():
    client = ig_client.IGClient(token="old", user_id="123")
    responses.add(responses.GET, f"{BASE}/refresh_access_token",
                  json={"access_token": "new", "expires_in": 5184000}, status=200)
    tok, exp = client.refresh_long_lived_token()
    assert tok == "new" and exp == 5184000


@responses.activate
def test_create_container_reel_payload():
    client = ig_client.IGClient(token="t", user_id="123")
    responses.add(responses.POST, f"{BASE}/{VER}/123/media",
                  json={"id": "c3"}, status=200)
    client.create_container(kind="video", media_type="REELS",
                            url="https://x/v.mp4", caption="hi #a", share_to_feed=True)
    body = responses.calls[0].request.body
    assert "video_url=" in body and "media_type=REELS" in body and "share_to_feed=true" in body
