# Command Centre: brief

_Written 2 Nov 2026 from the Claude setup and migration conversation. Milestone: build v1 in the week of 9 Nov 2026._

## Why
Omkar runs business development solo and works across many places. Each morning he gets a BD digest (09:13) and a check-in (09:55) in his Slack DM, an end-of-day wrap (16:55), and works through a 5–7 pm review block. Drafts sit in Gmail, leads in Frappe, posts in a Google Sheet, videos on E:, decisions with Alfred. He wants **one screen** for all of it, designed to be a pleasure to open.

## How Omkar's setup works now (context for building)
| Area | Where it runs | What it produces |
|---|---|---|
| BD & Outreach | Claude Code cloud session ("Spring Money Sales Outreach") | Gmail drafts, Frappe updates, Slack send lists, 09:13 digest, one-off reminders, Friday 16:03 weekly update draft for Nikhil |
| Check-in and wrap | Claude in Slack (Omkar's DM) | 09:55 check-in (scoreboard, the hard thing, top 3) and 16:55 wrap |
| Founder's Office (Alfred) | Claude project | `07-Founder/bruce-log.md`, `00-Knowledge/decisions.md`, `00-Knowledge/clients-and-revenue.md` |
| Videos and social | Claude Code on this PC, `E:\Spring Money Product Videos` | Renders, `LATEST.md`, weekly social post packs in `scripts/social/` |
| Content calendar | Google Sheet "Spring Money · Content calendar (Nov 2026 – Mar 2027)" (id `1iHhAOqWoqefJgybh3jXClyjgHGbjoQLbSN9LA4Dzra8`), with Account, Published date and Link columns | |
| Deals, company | Claude projects (Deals & Onboarding, Spring Money Company) | Conversation only |
| CRM | Frappe, `https://springmoneyoffice.m.frappe.cloud`, doctype Lead; fields `custom_next_followup_date`, `custom_next_action_note`, `custom_last_activity_date` | |
| Calendar | Google Calendar (omkar@spring.money) | 5–7 pm daily review block |

Shared knowledge lives in Google Drive `SpringMoney/` (synced to `H:\My Drive\SpringMoney\` on this PC).

## v1 panels
1. **Today's follow-ups**: Frappe leads with next follow-up date on or before today, with firm, contact, what's due, and a link to the lead.
2. **Drafts waiting for me**: Gmail drafts from the outreach work, with subject, recipient and age.
3. **Reminders**: today's and the next 7 days' reminders (from Frappe dates and the scheduled reminders list).
4. **Social this week**: rows from the content calendar for this week, with status (to fill / ready / published) and the file path.
5. **Scoreboard**: paying clients and MRR from `clients-and-revenue.md`, with its "last checked" date; anything marked [CHECK] shown as unconfirmed.
6. **Personal homework and other tasks**: a simple list Omkar can add to and tick off. Stored locally in a plain file he owns.
7. **Last night's runs**: what each scheduled job did (digest, weekly update, reminders), as far as it can be seen.

Each panel shows when it was last refreshed.

## Suggested architecture (to confirm with Omkar before building)
- Prefer reading from sources that already exist: Frappe API (keyring credentials), Google Drive files under `H:\My Drive\SpringMoney\` (local sync), the content calendar sheet.
- For things only Claude sessions know (digest output, run results), a simple pattern: scheduled jobs also write a small summary file into `H:\My Drive\SpringMoney\00-Knowledge\command-centre\` and the app reads that folder.
- Gmail drafts and Calendar may need a Google sign-in for the app; if that's heavy for v1, show links instead and add live data in v2.
- A small local web app opened in its own window is likely enough; Omkar decides on looks from 2–3 design options shown as screenshots.

## Out of scope for v1
Sending, posting or editing anything; mobile; multi-user access; replacing Slack.

## Open items
1. Where the code lives: a private GitHub repo (Spring-money org access is being sorted on 10 Nov), or local only for v1.
2. Folder location: `C:\Users\Vismi\command-centre` suggested (small app; C: is short on space).
3. Design direction: Omkar picks from 2–3 options.
4. Gmail and Calendar live data in v1, or links only.
