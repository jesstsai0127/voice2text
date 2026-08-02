import os
import sys
import threading
import time
from unittest.mock import patch

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import trigger_server


def test_run_daily_endpoint_returns_immediately_and_runs_in_background():
    calls = []

    def fake_run_daily(output_dir):
        calls.append(output_dir)
        time.sleep(0.5)
        return []

    with patch("trigger_server.run_daily", side_effect=fake_run_daily):
        server = trigger_server.make_server(port=0, output_dir="/tmp/voice2text-test")
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            start = time.time()
            response = requests.post(f"http://127.0.0.1:{port}/run-daily", timeout=5)
            elapsed = time.time() - start

            assert response.status_code == 202
            # must return well before the (fake) 0.5s of "work" finishes —
            # proves the work runs in a background thread, not inline
            assert elapsed < 0.3

            time.sleep(0.7)
            assert calls == ["/tmp/voice2text-test"]
        finally:
            server.shutdown()
