import os

import requests

from feed import find_latest_episode, resolve_feed_url
from notion_store import _headers, _load_secret
from pipeline import run_episode


def list_tracked_feeds() -> list:
    response = requests.post(
        f"https://api.notion.com/v1/data_sources/{_load_secret('NOTION_FEEDS_DATA_SOURCE_ID')}/query",
        headers=_headers(),
        json={"page_size": 100},
        timeout=60,
    )
    response.raise_for_status()
    return [
        page["properties"]["網址"]["url"]
        for page in response.json()["results"]
        if page["properties"]["網址"]["url"]
    ]


def run_daily(output_dir: str) -> list:
    results = []
    for raw_url in list_tracked_feeds():
        feed_url = resolve_feed_url(raw_url)
        episode = find_latest_episode(feed_url)
        source_dir = os.path.join(output_dir, episode["filename"])
        result = run_episode(
            episode["audio_url"], source_dir, filename=episode["filename"]
        )
        results.append({"feed_url": raw_url, "episode": episode, **result})
    return results
