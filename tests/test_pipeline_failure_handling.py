import http.server
import importlib
import json
import os
import sys
import threading
import uuid

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import transcribe
from notion_store import _headers, _load_secret, get_or_create_show_database

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


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


def _serve_fixture_dir():
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(
        *a, directory=FIXTURE_DIR, **kw
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _serve_always_failing_whisper():
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(length)
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "boom"}).encode("utf-8"))

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def test_run_episode_returns_failed_result_instead_of_raising(tmp_path, monkeypatch):
    audio_server = _serve_fixture_dir()
    whisper_server = _serve_always_failing_whisper()
    monkeypatch.setenv(
        "WHISPER_SERVER_URL", f"http://127.0.0.1:{whisper_server.server_address[1]}"
    )
    importlib.reload(transcribe)
    import pipeline

    importlib.reload(pipeline)
    run_episode = pipeline.run_episode

    feed_page_id = _create_test_tracked_feed(f"測試節目-{uuid.uuid4().hex[:6]}")
    data_source_id = get_or_create_show_database(feed_page_id, "測試節目")

    unique_name = f"known-sentence-{uuid.uuid4().hex[:8]}.m4a"
    url = f"http://127.0.0.1:{audio_server.server_address[1]}/known-sentence.m4a"

    try:
        result = run_episode(
            url, str(tmp_path), filename=unique_name, data_source_id=data_source_id
        )

        assert result["skipped"] is False
        assert result["failed"] is True
        assert "notion_page_id" not in result
    finally:
        audio_server.shutdown()
        whisper_server.shutdown()
        _archive(feed_page_id)
        monkeypatch.undo()
        importlib.reload(transcribe)
        importlib.reload(pipeline)
