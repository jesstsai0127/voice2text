import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from feed import find_latest_episode, resolve_feed_url

# 哈利說「科技浪 Tech.wav」— used throughout this project as the reference show
TECHWAV_APPLE_URL = "https://podcasts.apple.com/tw/podcast/ep1-%E8%A9%A6%E6%92%AD%E9%9B%86-%E5%85%A8%E4%B8%96%E7%95%8C%E4%B8%80%E8%B5%B7%E5%81%9A%E4%BA%86%E4%B8%80%E5%80%8B%E7%BE%8E%E5%A4%A2/id1702409419?i=1000624338047"
TECHWAV_RSS_URL = "https://feed.firstory.me/rss/user/cm3o5681s06e801v3fxpjehwb"


def test_resolve_feed_url_converts_apple_podcasts_url_to_rss():
    resolved = resolve_feed_url(TECHWAV_APPLE_URL)
    assert resolved == TECHWAV_RSS_URL


def test_resolve_feed_url_passes_through_an_already_rss_url():
    resolved = resolve_feed_url(TECHWAV_RSS_URL)
    assert resolved == TECHWAV_RSS_URL


def test_find_latest_episode_returns_a_playable_audio_url():
    episode = find_latest_episode(TECHWAV_RSS_URL)

    assert episode["title"].strip() != ""
    assert episode["audio_url"].startswith("https://")
    assert episode["filename"] != ""
