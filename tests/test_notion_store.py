import os
import sys
import uuid

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from notion_store import _headers, fetch_record, save_record


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


def test_save_record_round_trips_through_notion():
    unique_filename = f"test-{uuid.uuid4().hex[:8]}.mp3"
    file_size = 12345
    transcript = "這是一份測試逐字稿，用來驗證 Notion 儲存有沒有正確存進去。"
    report = "- 測試重點一\n- 測試重點二"

    page_id = save_record(
        filename=unique_filename,
        file_size=file_size,
        transcript=transcript,
        report=report,
    )

    try:
        record = fetch_record(page_id)

        assert record["filename"] == unique_filename
        assert record["file_size"] == file_size
        assert transcript in record["transcript"]
        assert report in record["report"]
    finally:
        _archive(page_id)
