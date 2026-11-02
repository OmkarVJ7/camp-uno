// Sample data for the mock-ups. Made up for layout only.

// Omkar's work areas and the stages inside each.
const AREAS = {
  bd:        { label: "BD & outreach", short: "BD", color: "#006E4A", stages: ["Leads", "Research", "Outreach", "Follow-up"] },
  deals:     { label: "Deals & onboarding", short: "Deals", color: "#2E6FD8", stages: ["Proposal", "Negotiation", "Legal", "Handover"] },
  product:   { label: "Product & demos", short: "Product", color: "#B45309", stages: ["Custom build", "Collateral", "Deployment"] },
  company:   { label: "Company", short: "Company", color: "#494D4C", stages: ["Pitch deck", "Projections"] },
  marketing: { label: "Marketing", short: "Mktg", color: "#0E5235", stages: ["Campaign", "Collateral", "Posting"] },
  other:     { label: "Other", short: "Other", color: "#686D6C", stages: [] },
};

// Where each item comes from.
const SOURCES = {
  slack:    { label: "Slack", tag: "SLACK", color: "#0E5235", from: "Slack" },
  gmail:    { label: "Gmail", tag: "MAIL", color: "#B42318", from: "Gmail" },
  frappe:   { label: "Frappe CRM", tag: "CRM", color: "#006E4A", from: "Frappe" },
  calendar: { label: "Calendar", tag: "CAL", color: "#2E6FD8", from: "Google Calendar" },
  drive:    { label: "Drive", tag: "DRIVE", color: "#B45309", from: "Google Drive" },
  sheet:    { label: "Content calendar", tag: "SHEET", color: "#686D6C", from: "Google Sheet" },
  local:    { label: "My tasks", tag: "MINE", color: "#0A7E57", from: "Added by you" },
};

const URGENCY = {
  overdue: { label: "Overdue", color: "#B42318" },
  today:   { label: "Today", color: "#006E4A" },
  week:    { label: "This week", color: "#686D6C" },
};

// Listed in the order the "Do next" tile shows them.
const ITEMS = [
  { area: "bd", stage: "Follow-up", src: "frappe", title: "Sample Wealth Partners", sub: "Send MoM and pricing note after demo", when: "2 days late", due: "overdue", done: false },
  { area: "deals", stage: "Proposal", src: "gmail", title: "Proposal: Example Capital Advisors", sub: "Draft waiting since Friday", when: "3 days", due: "overdue", done: false },
  { area: "company", stage: "Projections", src: "slack", title: "Nikhil: pipeline numbers for board update", sub: "#leadership · asked 10:12", when: "Today", due: "today", done: false },
  { area: "bd", stage: "Leads", src: "frappe", title: "Shortlist 10 RIAs in Pune", sub: "From BD digest", when: "Today", due: "today", done: true },
  { area: "bd", stage: "Outreach", src: "calendar", title: "Call with sample advisor", sub: "Discovery call", when: "15:00", due: "today", done: false },
  { area: "product", stage: "Custom build", src: "slack", title: "Custom report for Example Capital", sub: "#product · dev has a question", when: "Today", due: "today", done: false },
  { area: "deals", stage: "Legal", src: "drive", title: "Contract redlines: Illustrative Advisory", sub: "Legal returned comments", when: "Today", due: "today", done: false },
  { area: "bd", stage: "Outreach", src: "frappe", title: "Placeholder Investments", sub: "WhatsApp after email", when: "Today", due: "today", done: false },
  { area: "bd", stage: "Research", src: "drive", title: "Research: Demo Financial Services", sub: "Notes doc before Thursday call", when: "Today", due: "today", done: false },
  { area: "deals", stage: "Handover", src: "slack", title: "Handover to tech: Sample Wealth", sub: "#delivery · onboarding checklist", when: "Wed", due: "week", done: false },
  { area: "product", stage: "Collateral", src: "drive", title: "Demo deck for Illustrative Advisory", sub: "Custom slides for their team", when: "Thu", due: "week", done: false },
  { area: "marketing", stage: "Posting", src: "sheet", title: "Thu · Instagram · Company", sub: "To fill · no file yet", when: "Thu", due: "week", done: false },
  { area: "marketing", stage: "Campaign", src: "gmail", title: "Webinar invite campaign", sub: "Draft reviewed", when: "Today", due: "today", done: true },
  { area: "company", stage: "Pitch deck", src: "drive", title: "Pitch deck v7 review", sub: "Comments from Nikhil", when: "Fri", due: "week", done: false },
  { area: "other", stage: "", src: "calendar", title: "Friday weekly update", sub: "Scheduled reminder", when: "Fri 16:03", due: "week", done: false },
];

const MY_LIST = [
  { text: "Read the partner agreement draft", done: false },
  { text: "Homework: pricing page notes", done: false },
  { text: "Book travel for client visit", done: true },
];

const RUNS = [
  { name: "BD digest", note: "09:13 · sent to Slack", ok: true },
  { name: "Reminders", note: "3 created", ok: true },
  { name: "Weekly update", note: "no summary file found", ok: false },
];

const SCORE = { clients: "00", mrr: "₹0.0L", checked: "6 Nov 2026", mrrUnconfirmed: true };

const GROUPINGS = { area: AREAS, source: SOURCES, urgency: URGENCY };
const GROUP_FIELD = { area: "area", source: "src", urgency: "due" };

function groupItems(mode) {
  const groups = GROUPINGS[mode] || AREAS;
  const field = GROUP_FIELD[mode] || "area";
  return Object.keys(groups).map(k => ({
    key: k,
    label: groups[k].label,
    color: groups[k].color,
    from: mode === "source" ? SOURCES[k].from + " · 08:42" : mode === "area" ? AREAS[k].stages.join(" · ") || "Anything else" : "",
    items: ITEMS.filter(i => i[field] === k),
  }));
}

// The small label shown on each item: whatever the current grouping doesn't already say.
function chip(i, mode) {
  if (mode === "area") return i.stage || SOURCES[i.src].tag;
  if (mode === "source") return AREAS[i.area].short;
  return SOURCES[i.src].tag;
}

// Remembers the chosen grouping between visits.
function getMode() {
  try { return localStorage.getItem("cc-group") || "area"; } catch (e) { return "area"; }
}

// The left nav tells the theme when the grouping changes.
function onGroupChange(fn) {
  window.addEventListener("message", e => { if (e.data && e.data.group) fn(e.data.group); });
}

// The left nav tells the theme the time of day and whether panels should be dark.
function onScene(fn) {
  window.addEventListener("message", e => { if (e.data && e.data.phase) fn(e.data.phase, !!e.data.dark); });
}

function progress() {
  const done = ITEMS.filter(i => i.done).length;
  return { done, total: ITEMS.length, pct: Math.round(100 * done / ITEMS.length) };
}
