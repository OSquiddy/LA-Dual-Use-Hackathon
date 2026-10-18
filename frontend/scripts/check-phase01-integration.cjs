// Render the real dashboard against synthetic state/detail snapshots exported by pytest.
//   (backend)  HANDOFFPROOF_INTEGRATION_SNAPSHOTS=<dir> pytest tests/test_phase01_acceptance.py
//   (frontend) npm run check:phase01 -- <dir>
const fs = require("fs");
const path = require("path");
const { renderApp } = require("./render-app.cjs");

const snapshotDir = process.argv[2];
if (!snapshotDir) throw new Error("Pass the snapshot directory exported by test_phase01_acceptance.py");

const escapeHtml = (s) => s.replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#x27;" })[ch]);
const results = [];
const files = fs.readdirSync(snapshotDir).filter((name) => name.endsWith(".json")).sort();
if (files.length !== 12) throw new Error(`Expected 12 combined scenario exports, got ${files.length}`);

for (const file of files) {
  const snapshots = JSON.parse(fs.readFileSync(path.join(snapshotDir, file), "utf8"));
  if (snapshots.length !== 4) throw new Error(`Expected four handoff stages in ${file}`);
  for (const snapshot of snapshots) {
    try {
      const html = renderApp({ state: snapshot.state, detail: snapshot.detail, selectedId: snapshot.detail.id });
      const assert = (ok, message) => { if (!ok) throw new Error(message); };
      assert(html.includes("Prototype · not a city service"), "Prototype identity absent");
      for (const alert of snapshot.state.critical_alerts) {
        assert(html.includes(escapeHtml(alert.reason)), "Critical reason absent");
        if (alert.quote) assert(html.includes(escapeHtml(alert.quote)), "Critical evidence absent");
      }
      if (snapshot.stage === "closed") {
        assert(html.includes("No open incidents"), "Closed case remains in queue");
      } else {
        assert(html.includes(escapeHtml(snapshot.detail.title)), "Incident title absent");
        for (const report of snapshot.detail.reports) {
          assert(html.includes(escapeHtml(report.transcript)), "A retained report transcript is absent");
        }
        assert(/agreed to a callback|No caller gave callback permission/.test(html), "Consent summary absent");
        assert(html.includes(snapshot.detail.reports.some((r) => r.callback_ok) ? "callback OK" : "no callback"), "Per-report consent absent");
      }
      if (snapshot.stage === "acknowledged") {
        assert(html.includes("Acknowledged") && html.includes("Accept responsibility") && !html.includes("Accepted by"),
          "Receipt confused with acceptance");
      }
      if (snapshot.stage === "accepted") assert(html.includes("Accepted by Synthetic operator"), "Acceptance label absent");
      assert(!/\+1\d{10}/.test(html), "Full phone number exposed");
      results.push({ scenario: file, stage: snapshot.stage, result: "PASS" });
    } catch (error) {
      results.push({ scenario: file, stage: snapshot.stage, result: "FAIL", error: error.message });
    }
  }
}

const failed = results.filter((r) => r.result === "FAIL");
console.log(JSON.stringify({ checks: results.length, passed: results.length - failed.length, failed: failed.length, failures: failed }, null, 2));
process.exitCode = failed.length ? 1 : 0;
