import os
import sys
import uuid

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from notion_store import (
    _headers,
    _load_secret,
    fetch_record,
    get_or_create_show_database,
    save_record,
)


def _archive(page_id: str) -> None:
    # Test-only cleanup so runs don't leave permanent rows in the real
    # Notion database. Notion has no hard delete via the API — archiving
    # (moving to trash) is the closest equivalent.
    response = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=_headers(),
        json={"in_trash": True},
        timeout=60,
    )
    response.raise_for_status()


def _create_test_tracked_feed(name: str) -> str:
    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=_headers(),
        json={
            "parent": {
                "type": "data_source_id",
                "data_source_id": _load_secret("NOTION_FEEDS_DATA_SOURCE_ID"),
            },
            "properties": {
                "名稱": {"title": [{"type": "text", "text": {"content": name}}]},
            },
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["id"]


def _fetch_page_properties(page_id: str) -> dict:
    response = requests.get(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=_headers(),
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["properties"]


def test_get_or_create_show_database_creates_once_and_reuses():
    feed_page_id = _create_test_tracked_feed(f"測試節目-{uuid.uuid4().hex[:6]}")

    try:
        first_data_source_id = get_or_create_show_database(feed_page_id, "測試節目")
        second_data_source_id = get_or_create_show_database(feed_page_id, "測試節目")

        assert first_data_source_id == second_data_source_id

        stored_id = _fetch_page_properties(feed_page_id)["集數資料庫ID"]["rich_text"]
        assert stored_id[0]["plain_text"] == first_data_source_id
    finally:
        _archive(feed_page_id)


def test_save_record_round_trips_through_notion():
    feed_page_id = _create_test_tracked_feed(f"測試節目-{uuid.uuid4().hex[:6]}")
    data_source_id = get_or_create_show_database(feed_page_id, "測試節目")

    unique_filename = f"test-{uuid.uuid4().hex[:8]}"
    file_size = 12345
    extension = "mp3"
    title = "EP999 - 測試集數標題"
    transcript = "這是一份測試逐字稿，用來驗證 Notion 儲存有沒有正確存進去。"
    report = "- 測試重點一\n- 測試重點二"

    page_id = save_record(
        data_source_id=data_source_id,
        filename=unique_filename,
        file_size=file_size,
        extension=extension,
        transcript=transcript,
        report=report,
        tags=["測試分類"],
        title=title,
    )

    try:
        record = fetch_record(page_id)

        assert record["filename"] == unique_filename
        assert record["file_size"] == file_size
        assert record["extension"] == extension
        assert record["tags"] == ["測試分類"]
        assert record["title"] == title
        assert transcript in record["transcript"]
        assert report in record["report"]
    finally:
        _archive(page_id)
        _archive(feed_page_id)
