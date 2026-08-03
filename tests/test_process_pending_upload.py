import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from notion_store import _headers, _load_secret, fetch_record, list_pending_uploads
from pipeline import process_pending_upload

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _simulate_manual_upload(filename: str) -> str:
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


def test_process_pending_upload_updates_the_same_row(tmp_path):
    page_id = _simulate_manual_upload("known-sentence.m4a")

    try:
        pending = [p for p in list_pending_uploads() if p["page_id"] == page_id]
        assert len(pending) == 1

        result = process_pending_upload(
            page_id=pending[0]["page_id"],
            file_url=pending[0]["file_url"],
            filename=pending[0]["filename"],
            output_dir=str(tmp_path),
        )

        assert result["skipped"] is False
        assert result["notion_page_id"] == page_id  # same row, not a new one

        record = fetch_record(page_id)
        assert record["filename"] == "known-sentence"
        assert record["extension"] == "m4a"
        assert record["transcript"] != ""
        assert record["report"] != ""

        still_pending = [p for p in list_pending_uploads() if p["page_id"] == page_id]
        assert still_pending == []
    finally:
        _archive(page_id)
