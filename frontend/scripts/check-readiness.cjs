// Readiness checks: render the real dashboard against synthetic states. Run from frontend/:
//   npm run check:readiness
const fs = require("fs");
const { renderApp } = require("./render-app.cjs");

const base = JSON.parse(fs.readFileSync("src/fixtures/state.json", "utf8"));
const rows = [];
const render = (state, error = null) => renderApp({ state, error });

function check(name, fn) {
  try {
    if (!fn()) throw Error("Expected text was absent");
    rows.push([name, "PASS"]);
  } catch (e) {
    rows.push([name, "FAIL", e.message]);
  }
}

check("Prototype identity visible", () => render(base).includes("Prototype · not a city service"));
check("Loading state visible", () => render(null).includes("Loading"));
check("Backend outage banner visible", () => render(null, "synthetic offline").includes("Backend unreachable"));

const empty = { ...base, incidents: [], critical_alerts: [], supervisor_queue: [], alerts: [], departments: [] };
check("Empty queue message visible", () => render(empty).includes("No open incidents"));
check("Department alert rendered", () => render(base).includes("accepted 0 of 12"));

const critical = {
  ...base,
  supervisor_queue: [],
  alerts: [],
  critical_alerts: [{
    incident_id: 1, title: "CRITICAL CASE", quote: "UNIQUE CRITICAL EVIDENCE", reason: "REQUIRES REVIEW",
    evidence: ["callback:1"], since: base.now, accepted: true, owner: "Demo operator",
  }],
  incidents: base.incidents.map((i) => ({ ...i, accepted: true, critical: true, why: "Accepted by Demo operator" })),
};
check("Accepted critical alert evidence remains visible outside top ten", () => render(critical).includes("UNIQUE CRITICAL EVIDENCE"));

const many = {
  ...critical,
  critical_alerts: Array.from({ length: 12 }, (_, n) => ({ ...critical.critical_alerts[0], incident_id: n + 1, quote: `PINNED-EVIDENCE-${n + 1}-END` })),
};
check("All twelve critical alerts render beyond the queue cap", () => {
  const html = render(many);
  return many.critical_alerts.every((a) => html.includes(a.quote));
});

// The lane is always on screen; with nothing critical it says so instead of disappearing.
check("Critical lane shows an explicit empty state", () => render(empty).includes("No critical alerts"));

// Ownership: a proposed owner, an acknowledgment and an acceptance must read differently.
const plain = { ...base.incidents[0], critical: false, owner: "J. Ramirez (on-call)" };
for (const [accepted, acknowledged, expected] of [
  [false, false, "Proposed: J. Ramirez (on-call)"],
  [false, true, "Acknowledged · not accepted"],
  [true, true, "Accepted by J. Ramirez (on-call)"],
]) {
  check(`Ownership label: ${expected}`, () => {
    const html = render({ ...empty, incidents: [{ ...plain, accepted, acknowledged }] });
    return html.includes(expected) && (accepted || !html.includes("Accepted by"));
  });
}

console.log(JSON.stringify(rows, null, 2));
// Exit nonzero so an absent critical alert cannot be mistaken for a passing check.
process.exitCode = rows.some((row) => row[1] === "FAIL") ? 1 : 0;
