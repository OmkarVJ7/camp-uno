"""Command Centre: opens the dashboard in its own window.

Serves the web folder on a fixed local port (so the page's saved settings survive
restarts). The page opens instantly from the last saved snapshot while fresh data
is gathered in the background; Refresh gathers it on the spot.
Everything the app stores stays under D:\\command-centre\\data.
"""
import json
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import webview

import collectors

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
DATA = ROOT.parent / "data"
SNAPSHOT = DATA / "cache" / "snapshot.json"
PORT = 47821
BACKGROUND_MINUTES = 15   # how often fresh data is gathered while the app is open


class Snapshot:
    """The latest gathered data, shared by every page load. `version` goes up with each refresh."""

    def __init__(self):
        self.lock = threading.Lock()
        self.ready = threading.Event()
        self.data, self.version = None, 0
        if SNAPSHOT.exists():
            try:
                self.data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
                self.data["META"]["version"] = 0   # from disk: fresher data is on its way
                self.ready.set()
            except ValueError:
                pass

    def refresh(self):
        data = collectors.collect()
        with self.lock:
            self.version += 1
            data["META"]["version"] = self.version
            self.data = data
        self.ready.set()
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def current(self):
        self.ready.wait(timeout=30)
        with self.lock:
            return self.data, self.version


snapshot = Snapshot()


def keep_fresh():
    while True:
        try:
            snapshot.refresh()
        except Exception:
            pass  # a failed round leaves the last good data in place; the next round tries again
        time.sleep(BACKGROUND_MINUTES * 60)


class Handler(SimpleHTTPRequestHandler):
    def send_body(self, status, body, content_type):
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/data.js":
            data = dict(snapshot.current()[0] or {})
            body = "// Latest snapshot; the app refreshes it in the background.\n" + "".join(
                f"const {name} = {json.dumps(value, ensure_ascii=False)};\n" for name, value in data.items()
            )
            self.send_body(200, body, "text/javascript; charset=utf-8")
            return
        if path == "/api/version":
            _, version = snapshot.current()
            self.send_body(200, json.dumps({"version": version}), "application/json")
            return
        super().do_GET()

    def do_POST(self):
        if self.path == "/api/refresh":
            # Refresh button: gather everything now, then the page reloads.
            try:
                snapshot.refresh()
                self.send_response(204)
            except Exception:
                self.send_response(500)
            self.end_headers()
            return
        # The only thing the page may write: Omkar's own list, to data\my-list.md.
        if self.path != "/api/my-list":
            self.send_error(404)
            return
        try:
            items = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"[]")
            collectors.write_my_list(items)
            self.send_response(204)
        except (ValueError, TypeError, OSError):
            self.send_response(400)
        self.end_headers()

    def end_headers(self):
        # Always serve the latest files; no stale copies after an update.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


def main():
    DATA.mkdir(exist_ok=True)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), partial(Handler, directory=str(WEB)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        threading.Thread(target=keep_fresh, daemon=True).start()
    except OSError:
        pass  # Already open in another window; that one's server serves this window too.
    webview.create_window(
        "Command Centre",
        f"http://127.0.0.1:{PORT}/",
        width=1440,
        height=900,
        min_size=(1024, 700),
        maximized=True,
        background_color="#FCFFFE",
    )
    webview.start(private_mode=False, storage_path=str(DATA / "webview"))


if __name__ == "__main__":
    main()
