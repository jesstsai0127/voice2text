import os
from datetime import datetime, timedelta, timezone

import requests

from feed import find_all_episodes, resolve_feed_url
from joblock import JobAlreadyRunningError, exclusive_job_lock
from notion_store import (
    _headers,
    _load_secret,
    get_or_create_show_database,
    is_filename_recorded,
    list_pending_uploads,
)
from pipeline import process_pending_upload, run_episode

PERSONAL_UPLOAD_SOURCE_TYPE = "個人上傳"
RECENT_WINDOW_DAYS = 3
BACKFILL_BATCH_SIZE = 3


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


def _podcast_feeds() -> list:
    return [
        feed
        for feed in list_tracked_feeds()
        if feed["source_type"] != PERSONAL_UPLOAD_SOURCE_TYPE and feed["url"]
    ]


def _process_episode(feed: dict, data_source_id: str, episode: dict, output_dir: str) -> dict:
    source_dir = os.path.join(output_dir, episode["filename"])
    result = run_episode(
        episode["audio_url"],
        source_dir,
        filename=episode["filename"],
        title=episode["title"],
        data_source_id=data_source_id,
        published_at=episode["published_at"],
    )
    return {"feed_url": feed["url"], "episode": episode, **result}


def _run_podcast_check(output_dir: str) -> list:
    results = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_WINDOW_DAYS)
    for feed in _podcast_feeds():
        data_source_id = get_or_create_show_database(feed["page_id"], feed["name"])
        episodes = find_all_episodes(resolve_feed_url(feed["url"]))
        recent = [
            episode
            for episode in episodes
            if datetime.fromisoformat(episode["published_at"]) >= cutoff
        ]
        for episode in recent:
            results.append(_process_episode(feed, data_source_id, episode, output_dir))
    return results


def _run_backfill(output_dir: str, batch_size: int) -> list:
    results = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_WINDOW_DAYS)
    for feed in _podcast_feeds():
        data_source_id = get_or_create_show_database(feed["page_id"], feed["name"])
        episodes = find_all_episodes(resolve_feed_url(feed["url"]))
        older = [
            episode
            for episode in episodes
            if datetime.fromisoformat(episode["published_at"]) < cutoff
        ]

        processed_count = 0
        for episode in older:
            if processed_count >= batch_size:
                break
            base_name, ext = os.path.splitext(episode["filename"])
            extension = ext.lstrip(".")
            if is_filename_recorded(data_source_id, base_name, extension):
                continue
            results.append(_process_episode(feed, data_source_id, episode, output_dir))
            processed_count += 1
    return results


def _run_personal_uploads(output_dir: str) -> list:
    results = []
    for feed in list_tracked_feeds():
        if feed["source_type"] != PERSONAL_UPLOAD_SOURCE_TYPE:
            continue
        data_source_id = get_or_create_show_database(feed["page_id"], feed["name"])
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
    return results


def run_daily_podcast_check(output_dir: str) -> list:
    try:
        with exclusive_job_lock():
            return _run_podcast_check(output_dir)
    except JobAlreadyRunningError:
        return []


def run_podcast_backfill(output_dir: str, batch_size: int = BACKFILL_BATCH_SIZE) -> list:
    try:
        with exclusive_job_lock():
            return _run_backfill(output_dir, batch_size)
    except JobAlreadyRunningError:
        return []


def run_personal_uploads(output_dir: str) -> list:
    try:
        with exclusive_job_lock():
            return _run_personal_uploads(output_dir)
    except JobAlreadyRunningError:
        return []


def run_daily(output_dir: str) -> list:
    """Back-compat entry point covering the two priority jobs (today's new
    podcast episodes + pending personal uploads); backfill runs on its own
    separate schedule via run_podcast_backfill()."""
    return run_daily_podcast_check(output_dir) + run_personal_uploads(output_dir)
