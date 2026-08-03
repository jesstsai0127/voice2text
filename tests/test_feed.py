import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from feed import find_all_episodes, find_latest_episode, resolve_feed_url

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
    # a parseable ISO timestamp, so Notion's 發布日期 can be sorted newest-first
    assert datetime.fromisoformat(episode["published_at"])


def test_find_all_episodes_returns_every_episode_newest_first():
    episodes = find_all_episodes(TECHWAV_RSS_URL)

    assert len(episodes) > 1
    assert all(e["title"].strip() != "" for e in episodes)
    assert all(e["audio_url"].startswith("https://") for e in episodes)

    published_dates = [datetime.fromisoformat(e["published_at"]) for e in episodes]
    assert published_dates == sorted(published_dates, reverse=True)

    # EP1 (試播集) should be somewhere in the full list, since it's the very
    # first thing this show ever published
    assert any("全世界一起做了一個美夢" in e["title"] for e in episodes)
