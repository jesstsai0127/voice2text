import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from daily_run import run_personal_uploads
from notion_store import _headers, get_or_create_show_database

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
PERSONAL_AUDIO_FEED_PAGE_ID = "3b1fa664-385e-81d2-b403-c7e9224ab940"  # 個人音檔


def _simulate_manual_upload(filename: str) -> str:
    data_source_id = get_or_create_show_database(PERSONAL_AUDIO_FEED_PAGE_ID, "個人音檔")

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
                "data_source_id": data_source_id,
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


def test_run_personal_uploads_processes_pending_uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "daily_run.list_tracked_feeds",
        lambda: [
            {
                "page_id": PERSONAL_AUDIO_FEED_PAGE_ID,
                "url": None,
                "name": "個人音檔",
                "source_type": "個人上傳",
            }
        ],
    )
    monkeypatch.setenv("VOICE2TEXT_LOCK_PATH", str(tmp_path / "job.lock"))

    page_id = _simulate_manual_upload("known-sentence.m4a")

    try:
        results = run_personal_uploads(str(tmp_path))

        matching = [r for r in results if r.get("notion_page_id") == page_id]
        assert len(matching) == 1
        assert matching[0]["skipped"] is False
    finally:
        _archive(page_id)
