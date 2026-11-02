"""Gathers everything the page shows, fresh on every load.

Each source reports its own status and last-refreshed time, so the page can say
"not connected", "stale" or when it was last updated. Nothing here invents data:
a source that isn't connected yet returns no items. Everything is read-only.
"""
import json
import re
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
CACHE = DATA / "cache"
MY_LIST_FILE = DATA / "my-list.md"
REVENUE_FILE = Path(r"H:\My Drive\SpringMoney\00-Knowledge\clients-and-revenue.md")
STALE_AFTER_DAYS = 14   # the scoreboard counts as stale if "Last checked" is older than this

# Shown in the left nav, in this order.
SOURCES = [
    ("slack", "Slack"),
    ("frappe", "Frappe CRM"),
    ("gmail", "Gmail"),
    ("calendar", "Google Calendar"),
    ("drive", "Google Drive"),
    ("sheet", "Content calendar"),
    ("scoreboard", "Scoreboard"),
]

# ---------- Frappe ----------

FRAPPE = "https://springmoneyoffice.m.frappe.cloud"
KEYRING_SERVICE = "frappe-springmoney"

# Pipeline stage -> (work area, stage label, priority). A lower priority is closer to a deal
# and goes earlier on the track. Stages not listed here are skipped as dead.
STAGES = {
    "Negotiation":    ("deals", "Negotiation", 1),
    "Proposal Sent":  ("deals", "Proposal", 2),
    "Demo Done":      ("deals", "Proposal", 3),
    "Customer":       ("deals", "Handover", 4),
    "Meeting Booked": ("bd", "Outreach", 5),
    "Replied":        ("bd", "Follow-up", 6),
    "Nurture":        ("bd", "Follow-up", 7),
    "In Sequence":    ("bd", "Outreach", 8),
    "Not Now":        ("bd", "Follow-up", 9),
    "Not Contacted":  ("bd", "Leads", 10),
    "":               ("bd", "Leads", 10),
}
DEAD_STAGES = ["Closed-lost", "Bounced", "Churned"]   # the stages in Frappe today that STAGES leaves out
BACKLOG_DAYS = 30   # overdue by more than this counts as backlog, not today's work
LEAD_FIELDS = ["name", "company_name", "lead_name", "custom_contact_person", "custom_pipeline_stage",
               "custom_next_followup_date", "custom_next_action_note"]


def frappe_get(path, params, timeout=5):
    import keyring
    key = keyring.get_password(KEYRING_SERVICE, "api_key")
    secret = keyring.get_password(KEYRING_SERVICE, "api_secret")
    if not (key and secret):
        raise RuntimeError("Frappe key not found in the Windows key store")
    req = urllib.request.Request(FRAPPE + path + "?" + urllib.parse.urlencode(params))
    req.add_header("Authorization", f"token {key}:{secret}")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["data"]


def fetch_leads(today):
    """Leads with a follow-up due within the next 7 days, overdue ones included."""
    week = (today + timedelta(days=7)).isoformat()
    return frappe_get("/api/resource/Lead", {
        "fields": json.dumps(LEAD_FIELDS),
        "filters": json.dumps([["custom_next_followup_date", "is", "set"], ["custom_next_followup_date", "<=", week]]),
        "order_by": "custom_next_followup_date asc",
        "limit_page_length": 2000,
    })


def lead_item(lead, today):
    area, stage, priority = STAGES[lead["custom_pipeline_stage"] or ""]
    due_on = date.fromisoformat(lead["custom_next_followup_date"])
    late = (today - due_on).days
    if late > 0:
        due, when = "overdue", f"{plural(late, 'day')} late"
    elif late == 0:
        due, when = "today", "Today"
    else:
        due, when = "week", f"{due_on:%a} {due_on.day} {due_on:%b}"
    contact = lead["custom_contact_person"] or lead["lead_name"] or ""
    title = lead["company_name"] or lead["lead_name"] or lead["name"]
    what = lead["custom_next_action_note"] or f"Follow up · {lead['custom_pipeline_stage'] or 'no stage'}"
    return {
        "id": lead["name"],
        "stamp": lead["custom_next_followup_date"],   # a "done" mark only holds for this follow-up date
        "area": area,
        "stage": stage,
        "src": "frappe",
        "title": title,
        "sub": what + (f" · {contact}" if contact and contact != title else ""),
        "when": when,
        "due": due,
        "late": max(late, 0),
        "priority": priority,
        "done": False,
        "url": f"{FRAPPE}/app/lead/{urllib.parse.quote(lead['name'])}",
    }


def frappe_items(today):
    """Today's Frappe work, plus backlog counts per area. Falls back to the last saved copy offline."""
    cache = CACHE / "frappe.json"
    try:
        leads = fetch_leads(today)
        fetched_at = datetime.now().isoformat(timespec="seconds")
        write_atomic(cache, json.dumps({"fetchedAt": fetched_at, "leads": leads}))
        status = "ok"
    except Exception as e:  # offline, Frappe down, or key missing
        try:
            saved = json.loads(cache.read_text(encoding="utf-8"))
            leads, fetched_at, status = saved["leads"], saved["fetchedAt"], "stale"
        except (OSError, ValueError, KeyError):
            return [], {}, {"status": "error", "refreshedAt": None, "note": str(e)[:120]}

    items, backlog, skipped = [], {}, 0
    for lead in leads:
        if (lead.get("custom_pipeline_stage") or "") not in STAGES:
            continue
        try:
            item = lead_item(lead, today)
        except (ValueError, KeyError, TypeError):  # one odd record (say, an impossible date) mustn't hide the rest
            skipped += 1
            continue
        if item["late"] > BACKLOG_DAYS:
            backlog[item["area"]] = backlog.get(item["area"], 0) + 1
            continue
        items.append(item)

    result = {"status": status, "refreshedAt": fetched_at}
    if skipped:
        result["note"] = f"{plural(skipped, 'lead')} couldn't be read and {'was' if skipped == 1 else 'were'} left out"
    return items, backlog, result


# ---------- Feeds written by scheduled Claude tasks (Slack first) ----------

FEEDS = DATA / "feeds"
FEED_STALE_HOURS = 12   # a feed older than this shows as stale (runs are ~3 times a working day)
# Where feed items sit in the track order, next to the Frappe stage priorities above (1 = Negotiation).
FEED_PRIORITY = {"reply": 1.5, "rsvp": 1.6, "draft": 2.5, "post": 6, "event": 12, "fyi": 12}
# Only urgent invites and posts jump the queue: an invite more than a day out, or a post on a later day, waits.
LATER_PRIORITY = {"rsvp": 7, "post": 8}
FEED_STAGE = {"reply": "Reply", "rsvp": "RSVP", "draft": "Draft", "event": "Meeting", "fyi": "FYI"}


def plural(n, word):
    return f"{n} {word}{'s' if n != 1 else ''}"


def local_time(text):
    """An ISO time as local wall-clock time. Times with an offset (+05:30, or Z for UTC) are converted,
    not just stripped, so a UTC time doesn't read 5.5 hours early."""
    t = datetime.fromisoformat(text)
    return t.astimezone().replace(tzinfo=None) if t.tzinfo else t


def write_atomic(path, text):
    """Write via a temporary file, so a reader never sees half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def feed_item(raw, src, now):
    """A feed entry becomes a track item. Each kind has its own idea of today and overdue:
    replies and drafts age from when they arrived; invites and meetings count to their start;
    posts count to their planned date. Returns None for things already over."""
    kind = raw.get("kind", "reply")
    today = now.date()
    late, stage = 0, FEED_STAGE.get(kind, "")
    if kind in ("reply", "draft"):
        received = local_time(raw["receivedAt"])
        age = (today - received.date()).days
        if kind == "draft":
            due, when = ("today", "Draft · today") if age == 0 else ("overdue", f"Draft · {plural(age, 'day')} old")
        else:
            due, when = ("today", f"Today {received:%H:%M}") if age == 0 else ("overdue", f"{plural(age, 'day')} waiting")
        late = age
    elif kind in ("rsvp", "event"):
        at = local_time(raw["eventAt"])
        if at < now:
            return None
        days = (at.date() - today).days
        label = "Today" if days == 0 else "Tomorrow" if days == 1 else f"{at:%a} {at.day} {at:%b}"
        when = f"{'RSVP · ' if kind == 'rsvp' else ''}{label} {at:%H:%M}"
        # An invite needs answering soon if the meeting is within a day; a meeting only counts on its day.
        due = "today" if days == 0 or (kind == "rsvp" and days <= 1) else "week"
    elif kind == "post":
        status = raw.get("status", "")
        if status.lower().startswith("published"):
            return None
        on = date.fromisoformat(raw["dueOn"])
        days = (on - today).days
        stage = "To fill" if status.lower().startswith("to fill") else "Posting"
        if days < 0:
            due, when, late = "overdue", f"Post · {plural(-days, 'day')} late", -days
        else:
            due = "today" if days == 0 else "week"
            when = "Post today" if days == 0 else f"Post {on:%a} {on.day} {on:%b}"
        if stage == "To fill":
            when = when.replace("Post", "Fill")
    else:  # fyi
        received = local_time(raw["receivedAt"])
        due, when = "week", f"FYI · {received.day} {received:%b}"
    return {
        # A "done" mark only holds for this version of the item (the same message, invite time or post date).
        "id": raw["id"], "stamp": raw.get("receivedAt") or raw.get("eventAt") or raw.get("dueOn") or "",
        "area": raw.get("area", "other"), "stage": raw.get("stage", stage),
        "src": src, "title": raw["title"], "sub": raw.get("sub", ""), "when": when, "due": due,
        "late": late, "done": False, "url": raw.get("url"),
        "priority": LATER_PRIORITY[kind] if kind in LATER_PRIORITY and due == "week" else
                    2.6 if kind == "post" else FEED_PRIORITY.get(kind, 12),
    }


def read_feed(src, now):
    """Items and run reports from data\\feeds\\<src>.json, with the feed's own freshness."""
    path = FEEDS / f"{src}.json"
    if not path.exists():
        return [], [], not_connected()
    try:
        feed = json.loads(path.read_text(encoding="utf-8"))
        made = local_time(feed["generatedAt"])
    except (OSError, ValueError, KeyError, TypeError) as e:
        return [], [], {"status": "error", "refreshedAt": None, "note": f"{src}.json couldn't be read: {e}"[:120]}
    # One odd entry is skipped and reported; the rest of the feed still shows.
    items, skipped = [], 0
    for raw in feed.get("items", []):
        try:
            item = feed_item(raw, src, now)
        except (ValueError, KeyError, TypeError, AttributeError):
            skipped += 1
            continue
        if item:
            items.append(item)
    stale = now - made > timedelta(hours=FEED_STALE_HOURS)
    result = {"status": "stale" if stale else "ok", "refreshedAt": made.isoformat(timespec="seconds")}
    if skipped:
        result["note"] = f"{skipped} {'entry was' if skipped == 1 else 'entries were'} left out because they couldn't be read"
    return items, feed.get("runs", []), result


# ---------- Scoreboard (clients-and-revenue.md) ----------

CHECK = re.compile(r"\[CHECK[^\]]*\]")


def table_rows(text, first_header):
    """Rows of the Markdown table whose first header cell is `first_header`, as dicts."""
    lines = [l.strip() for l in text.splitlines()]
    start = next(i for i, l in enumerate(lines) if l.startswith("|") and l.strip("| ").startswith(first_header))
    headers = [c.strip() for c in lines[start].strip("|").split("|")]
    rows = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        rows.append(dict(zip(headers, (c.strip() for c in line.strip("|").split("|")))))
    return rows


def scoreboard():
    """Paying clients and MRR as the file states them. Anything marked [CHECK] is flagged as unconfirmed."""
    if not REVENUE_FILE.exists():
        return None, {"status": "error", "refreshedAt": None, "note": "clients-and-revenue.md not found on H:"}
    text = REVENUE_FILE.read_text(encoding="utf-8")
    modified = datetime.fromtimestamp(REVENUE_FILE.stat().st_mtime).isoformat(timespec="seconds")

    mrr_line = re.search(r"\*\*Total MRR:\*\*\s*(.+)", text)
    mrr_text = mrr_line.group(1).strip() if mrr_line else ""
    mrr = re.search(r"₹[\d,\.]+\s*(?:L|lakh|Cr|crore)?", mrr_text)
    checked = re.search(r"\*\*Last checked:\*\*\s*(\d{4}-\d{2}-\d{2})", text)
    checked_on = date.fromisoformat(checked.group(1)) if checked else None

    # Group clients by status, keeping whether each status is confirmed.
    groups = {}
    for row in table_rows(text, "Client"):
        raw = row.get("Status", "")
        status = CHECK.sub("", raw).strip() or "Unknown"
        g = groups.setdefault(status, {"status": status, "count": 0, "unconfirmed": 0, "names": []})
        g["count"] += 1
        g["unconfirmed"] += bool(CHECK.search(raw))
        g["names"].append(row.get("Client", "").split(" (")[0])
    paying = groups.get("Paying", {"count": 0, "unconfirmed": 0})

    score = {
        "clients": paying["count"],
        "clientsUnconfirmed": paying["unconfirmed"] > 0,
        "mrr": mrr.group(0).strip() if mrr else None,
        "mrrUnconfirmed": bool(CHECK.search(mrr_text)) or not mrr,
        "mrrNote": CHECK.sub("", mrr_text).replace(mrr.group(0), "").strip(" ,") if mrr else "",
        "checked": f"{checked_on.day} {checked_on:%b %Y}" if checked_on else None,
        "groups": list(groups.values()),
        "file": str(REVENUE_FILE),
    }
    stale = not checked_on or (date.today() - checked_on).days > STALE_AFTER_DAYS
    return score, {"status": "stale" if stale else "ok", "refreshedAt": modified}


# ---------- My list (a plain Markdown checklist Omkar owns) ----------

ITEM_LINE = re.compile(r"^\s*[-*]\s*\[( |x|X)\]\s*(.+?)\s*$")


def read_my_list():
    if not MY_LIST_FILE.exists():
        return []
    return [{"text": m.group(2), "done": m.group(1).lower() == "x"}
            for m in map(ITEM_LINE.match, MY_LIST_FILE.read_text(encoding="utf-8").splitlines()) if m]


def write_my_list(items):
    """Saves the list as a checklist anyone can open in Notepad. Each task stays on one line."""
    if not isinstance(items, list):
        raise ValueError("expected a list of tasks")
    lines = ["# My list", "", "_Personal tasks and homework. Edit here or in the Command Centre._", ""]
    for i in items:
        text = " ".join(str(i.get("text", "")).split()) if isinstance(i, dict) else ""
        if text:
            lines.append(f"- [{'x' if i.get('done') else ' '}] {text}")
    write_atomic(MY_LIST_FILE, "\n".join(lines) + "\n")


def frappe_rules():
    """The sorting rules above, in a form the page can show as-is."""
    areas = {}
    for stage, (area, label, priority) in sorted(STAGES.items(), key=lambda s: s[1][2]):
        if stage:
            areas.setdefault(area, []).append({"stage": stage, "label": label})
    return {
        "areas": areas,
        "order": [s for s, _ in sorted(STAGES.items(), key=lambda s: s[1][2]) if s],
        "skipped": DEAD_STAGES,
        "backlogDays": BACKLOG_DAYS,
        "window": "due in the next 7 days, or overdue",
        "feeds": [
            "Slack messages waiting on your reply, and meeting invites you haven't answered (for meetings within a day), "
            "go on the track right after Negotiation leads.",
            "Gmail drafts waiting to be sent come next, after Proposal Sent leads, followed by posts due today or late. "
            "A draft older than a day counts as overdue.",
            "Content calendar posts count to their planned date; published ones drop off, and 'To fill' rows show as Fill. "
            "Later posts, and invites more than a day away, wait after the Frappe follow-ups.",
            "Meetings you've accepted and things only worth a look (Drive files, FYI messages) go last.",
            "Each item sits in the building for its work area; Claude picks the area when it reads the source.",
        ],
    }


# ---------- Everything ----------

def not_connected():
    return {"status": "not_connected", "refreshedAt": None}


def empty(note):
    """A complete but empty data set, so the page can show 'no data yet' instead of breaking."""
    return {
        "ITEMS": [],
        "BACKLOG": {"counts": {}, "days": BACKLOG_DAYS, "url": f"{FRAPPE}/app/lead"},
        "RULES": frappe_rules(),
        "MY_LIST": [],
        "RUNS": [],
        "SCORE": None,
        "META": {
            "refreshedAt": None,
            "sources": [{"key": key, "label": label, "status": "error", "refreshedAt": None, "note": note}
                        for key, label in SOURCES],
        },
    }


def collect():
    today, now = date.today(), datetime.now()
    status = {key: not_connected() for key, _ in SOURCES}
    items, backlog, status["frappe"] = frappe_items(today)
    runs = []
    for src in ("slack", "gmail", "calendar", "drive", "sheet"):
        feed_items, feed_runs, status[src] = read_feed(src, now)
        items += feed_items
        runs += feed_runs

    # Most important first (closest to a deal, or someone waiting on you), then most overdue.
    # The page fills today's track in this order, up to the day size chosen in the nav.
    items.sort(key=lambda i: (i["priority"], -i["late"]))

    try:
        score, status["scoreboard"] = scoreboard()
    except Exception as e:  # the file changed shape; show the problem rather than break the page
        score, status["scoreboard"] = None, {"status": "error", "refreshedAt": None, "note": str(e)[:120]}
    return {
        "ITEMS": items,
        "BACKLOG": {
            "counts": backlog,
            "days": BACKLOG_DAYS,
            "url": f"{FRAPPE}/app/lead?custom_next_followup_date=" + urllib.parse.quote(
                json.dumps(["<", (today - timedelta(days=BACKLOG_DAYS)).isoformat()])),
        },
        "RULES": frappe_rules(),
        "MY_LIST": read_my_list(),
        "RUNS": runs,
        "SCORE": score,
        "META": {
            "refreshedAt": datetime.now().isoformat(timespec="seconds"),
            "sources": [{"key": key, "label": label, **status[key]} for key, label in SOURCES],
        },
    }
