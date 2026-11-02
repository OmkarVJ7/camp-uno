"""Command Centre: opens the dashboard in its own window.

Serves the web folder on a fixed local port (so the page's saved settings survive
restarts). The page opens instantly from the last saved snapshot while fresh data
is gathered in the background; Refresh gathers it on the spot.
Everything the app stores stays under D:\\command-centre\\data.
"""
import json
import threading
import time
import urllib.request
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
        self.refreshing = threading.Lock()   # one gathering round at a time (background or Refresh button)
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
        # If a round is already running, wait for it rather than gathering twice at once;
        # the caller then gets that round's (fresh) result.
        with self.refreshing:
            data = collectors.collect()
            with self.lock:
                self.version += 1
                data["META"]["version"] = self.version
                self.data = data
            self.ready.set()
            collectors.write_atomic(SNAPSHOT, json.dumps(data, ensure_ascii=False))

    def current(self):
        """The latest data, or a complete empty set if nothing could be gathered yet."""
        self.ready.wait(timeout=30)
        with self.lock:
            data = self.data or collectors.empty("Still gathering the first data. Press Refresh in a moment.")
            return data, self.version


snapshot = Snapshot()


def keep_fresh():
    while True:
        try:
            snapshot.refresh()
        except Exception:
            pass  # a failed round leaves the last good data in place; the next round tries again
        time.sleep(BACKGROUND_MINUTES * 60)


class Handler(SimpleHTTPRequestHandler):
    def allowed(self):
        """Answer only the app's own page. A website open in another browser could otherwise read
        data.js or post to the API (it would send a different Sec-Fetch-Site), and a DNS trick
        would arrive with a different Host."""
        host_ok = self.headers.get("Host") in (f"127.0.0.1:{PORT}", f"localhost:{PORT}")
        return host_ok and self.headers.get("Sec-Fetch-Site") in (None, "same-origin", "none")

    def send_body(self, status, body, content_type):
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if not self.allowed():
            self.send_error(403)
            return
        path = self.path.split("?")[0]
        if path == "/data.js":
            data = snapshot.current()[0]
            body = "// Latest snapshot; the app refreshes it in the background.\n" + "".join(
                f"const {name} = {json.dumps(value, ensure_ascii=False)};\n" for name, value in data.items()
            )
            self.send_body(200, body, "text/javascript; charset=utf-8")
            return
        if path == "/api/version":
            _, version = snapshot.current()
            self.send_body(200, json.dumps({"version": version}), "application/json")
            return
        if path == "/api/feedback":
            self.send_body(200, json.dumps({"count": collectors.feedback_count()}), "application/json")
            return
        super().do_GET()

    def do_POST(self):
        # A JSON body can't be sent cross-site without the browser asking first, which we never answer.
        if not self.allowed() or not self.headers.get("Content-Type", "").startswith("application/json"):
            self.send_error(403)
            return
        if self.path == "/api/refresh":
            # Refresh button: gather everything now, then the page reloads.
            try:
                snapshot.refresh()
                self.send_response(204)
            except Exception:
                self.send_response(500)
            self.end_headers()
            return
        if self.path == "/api/feedback":
            # A note from the test run, appended to data\feedback.md.
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                collectors.add_feedback(body.get("text", ""))
                self.send_body(200, json.dumps({"count": collectors.feedback_count()}), "application/json")
            except (ValueError, TypeError, AttributeError, OSError):
                self.send_response(400)
                self.end_headers()
            return
        # The other thing the page may write: Omkar's own list, to data\my-list.md.
        if self.path != "/api/my-list":
            self.send_error(404)
            return
        try:
            items = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"[]")
            collectors.write_my_list(items)
            self.send_response(204)
        except (ValueError, TypeError, AttributeError, OSError):
            self.send_response(400)
        self.end_headers()

    def end_headers(self):
        # Always serve the latest files; no stale copies after an update.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


def already_running():
    """True if the port is held by another Command Centre (it answers /api/version), not some other program."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/version", timeout=2) as r:
            return "version" in json.loads(r.read())
    except (OSError, ValueError):
        return False


ICON = ROOT / "command-centre.ico"


def use_brand_icon(window):
    """Windows gives the window Python's icon; swap in the Spring Money mark once it's shown.
    Purely cosmetic, so any problem here is ignored."""
    try:
        from System import Action
        from System.Drawing import Icon
        form = window.native
        form.Invoke(Action(lambda: setattr(form, "Icon", Icon(str(ICON)))))
    except Exception:
        pass


PORT_TAKEN = f"""<body style="font-family:Segoe UI,sans-serif;padding:40px;color:#272B2A;background:#FCFFFE">
<h2>Command Centre can't start</h2>
<p>Another program on this PC is using port {PORT}, which the Command Centre needs.</p>
<p>Close that program (or restart the PC) and open the Command Centre again.</p></body>"""


def main():
    DATA.mkdir(exist_ok=True)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), partial(Handler, directory=str(WEB)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        threading.Thread(target=keep_fresh, daemon=True).start()
    except OSError:
        # Port taken. If it's another Command Centre window, share its server; otherwise say so plainly.
        if not already_running():
            webview.create_window("Command Centre", html=PORT_TAKEN, width=640, height=320)
            webview.start()
            return
    window = webview.create_window(
        "Command Centre",
        f"http://127.0.0.1:{PORT}/",
        width=1440,
        height=900,
        min_size=(1024, 700),
        maximized=True,
        background_color="#FCFFFE",
    )
    window.events.shown += lambda: use_brand_icon(window)
    webview.start(private_mode=False, storage_path=str(DATA / "webview"))


if __name__ == "__main__":
    main()
