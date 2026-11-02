# camp-uno · Command Centre

One calm screen for Omkar's day across Spring Money. It opens from a desktop shortcut into **The Base**: an isometric village where each work area is a building and today's tasks form a numbered track from Start (09:00) to Finish (17:00 review).

It replaces switching between Slack, Gmail, Frappe, Calendar, Drive and Claude sessions just to see what needs attention. It is **read-only**: it shows and links, and never sends, posts, edits CRM records or deletes anything.

## What you see

- **The track:** everything due today or overdue, most important first (deals closest to closing, then people waiting on a reply). A light day makes a short track, a heavy day packs the squares closer. "Today's track" in the menu can cap it at 10, 15 or 20.
- **Buildings:** one per work area (BD & outreach, Deals & onboarding, Product & demos, Company, Marketing, Other). Taller means more open work. A protest crowd gathers where something is overdue.
- **Your move:** the next square, bottom left, with a button that opens it where you act on it.
- **Scoreboard:** paying clients and MRR as `clients-and-revenue.md` states them; anything marked [CHECK] shows as unconfirmed.
- **Notice board:** your own list, saved as a plain checklist you can also edit in Notepad.
- **Night watch:** whether the morning brief, BD digest and end-of-day wrap arrived.
- **The ⓘ next to "Group by"** shows the live sorting rules.

Light by default; Auto appearance follows the clock from morning to night.

## Where the data comes from

| Source | How | Refreshed |
|---|---|---|
| Frappe CRM (follow-ups) | Read directly with the key in the Windows key store | On open, every 15 min, and on Refresh |
| Scoreboard | `H:\My Drive\SpringMoney\00-Knowledge\clients-and-revenue.md` | Same |
| My list | `data\my-list.md` (the only file the app writes) | Instantly |
| Slack | Scheduled Claude task `command-centre-slack-feed` → `data\feeds\slack.json` | Weekdays 09:30, 13:30, 17:30 |
| Gmail drafts, Calendar, Drive, content calendar | Scheduled Claude task `command-centre-google-feed` → `data\feeds\*.json` | Weekdays 09:35, 13:35, 17:35 |

The scheduled tasks only run while the Claude desktop app is open. Each source shows its own "updated" time in the menu, and an amber warning appears at the top when one is out of date.

## Running it

Double-click **Command Centre** on the desktop. Behind the shortcut:

```
D:\command-centre\.venv\Scripts\pythonw.exe D:\command-centre\app\main.py
```

First-time setup on a new PC: create the environment with `python -m venv .venv`, then `.venv\Scripts\python -m pip install pywebview keyring`, and store the Frappe key in the Windows key store under service `frappe-springmoney` (accounts `api_key` and `api_secret`).

## Folders

```
app/
  main.py          window, local server, background refresh
  collectors.py    reads Frappe, the scoreboard file, my list and the feeds; sorting rules live here
  web/             The Base page, the menu, fonts and brand files
design-options/    earlier design mock-ups with sample data (four themes), for reference
data/              your list, feeds and saved copies; stays on this PC, never uploaded
```

## Privacy

No keys or passwords are stored in this repository. `data/` (your list, the Slack and Google feeds, cached Frappe data) and the Python environment are excluded by `.gitignore`. The local server only answers the app's own page.
