import http.server
import json
import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _make_server(responses):
    """Serves one canned (status, body) response per request, in order.
    Extra requests beyond the list keep repeating the last response."""
    call_count = {"n": 0}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(length)

            index = min(call_count["n"], len(responses) - 1)
            call_count["n"] += 1
            status, body = responses[index]

            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(body).encode("utf-8"))

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, call_count


def test_transcribe_succeeds_normally_on_first_try(monkeypatch):
    server, call_count = _make_server([(200, {"text": "第一次就成功"})])
    monkeypatch.setenv("WHISPER_SERVER_URL", f"http://127.0.0.1:{server.server_address[1]}")
    import importlib
    import transcribe

    importlib.reload(transcribe)

    try:
        text = transcribe.transcribe(os.path.join(FIXTURE_DIR, "known-sentence.m4a"))
        assert text == "第一次就成功"
        assert call_count["n"] == 1
    finally:
        server.shutdown()


def test_transcribe_retries_once_with_fallback_and_succeeds(monkeypatch):
    server, call_count = _make_server(
        [(500, {"error": "boom"}), (200, {"text": "第二次成功"})]
    )
    monkeypatch.setenv("WHISPER_SERVER_URL", f"http://127.0.0.1:{server.server_address[1]}")
    import importlib
    import transcribe

    importlib.reload(transcribe)

    try:
        text = transcribe.transcribe(os.path.join(FIXTURE_DIR, "known-sentence.m4a"))
        assert text == "第二次成功"
        assert call_count["n"] == 2
    finally:
        server.shutdown()


def test_transcribe_raises_clear_failure_when_both_attempts_fail(monkeypatch):
    server, call_count = _make_server([(500, {"error": "boom"})])
    monkeypatch.setenv("WHISPER_SERVER_URL", f"http://127.0.0.1:{server.server_address[1]}")
    import importlib
    import transcribe

    importlib.reload(transcribe)

    try:
        with pytest.raises(transcribe.TranscriptionFailedError):
            transcribe.transcribe(os.path.join(FIXTURE_DIR, "known-sentence.m4a"))
        assert call_count["n"] == 2
    finally:
        server.shutdown()
