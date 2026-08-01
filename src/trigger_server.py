import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from daily_run import run_daily


def make_server(port: int, output_dir: str) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/run-daily":
                self.send_response(404)
                self.end_headers()
                return

            threading.Thread(
                target=run_daily, args=(output_dir,), daemon=True
            ).start()

            self.send_response(202)
            self.end_headers()

        def log_message(self, format, *args):
            pass  # quiet by default; n8n's own execution log has the trigger record

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    listen_port = int(os.environ.get("VOICE2TEXT_TRIGGER_PORT", "8100"))
    output_dir = os.environ.get(
        "VOICE2TEXT_OUTPUT_DIR", os.path.expanduser("~/voice2text-runs")
    )
    server = make_server(listen_port, output_dir)
    print(f"voice2text trigger server listening on 127.0.0.1:{listen_port}")
    server.serve_forever()
