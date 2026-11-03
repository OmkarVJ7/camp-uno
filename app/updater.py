"""Keeps the app in step with GitHub: on opening, it fetches the approved version (branch `main`
on github.com/OmkarVJ7/camp-uno) and moves to it if it's newer.

It only ever fast-forwards: it never overwrites local edits, never merges, never pushes.
If anything is off (offline, local edits, a different branch, history that doesn't line up)
it leaves the app exactly as it is and says why. Page changes show after a reload; changes to
the Python files take effect the next time the app is opened.
"""
import subprocess
import threading
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BRANCH = "main"
FETCH_TIMEOUT = 30   # seconds; it runs in the background, so a slow network never delays opening


class Update:
    """What the last check found, for the page to show."""

    def __init__(self):
        self.lock = threading.Lock()
        self.state = {"status": "checking", "note": "", "checkedAt": None, "needsRestart": False}

    def set(self, status, note="", needs_restart=False):
        with self.lock:
            self.state = {"status": status, "note": note, "needsRestart": needs_restart,
                          "checkedAt": datetime.now().isoformat(timespec="seconds")}

    def current(self):
        with self.lock:
            return dict(self.state)


update = Update()


def git(*args, timeout=10):
    # No console window flashes up: the app itself runs without one.
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    out = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True,
                         timeout=timeout, creationflags=flags)
    if out.returncode:
        raise RuntimeError(out.stderr.strip() or f"git {args[0]} failed")
    return out.stdout.strip()


def check():
    """Fetch the approved version and fast-forward to it when that's safe. Never raises."""
    try:
        if not (REPO / ".git").exists():
            return update.set("off", "This copy isn't linked to GitHub.")
        if git("rev-parse", "--abbrev-ref", "HEAD") != BRANCH:
            return update.set("skipped", f"Not on {BRANCH}, so left as it is.")
        if git("status", "--porcelain", "--untracked-files=no"):
            return update.set("skipped", "There are local edits, so left as it is.")
        git("fetch", "--quiet", "origin", BRANCH, timeout=FETCH_TIMEOUT)
        here, there = git("rev-parse", "HEAD"), git("rev-parse", f"origin/{BRANCH}")
        if here == there:
            return update.set("current")
        # Only move forward along the same line of history; anything else needs a person to look.
        try:
            git("merge-base", "--is-ancestor", "HEAD", f"origin/{BRANCH}")
        except RuntimeError:
            return update.set("skipped", "This copy has changes GitHub doesn't, so left as it is.")
        changed = git("diff", "--name-only", "HEAD", f"origin/{BRANCH}").splitlines()
        git("merge", "--ff-only", "--quiet", f"origin/{BRANCH}")
        needs_restart = any(name.endswith(".py") for name in changed)
        update.set("updated", f"{len(changed)} file{'s' if len(changed) != 1 else ''} updated.", needs_restart)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as e:
        # Offline, git missing, or GitHub unreachable: carry on with the version already here.
        update.set("skipped", f"Couldn't reach GitHub ({str(e).splitlines()[0][:80]}).")


def start():
    threading.Thread(target=check, daemon=True).start()
