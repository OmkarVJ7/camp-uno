// Fixed lookups and helpers shared by the page. The live data (ITEMS, MY_LIST, RUNS, SCORE, META)
// comes from data.js, which the app builds fresh on every load.

// Text from Slack, Gmail, Frappe and files is shown as text, never run as code.
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
// Links only open if they are normal web addresses.
function safeUrl(u) {
  return /^https?:\/\//i.test(u || "") ? esc(u) : "#";
}
// Run once after data.js loads: escapes every piece of incoming text in place. MY_LIST stays raw
// (it is saved back to its file) and is escaped where it is shown.
function cleanData() {
  const clean = (v, key) => {
    if (typeof v === "string") return key === "url" ? safeUrl(v) : esc(v);
    if (Array.isArray(v)) { v.forEach((x, i) => v[i] = clean(x, key)); return v; }
    if (v && typeof v === "object") { for (const k of Object.keys(v)) v[k] = clean(v[k], k); }
    return v;
  };
  [ITEMS, RUNS, SCORE, META, typeof RULES === "undefined" ? null : RULES].forEach(d => clean(d));
  if (typeof BACKLOG !== "undefined") BACKLOG.url = safeUrl(BACKLOG.url);
}

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

// The "Channel" grouping clubs related sources together.
const CHANNELS = {
  communication: { label: "Communication", color: "#0E5235", sources: ["slack", "gmail"] },
  calendar:      { label: "Calendar", color: "#2E6FD8", sources: ["calendar"] },
  documents:     { label: "Documents", color: "#B45309", sources: ["drive", "sheet"] },
  crm:           { label: "CRM", color: "#006E4A", sources: ["frappe"] },
  local:         { label: "My tasks", color: "#0A7E57", sources: ["local"] },
};
const CHANNEL_OF = Object.fromEntries(Object.entries(CHANNELS).flatMap(([k, c]) => c.sources.map(s => [s, k])));

// "source" is kept as the setting's name so earlier saved choices still work; it shows as "Channel".
const GROUPINGS = { area: AREAS, source: CHANNELS, urgency: URGENCY };
const GROUP_OF = { area: i => i.area, source: i => CHANNEL_OF[i.src], urgency: i => i.due };

function groupItems(mode) {
  const groups = GROUPINGS[mode] || AREAS;
  const of = GROUP_OF[mode] || GROUP_OF.area;
  return Object.keys(groups).map(k => ({
    key: k,
    label: groups[k].label,
    color: groups[k].color,
    from: mode === "source" ? CHANNELS[k].sources.map(s => SOURCES[s].label).join(" · ") : mode === "area" ? AREAS[k].stages.join(" · ") || "Anything else" : "",
    items: ITEMS.filter(i => of(i) === k),
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

// The left nav tells the page when the grouping changes.
function onGroupChange(fn) {
  window.addEventListener("message", e => { if (e.data && e.data.group) fn(e.data.group); });
}

// How many squares today's track holds: "auto" (everything due today) or a number.
function getDaySize() {
  try { return localStorage.getItem("cc-day") || "auto"; } catch (e) { return "auto"; }
}
function onDaySize(fn) {
  window.addEventListener("message", e => { if (e.data && e.data.day) fn(e.data.day); });
}

// The left nav tells the page the time of day and whether panels should be dark.
function onScene(fn) {
  window.addEventListener("message", e => { if (e.data && e.data.phase) fn(e.data.phase, !!e.data.dark); });
}

function progress() {
  const done = ITEMS.filter(i => i.done).length;
  return { done, total: ITEMS.length, pct: ITEMS.length ? Math.round(100 * done / ITEMS.length) : 0 };
}

// "21:05" from an ISO time, or "never".
function hhmm(iso) {
  if (!iso) return "never";
  const d = new Date(iso);
  return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}
