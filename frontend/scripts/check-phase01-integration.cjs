// Render the real frontend against synthetic state/detail snapshots exported by pytest.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = process.cwd();
const ts = require(path.join(root, 'node_modules/typescript'));
const React = require(path.join(root, 'node_modules/react'));
const { renderToStaticMarkup } = require(path.join(root, 'node_modules/react-dom/server'));
const snapshotDir = process.argv[2];
if (!snapshotDir) throw new Error('Pass the snapshot directory exported by test_phase01_acceptance.py');

function render(snapshot) {
  const cache = {};
  function load(file) {
    if (cache[file]) return cache[file];
    const code = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
      compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS,
        jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
    }).outputText;
    const exports = {};
    cache[file] = exports;
    function req(name) {
      if (name === './useHandoffState') return { useHandoffState: () => ({ state: snapshot.state, error: null }) };
      if (name === './api' || name === '../api') return { API_MODE: 'live' };
      // Inject fetched detail and an open drawer; no browser effects or network are implied.
      if (name === 'react' && file.endsWith('/App.tsx')) {
        return { ...React, useState: (initial) => [initial === null ? snapshot.detail.id : initial, () => {}] };
      }
      if (name === 'react' && file.endsWith('/IncidentDetail.tsx')) {
        return { ...React, useState: (initial) => [initial === null ? snapshot.detail : initial, () => {}], useEffect: () => {} };
      }
      if (!name.startsWith('.')) return require(path.join(root, 'node_modules', name));
      let target = path.resolve(path.dirname(file), name);
      if (!path.extname(target)) target += fs.existsSync(target + '.tsx') ? '.tsx' : '.ts';
      return load(target);
    }
    vm.runInNewContext(code, { exports, require: req, console, setInterval, clearInterval });
    return exports;
  }
  return renderToStaticMarkup(React.createElement(load(path.join(root, 'src/App.tsx')).default));
}
const escapeHtml = (s) => s.replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#x27;' }[ch]));
const results = [];
const files = fs.readdirSync(snapshotDir).filter((name) => name.endsWith('.json')).sort();
if (files.length !== 12) throw new Error(`Expected 12 combined scenario exports, got ${files.length}`);
for (const file of files) {
  const snapshots = JSON.parse(fs.readFileSync(path.join(snapshotDir, file), 'utf8'));
  if (snapshots.length !== 4) throw new Error(`Expected four handoff stages in ${file}`);
  for (const snapshot of snapshots) {
    try {
      const html = render(snapshot);
      const assert = (ok, message) => { if (!ok) throw new Error(message); };
      assert(html.includes('Prototype demo'), 'Prototype identity absent');
      assert(html.includes(escapeHtml(snapshot.detail.title)), 'Incident title absent');
      for (const report of snapshot.detail.reports) {
        assert(!report.transcript, 'Ordinary API response exposed a transcript');
      }
      assert(html.includes('Unlock incident evidence'), 'Restricted evidence control absent');
      assert(html.includes('Callback permission:'), 'Consent display absent');
      for (const alert of snapshot.state.critical_alerts) {
        assert(html.includes(escapeHtml(alert.reason)), 'Critical reason absent');
        assert(!alert.quote, 'Critical response exposed raw evidence');
      }
      if (snapshot.stage === 'acknowledged') assert(html.includes('Acknowledged · awaiting acceptance'), 'Receipt confused with acceptance');
      if (snapshot.stage === 'accepted') assert(html.includes('Accepted'), 'Acceptance label absent');
      if (snapshot.stage === 'closed') assert(html.includes('No open incidents'), 'Closed case remains in queue');
      assert(!/\+1\d{10}/.test(html), 'Full phone number exposed');
      results.push({ scenario: file, stage: snapshot.stage, result: 'PASS' });
    } catch (error) {
      results.push({ scenario: file, stage: snapshot.stage, result: 'FAIL', error: error.message });
    }
  }
}
const failed = results.filter((r) => r.result === 'FAIL');
console.log(JSON.stringify({ checks: results.length, passed: results.length - failed.length, failed: failed.length, failures: failed }, null, 2));
process.exitCode = failed.length ? 1 : 0;
