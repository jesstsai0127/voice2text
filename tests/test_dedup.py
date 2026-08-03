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
    is_already_processed,
    save_record,
)


def _archive(page_id: str) -> None:
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


def test_processed_source_is_detected_and_new_one_is_not():
    feed_page_id = _create_test_tracked_feed(f"測試節目-{uuid.uuid4().hex[:6]}")
    data_source_id = get_or_create_show_database(feed_page_id, "測試節目")

    filename = f"dedup-test-{uuid.uuid4().hex[:8]}"
    file_size = 99999
    extension = "mp3"

    assert is_already_processed(data_source_id, filename, file_size, extension) is False

    page_id = save_record(
        data_source_id=data_source_id,
        filename=filename,
        file_size=file_size,
        extension=extension,
        transcript="t",
        report="r",
    )

    try:
        assert is_already_processed(data_source_id, filename, file_size, extension) is True

        # same filename+size, different extension -> different source
        assert is_already_processed(data_source_id, filename, file_size, "wav") is False

        # same filename+extension, different size -> different source
        assert (
            is_already_processed(data_source_id, filename, file_size + 1, extension) is False
        )
    finally:
        _archive(page_id)
        _archive(feed_page_id)


def test_duplicate_detection_marks_the_existing_record():
    feed_page_id = _create_test_tracked_feed(f"測試節目-{uuid.uuid4().hex[:6]}")
    data_source_id = get_or_create_show_database(feed_page_id, "測試節目")

    filename = f"dedup-mark-test-{uuid.uuid4().hex[:8]}"
    file_size = 55555
    extension = "m4a"

    page_id = save_record(
        data_source_id=data_source_id,
        filename=filename,
        file_size=file_size,
        extension=extension,
        transcript="t",
        report="r",
    )

    try:
        is_already_processed(data_source_id, filename, file_size, extension)
        is_already_processed(data_source_id, filename, file_size, extension)

        record = fetch_record(page_id)
        assert record["duplicate_count"] == 2
    finally:
        _archive(page_id)
        _archive(feed_page_id)
