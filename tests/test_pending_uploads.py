import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from notion_store import (
    _headers,
    _load_secret,
    list_pending_uploads,
    update_record,
)

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _simulate_manual_upload(filename: str) -> str:
    """Creates a page with only the 音檔 file property set, exactly as a
    user manually dragging a file into Notion would leave it — no title,
    no status. Returns the new page id."""
    upload = requests.post(
        "https://api.notion.com/v1/file_uploads",
        headers=_headers(),
        json={},
        timeout=60,
    )
    upload.raise_for_status()
    upload_id = upload.json()["id"]

    fixture_path = os.path.join(FIXTURE_DIR, filename)
    with open(fixture_path, "rb") as f:
        send = requests.post(
            f"https://api.notion.com/v1/file_uploads/{upload_id}/send",
            headers={
                "Authorization": _headers()["Authorization"],
                "Notion-Version": _headers()["Notion-Version"],
            },
            files={"file": (filename, f, "audio/mp4")},
            timeout=60,
        )
    send.raise_for_status()

    page = requests.post(
        "https://api.notion.com/v1/pages",
        headers=_headers(),
        json={
            "parent": {
                "type": "data_source_id",
                "data_source_id": _load_secret("NOTION_DATA_SOURCE_ID"),
            },
            "properties": {
                "音檔": {
                    "files": [
                        {
                            "type": "file_upload",
                            "file_upload": {"id": upload_id},
                            "name": filename,
                        }
                    ]
                }
            },
        },
        timeout=60,
    )
    page.raise_for_status()
    return page.json()["id"]


def _archive(page_id: str) -> None:
    response = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=_headers(),
        json={"in_trash": True},
        timeout=60,
    )
    response.raise_for_status()


def test_pending_upload_is_listed_then_disappears_once_processed():
    page_id = _simulate_manual_upload("known-sentence.m4a")

    try:
        pending = list_pending_uploads()
        matching = [p for p in pending if p["page_id"] == page_id]
        assert len(matching) == 1
        assert matching[0]["filename"] == "known-sentence.m4a"
        assert matching[0]["file_url"].startswith("https://")

        update_record(
            page_id=page_id,
            filename="known-sentence",
            file_size=59145,
            extension="m4a",
            transcript="測試逐字稿",
            report="測試報告",
            tags=["測試"],
        )

        pending_after = list_pending_uploads()
        assert page_id not in [p["page_id"] for p in pending_after]
    finally:
        _archive(page_id)
