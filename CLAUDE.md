# Command Centre

Owner: Omkar Jadhav (COO, Spring Money). Not an engineer: explain in plain words, one step at a time. Read `BRIEF.md` in this folder before anything else.

## What this is
A local desktop dashboard on Omkar's Windows PC: one beautiful screen that shows what needs his attention today across Spring Money, so he stops switching between Slack, Gmail, Frappe, Calendar, Drive and Claude sessions. It replaces the "office" view Munder Difflin gave him, without its agents.

## Definition of done (v1)
- Opens with one click (desktop shortcut) and loads in under 3 seconds.
- Shows the v1 panels in `BRIEF.md`, each with real data or a clear "no data yet" state. Never invented numbers.
- Every item links straight to where Omkar acts on it (Gmail draft, Frappe lead, Slack message, sheet row, file on E:).
- Looks designed, not like a default dashboard: Spring Money brand (use the spring-money-brand skill), light by default, calm, readable at a glance.
- Works with no internet for already-loaded data, and says when data is stale (with the time it was last refreshed).
- Omkar has used it for two working days and signed off.

## Rules
- Read-only in v1. The app shows and links; it never sends, posts, edits CRM records or deletes anything.
- No credentials in code or in synced folders. Reuse the Frappe key from the Windows keyring (service `frappe-springmoney`), as `C:\Users\Vismi\claude-connectors\frappe_mcp.py` does.
- Everything lives on D: (`D:\command-centre`): code, the Python environment (`.venv`), and app data (`data\`). Never install packages or write app data to C:, which is short on space. Keep dependencies small.
- Layout: `app\` is the real app (`main.py` window + local server, `collectors.py` data, `web\` The Base page). `design-options\` holds the earlier mock-ups for reference only.
- Build in small steps; show Omkar a screenshot after each visible change.
- Code lives in the private GitHub repo `OmkarVJ7/camp-uno` (branch `main`). Commit each finished change and push it. Never commit `data/` or `.venv/`.
- Omkar is learning as we go: when a technical term comes up, add a one-line plain-words explanation.
