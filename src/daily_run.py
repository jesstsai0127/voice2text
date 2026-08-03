import os

import requests

from feed import find_latest_episode, resolve_feed_url
from notion_store import (
    _headers,
    _load_secret,
    get_or_create_show_database,
    list_pending_uploads,
)
from pipeline import process_pending_upload, run_episode

PERSONAL_UPLOAD_SOURCE_TYPE = "個人上傳"


def list_tracked_feeds() -> list:
    response = requests.post(
        f"https://api.notion.com/v1/data_sources/{_load_secret('NOTION_FEEDS_DATA_SOURCE_ID')}/query",
        headers=_headers(),
        json={"page_size": 100},
        timeout=60,
    )
    response.raise_for_status()
    feeds = []
    for page in response.json()["results"]:
        props = page["properties"]
        name_title = props["名稱"]["title"]
        source_type_select = props["來源類型"]["select"]
        feeds.append(
            {
                "page_id": page["id"],
                "url": props["網址"]["url"],
                "name": name_title[0]["plain_text"] if name_title else "",
                "source_type": source_type_select["name"] if source_type_select else None,
            }
        )
    return feeds


def run_daily(output_dir: str) -> list:
    results = []
    for feed in list_tracked_feeds():
        data_source_id = get_or_create_show_database(feed["page_id"], feed["name"])

        if feed["source_type"] == PERSONAL_UPLOAD_SOURCE_TYPE:
            for pending in list_pending_uploads(data_source_id):
                source_dir = os.path.join(output_dir, pending["page_id"])
                result = process_pending_upload(
                    page_id=pending["page_id"],
                    file_url=pending["file_url"],
                    filename=pending["filename"],
                    output_dir=source_dir,
                    data_source_id=data_source_id,
                )
                results.append({"pending_upload": pending, **result})
            continue

        feed_url = resolve_feed_url(feed["url"])
        episode = find_latest_episode(feed_url)
        source_dir = os.path.join(output_dir, episode["filename"])
        result = run_episode(
            episode["audio_url"],
            source_dir,
            filename=episode["filename"],
            title=episode["title"],
            data_source_id=data_source_id,
        )
        results.append({"feed_url": feed["url"], "episode": episode, **result})

    return results
