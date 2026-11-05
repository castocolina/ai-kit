"""Loopback-only fakes for the Cursor Dashboard and command runner."""

import json
import pathlib
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import NamedTuple

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "cursor"


def load_dashboard_fixture(name: str) -> dict:
    """Load one named synthetic Dashboard JSON response."""
    path = FIXTURES / "dashboard" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def redact_payload(value, key: str = ""):
    """Redact strings while retaining the explicitly permitted payload labels."""
    allowed = {"id", "display_name", "version", "name"}
    if isinstance(value, dict):
        return {item_key: redact_payload(item, item_key)
                for item_key, item in value.items()}
    if isinstance(value, list):
        return [redact_payload(item, key) for item in value]
    if isinstance(value, str) and key not in allowed:
        return "<redacted>"
    return value


def _record_pid(pid: int) -> None:
    root = pathlib.Path(__file__).resolve().parent.parent
    ledger = root / "tmp" / "p23" / "03" / "children.pids"
    if ledger.parent.is_dir():
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(f"{pid}\n")


class _Response(NamedTuple):
    status: int
    body: object
    delay_s: float
    location: str | None
    trickle_s: float
    header_trickle_s: float


class _QuietThreadingHTTPServer(ThreadingHTTPServer):
    """Non-daemon handler threads, joined by server_close(): a daemon thread still writing a
    traceback at interpreter shutdown aborts Python (`_enter_buffered_busy`)."""

    def handle_error(self, request, client_address):
        # A client that gave up at its deadline is the point of the stall fakes, not an error.
        if not isinstance(sys.exc_info()[1], ConnectionError):
            super().handle_error(request, client_address)


class FakeDashboard:
    """Threaded Connect-JSON server bound exclusively to IPv4 loopback."""

    def __init__(self):
        self.requests: list[dict[str, str | None]] = []
        self._scripts: dict[str, list[_Response]] = {}
        self._stopped = threading.Event()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def _respond(self):
                length = int(self.headers.get("Content-Length", "0"))
                if length:
                    self.rfile.read(length)
                owner.requests.append({
                    "method": self.command,
                    "path": self.path,
                    "authorization": self.headers.get("Authorization"),
                    "content_type": self.headers.get("Content-Type"),
                })
                method = self.path.rsplit("/", 1)[-1]
                queue = owner._scripts.get(method, [])
                response = queue.pop(0) if queue else _Response(404, {}, 0, None, 0.0, 0.0)
                if owner._stopped.wait(response.delay_s):
                    return
                if response.header_trickle_s > 0:
                    # T-23-30: dribble only the status line and headers, one
                    # byte per interval, until the server stops — every individual recv
                    # succeeds, so a per-socket timeout alone never ends
                    # open(); only absolute-deadline enforcement can break
                    # the stall.
                    self.wfile.write(b"HTTP/1.1 200 OK\r\n")
                    self.wfile.flush()
                    header = b"X-Trickle: 0123456789abcdef\r\n"
                    index = 0
                    while not owner._stopped.wait(response.header_trickle_s):
                        self.wfile.write(header[index:index + 1])
                        self.wfile.flush()
                        index = (index + 1) % len(header)
                    return
                self.send_response(response.status)
                if response.location:
                    self.send_header("Location", response.location)
                payload = json.dumps(response.body).encode()
                if response.trickle_s > 0:
                    # Dribble the body one byte per interval until the server stops: a client
                    # that reads incrementally sees bytes keep arriving just
                    # before every read — a read that loops internally for a
                    # full 64 KiB would then outlive any deadline.
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    index = 0
                    while not owner._stopped.wait(response.trickle_s):
                        self.wfile.write(payload[index:index + 1])
                        self.wfile.flush()
                        index = (index + 1) % len(payload)
                    return
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            do_POST = _respond
            do_GET = _respond

            def log_message(self, _format, *_args):
                return

        self._server = _QuietThreadingHTTPServer(("127.0.0.1", 0), Handler)
        # A 0.05 s poll: the default 0.5 s makes every shutdown() wait up to half a second.
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        kwargs={"poll_interval": 0.05}, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_port}"

    def script(self, method: str, status: int = 200, body=None, delay_s: float = 0.0,
               location: str | None = None, trickle_s: float = 0.0,
               header_trickle_s: float = 0.0) -> None:
        response = _Response(status, body or {}, delay_s, location, trickle_s,
                             header_trickle_s)
        self._scripts.setdefault(method, []).append(response)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_exc):
        self._stopped.set()  # ends every delay and trickle loop, so server_close() can join
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)


class RunResult(NamedTuple):
    returncode: int | None
    text: str
    killed: bool
    blocked: bool
    elapsed_ms: float


def run_like_cursor(argv, payload, *, cwd, env, kill_after_ms=None, timeout_s=10.0):
    """Spawn argv without a shell and mimic Cursor's stdin/stdout handling."""
    started = time.monotonic()
    proc = subprocess.Popen(argv, shell=False, cwd=cwd, env=env, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _record_pid(proc.pid)
    killed = False
    try:
        stdin = proc.stdin
        assert stdin is not None
        stdin.write(json.dumps(payload).encode())
        stdin.close()
        proc.stdin = None
        if kill_after_ms is not None:
            time.sleep(kill_after_ms / 1000)
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
                killed = True
        try:
            out, _err = proc.communicate(timeout=timeout_s)
            text = out.decode(errors="replace").replace("\r", "").rstrip("\n")
            return RunResult(proc.returncode, text, killed, False,
                             (time.monotonic() - started) * 1000)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _err = proc.communicate()
            text = out.decode(errors="replace").replace("\r", "").rstrip("\n")
            return RunResult(proc.returncode, text, killed, True,
                             (time.monotonic() - started) * 1000)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
