// Render evidence boundaries and exercise the real API module with synthetic fetch responses.
const assert = require('assert/strict');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const ts = require('typescript');
const root = process.cwd();
const detail = JSON.parse(fs.readFileSync('src/fixtures/incident.json', 'utf8'));
const PRIVATE = 'PRIVATE_FULL_CONVERSATION_SENTINEL';
detail.reports[0].transcript = `Agent: A question\nUser: ${PRIVATE}`;
detail.callbacks = [{ attempt_no: 1, outcome: 'worse', danger: true, summary: PRIVATE, called_at: detail.reports[0].created_at }];
const rows = [];

function load(entry, { fetchedDetail = false, unlocked = false, fetch } = {}) {
  const cache = {};
  function module(file) {
    if (cache[file]) return cache[file];
    let source = fs.readFileSync(file, 'utf8').replace(/import\.meta\.env\.VITE_API/g, '"live"');
    const code = ts.transpileModule(source, { compilerOptions: {
      target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
    } }).outputText;
    const exports = {};
    cache[file] = exports;
    function req(name) {
      if (name === 'react') return { ...React, useState(initial) {
        const state = React.useState(initial);
        if (initial === null && ((fetchedDetail && file.endsWith('/IncidentDetail.tsx')) ||
          (unlocked && file.endsWith('/EvidenceReview.tsx')))) return [detail, state[1]];
        return state;
      } };
      if (!name.startsWith('.')) return require(name);
      let target = path.resolve(path.dirname(file), name);
      if (!path.extname(target)) target += fs.existsSync(target + '.tsx') ? '.tsx' : '.ts';
      if (target.endsWith('.json')) return JSON.parse(fs.readFileSync(target, 'utf8'));
      return module(target);
    }
    vm.runInNewContext(code, { exports, require: req, fetch, console, setInterval, clearInterval });
    return exports;
  }
  return module(path.join(root, entry));
}

async function check(name, fn) {
  try { await fn(); rows.push({ name, result: 'PASS' }); }
  catch (error) { rows.push({ name, result: 'FAIL', error: error.message }); }
}

(async () => {
  await check('Critical panel omits transcripts, legacy quotes and unsafe reasons', () => {
    const Panel = load('src/components/CriticalAlerts.tsx').default;
    const html = renderToStaticMarkup(React.createElement(Panel, {
      alerts: [{ incident_id: detail.id, title: detail.title, reason: `Agent: ${PRIVATE}`, quote: PRIVATE, evidence: [], accepted: false }],
      incidents: [detail], onOpen() {},
    }));
    assert(!html.includes(PRIVATE));
    assert(html.includes('concise assessment is unavailable'));
    assert(html.includes('Review incident evidence'));
  });
  await check('Ordinary drawer never renders raw evidence, including legacy API fields', () => {
    const Drawer = load('src/components/IncidentDetail.tsx', { fetchedDetail: true }).default;
    const html = renderToStaticMarkup(React.createElement(Drawer, { id: detail.id, onClose() {} }));
    assert(!html.includes(PRIVATE));
    assert(html.includes('Unlock incident evidence'));
    assert(html.includes('Callback permission: given') && html.includes('Callback permission: not given'));
  });
  await check('Unlocked reviewer view renders the complete source evidence', () => {
    const Review = load('src/components/EvidenceReview.tsx', { unlocked: true }).default;
    const html = renderToStaticMarkup(React.createElement(Review, { id: detail.id }));
    assert(html.includes(PRIVATE));
    assert(html.includes('Agent: A question\nUser:'));
    assert(html.includes('Lock evidence'));
  });
  await check('Locked evidence view requests reviewer authorization without rendering evidence', () => {
    const Review = load('src/components/EvidenceReview.tsx').default;
    const html = renderToStaticMarkup(React.createElement(Review, { id: detail.id }));
    assert(html.includes('type="password"'));
    assert(!html.includes(PRIVATE));
  });
  await check('Evidence fetch sends reviewer key only in authorization header with caching disabled', async () => {
    const seen = [];
    const api = load('src/api.ts', { fetch: async (url, init) => {
      seen.push({ url, init }); return { ok: true, json: async () => detail };
    } });
    assert.equal(await api.fetchIncidentEvidence(7, 'synthetic-reviewer-key'), detail);
    assert.equal(seen.length, 1);
    assert.equal(seen[0].url, '/api/incidents/7/evidence');
    assert.equal(seen[0].init.headers.Authorization, 'Bearer synthetic-reviewer-key');
    assert.equal(seen[0].init.cache, 'no-store');
    await api.fetchState();
    assert(!seen[1].init.headers.Authorization);
  });
  for (const status of [401, 503]) {
    await check(`Evidence HTTP ${status} fails without fallback or credential disclosure`, async () => {
      let requests = 0;
      const api = load('src/api.ts', { fetch: async () => { requests++; return { ok: false, status }; } });
      await assert.rejects(api.fetchIncidentEvidence(7, 'synthetic-private-key'), error =>
        error.message.includes(String(status)) && !error.message.includes('synthetic-private-key'));
      assert.equal(requests, 1);
    });
  }
  console.log(JSON.stringify(rows, null, 2));
  process.exitCode = rows.some(row => row.result === 'FAIL') ? 1 : 0;
})();
