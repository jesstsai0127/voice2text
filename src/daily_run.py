import os

import requests

from feed import find_latest_episode, resolve_feed_url
from notion_store import _headers, _load_secret, list_pending_uploads
from pipeline import process_pending_upload, run_episode


def list_tracked_feeds() -> list:
    response = requests.post(
        f"https://api.notion.com/v1/data_sources/{_load_secret('NOTION_FEEDS_DATA_SOURCE_ID')}/query",
        headers=_headers(),
        json={"page_size": 100},
        timeout=60,
    )
    response.raise_for_status()
    return [
        {"page_id": page["id"], "url": page["properties"]["網址"]["url"]}
        for page in response.json()["results"]
        if page["properties"]["網址"]["url"]
    ]


def run_daily(output_dir: str) -> list:
    results = []
    for feed in list_tracked_feeds():
        feed_url = resolve_feed_url(feed["url"])
        episode = find_latest_episode(feed_url)
        source_dir = os.path.join(output_dir, episode["filename"])
        result = run_episode(
            episode["audio_url"],
            source_dir,
            filename=episode["filename"],
            title=episode["title"],
            source_page_id=feed["page_id"],
        )
        results.append({"feed_url": feed["url"], "episode": episode, **result})

    for pending in list_pending_uploads():
        source_dir = os.path.join(output_dir, pending["page_id"])
        result = process_pending_upload(
            page_id=pending["page_id"],
            file_url=pending["file_url"],
            filename=pending["filename"],
            output_dir=source_dir,
        )
        results.append({"pending_upload": pending, **result})

    return results
