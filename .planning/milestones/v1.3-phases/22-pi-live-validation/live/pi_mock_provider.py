#!/usr/bin/env python3
"""Phase 22 spike tool: localhost-only mock provider; never shipped or linked."""

import argparse
import json
import signal
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen


class MockServer(ThreadingHTTPServer):
    """HTTP server that records request paths and model ids only."""

    daemon_threads = True
    allow_reuse_address = True


def make_handler(log_path: Path):
    """Create a request handler bound to the supplied log path."""

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            except (ValueError, UnicodeDecodeError):
                body = {}
            with log_path.open("a", encoding="utf-8") as log:
                log.write(json.dumps({"path": self.path, "model": body.get("model")}) + "\n")
            if not self.path.endswith("chat/completions"):
                self.send_error(404)
                return
            if body.get("stream"):
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                chunks = [
                    {"choices": [{"index": 0, "delta": {"content": "ok"}}]},
                    {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
                ]
                for chunk in chunks:
                    self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                self.wfile.write(b"data: [DONE]\n\n")
            else:
                payload = {
                    "id": "mock-completion",
                    "object": "chat.completion",
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"},
                                 "finish_reason": "stop"}],
                }
                encoded = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        def log_message(self, _format, *_args):
            return

    return Handler


def serve(port_file: Path, log_path: Path, ready: threading.Event | None = None):
    server = MockServer(("127.0.0.1", 0), make_handler(log_path))
    port_file.write_text(str(server.server_address[1]), encoding="ascii")
    if ready:
        ready.set()
    server.serve_forever(poll_interval=0.1)


def self_test():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        port_file, log_path = root / "port", root / "log"
        ready = threading.Event()
        server = MockServer(("127.0.0.1", 0), make_handler(log_path))
        port_file.write_text(str(server.server_address[1]), encoding="ascii")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for stream in (False, True):
                request = Request(
                    f"http://127.0.0.1:{port_file.read_text()}/v1/chat/completions",
                    data=json.dumps({"model": "self-test", "stream": stream}).encode(),
                    headers={"Content-Type": "application/json"}, method="POST",
                )
                with urlopen(request, timeout=3) as response:
                    response.read()
            records = [json.loads(line) for line in log_path.read_text().splitlines()]
            if len(records) != 2 or any(set(row) != {"path", "model"} or
                                         row["model"] != "self-test" for row in records):
                raise AssertionError(f"unexpected log records: {records!r}")
            print("mock self-test ok")
            return 0
        finally:
            server.shutdown()
            thread.join(timeout=3)
            server.server_close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port-file", type=Path)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        try:
            return self_test()
        except Exception as exc:  # self-test reports a concise failure reason
            print(f"mock self-test failed: {exc}")
            return 1
    if args.port_file is None or args.log is None:
        parser.error("--port-file and --log are required unless --self-test is used")
    server = MockServer(("127.0.0.1", 0), make_handler(args.log))
    args.port_file.write_text(str(server.server_address[1]), encoding="ascii")

    def stop(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
