import os
import sys
import uuid

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from notion_store import _headers, fetch_record, is_already_processed, save_record


def _archive(page_id: str) -> None:
    response = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=_headers(),
        json={"in_trash": True},
        timeout=60,
    )
    response.raise_for_status()


def test_processed_source_is_detected_and_new_one_is_not():
    filename = f"dedup-test-{uuid.uuid4().hex[:8]}"
    file_size = 99999
    extension = "mp3"

    assert is_already_processed(filename, file_size, extension) is False

    page_id = save_record(
        filename=filename,
        file_size=file_size,
        extension=extension,
        transcript="t",
        report="r",
    )

    try:
        assert is_already_processed(filename, file_size, extension) is True

        # same filename+size, different extension -> different source
        assert is_already_processed(filename, file_size, "wav") is False

        # same filename+extension, different size -> different source
        assert is_already_processed(filename, file_size + 1, extension) is False
    finally:
        _archive(page_id)


def test_duplicate_detection_marks_the_existing_record():
    filename = f"dedup-mark-test-{uuid.uuid4().hex[:8]}"
    file_size = 55555
    extension = "m4a"

    page_id = save_record(
        filename=filename,
        file_size=file_size,
        extension=extension,
        transcript="t",
        report="r",
    )

    try:
        is_already_processed(filename, file_size, extension)
        is_already_processed(filename, file_size, extension)

        record = fetch_record(page_id)
        assert record["duplicate_count"] == 2
    finally:
        _archive(page_id)
