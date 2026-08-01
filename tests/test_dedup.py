import os
import sys
import uuid

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from notion_store import _headers, is_already_processed, save_record


def _archive(page_id: str) -> None:
    response = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=_headers(),
        json={"in_trash": True},
        timeout=60,
    )
    response.raise_for_status()


def test_processed_source_is_detected_and_new_one_is_not():
    filename = f"dedup-test-{uuid.uuid4().hex[:8]}.mp3"
    file_size = 99999

    assert is_already_processed(filename, file_size) is False

    page_id = save_record(
        filename=filename, file_size=file_size, transcript="t", report="r"
    )

    try:
        assert is_already_processed(filename, file_size) is True

        # same filename, different size -> treated as a different source
        assert is_already_processed(filename, file_size + 1) is False
    finally:
        _archive(page_id)
