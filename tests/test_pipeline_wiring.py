import http.server
import os
import sys
import threading
import uuid

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from notion_store import _headers, fetch_record
from pipeline import run_episode

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _archive(page_id: str) -> None:
    response = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=_headers(),
        json={"in_trash": True},
        timeout=60,
    )
    response.raise_for_status()


def _serve_fixture_dir():
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(
        *a, directory=FIXTURE_DIR, **kw
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def test_pipeline_saves_to_notion_and_skips_on_rerun(tmp_path):
    server = _serve_fixture_dir()
    port = server.server_address[1]
    # unique per-run filename so this test's dedup check doesn't collide with
    # rows left by other test runs
    unique_name = f"known-sentence-{uuid.uuid4().hex[:8]}.m4a"
    url = f"http://127.0.0.1:{port}/known-sentence.m4a"

    page_id = None
    try:
        result = run_episode(url, str(tmp_path), filename=unique_name)
        assert result["skipped"] is False
        page_id = result["notion_page_id"]

        record = fetch_record(page_id)
        assert record["transcript"] != ""
        assert record["report"] != ""

        # second run with the same filename+size must be recognized as a
        # duplicate and skipped, not reprocessed/re-saved
        second_output_dir = str(tmp_path / "second-run")
        second_result = run_episode(url, second_output_dir, filename=unique_name)
        assert second_result["skipped"] is True
    finally:
        server.shutdown()
        if page_id:
            _archive(page_id)
