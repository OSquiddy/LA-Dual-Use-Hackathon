// Real component/API tests with synthetic props and mocked fetch; no real calls or browser implied.
const assert = require('assert/strict');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const ts = require('typescript');
const fixture = JSON.parse(fs.readFileSync('src/fixtures/incident.json', 'utf8'));
const incident = { ...fixture, callback_status: { eligible: true, reason: 'Explicit consent and valid stored number',
  scheduled_at: '2026-10-18T02:00:00Z', call_mode: 'simulate', attempts_used: 1, max_attempts: 2, automatic_live_enabled: false },
  reports: [{ ...fixture.reports[0], callback_ok: true, callback_eligible: true, callback_opt_out: false }],
  callbacks: [{ attempt_no: 1, state: 'calling', mode: 'simulate', outcome: null, danger: false,
    summary: 'Current conditions unknown', transcript: 'PRIVATE FULL CONVERSATION' }] };

function load(entry, { controls, fetch, mode = 'live' } = {}) {
  const cache = {};
  function module(file) {
    if (cache[file]) return cache[file];
    const source = fs.readFileSync(file, 'utf8').replace(/import\.meta\.env\.VITE_API/g, JSON.stringify(mode));
    const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2020,
      module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } }).outputText;
    const exports = {}; cache[file] = exports;
    function req(name) {
      if (name === 'react' && controls && file.endsWith('/CallbackPanel.tsx')) {
        let slot = 0;
        return { ...React, useEffect() {}, useRef: v => ({ current: v }), useState(v) {
          const index = slot++;
          const values = [controls.actor ?? 'Synthetic reviewer', controls.key ?? 'synthetic-private-key', !!controls.confirm, false, ''];
          return [values[index] ?? v, value => controls.setters.push({ index, value })];
        } };
      }
      if (!name.startsWith('.')) return require(name);
      let target = path.resolve(path.dirname(file), name);
      if (!path.extname(target)) target += fs.existsSync(target + '.tsx') ? '.tsx' : '.ts';
      return target.endsWith('.json') ? JSON.parse(fs.readFileSync(target, 'utf8')) : module(target);
    }
    vm.runInNewContext(code, { exports, require: req, fetch, console });
    return exports;
  }
  return module(path.resolve(entry));
}
function find(node, predicate) {
  if (!node || typeof node !== 'object') return null;
  if (Array.isArray(node)) return node.map(n => find(n, predicate)).find(Boolean);
  return predicate(node) ? node : find(node.props?.children, predicate);
}
const rows = [];
async function check(name, action) {
  try { await action(); rows.push({ name, result: 'PASS' }); }
  catch (error) { rows.push({ name, result: 'FAIL', error: error.message }); }
}
(async () => {
  for (const [state, text] of [['scheduled', 'Scheduled'], ['calling', 'Calling'], ['completed', 'Completed'],
    ['failed', 'Failed'], ['cancelled', 'Cancelled'], ['unknown', 'human review required']]) {
    await check(`Callback ${state} displays status, consent, deadline, risk and no transcript`, () => {
      const Component = load('src/components/CallbackPanel.tsx').default;
      const value = { ...incident, callbacks: [{ ...incident.callbacks[0], state }] };
      const html = renderToStaticMarkup(React.createElement(Component, { incident: value, onChanged() {} }));
      for (const label of [text, 'Callback permission: given', 'Scheduled callback time', 'Risk', 'Attempt #1', 'Conditions unknown']) assert(html.includes(label), label);
      assert(!html.includes('PRIVATE FULL CONVERSATION') && !html.includes('+1323'));
    });
  }
  await check('Opt-out remains visible independently of original consent', () => {
    const Component = load('src/components/CallbackPanel.tsx').default;
    const html = renderToStaticMarkup(React.createElement(Component, { incident: { ...incident,
      reports: [{ ...incident.reports[0], callback_opt_out: true, callback_eligible: false }] }, onChanged() {} }));
    assert(html.includes('Callback permission: given') && html.includes('Contact opted out or number blocked'));
  });
  for (const [mode, key, eligible, confirm, disabled] of [
    ['simulate', '', true, false, true], ['simulate', 'test-key', false, false, true],
    ['live', 'test-key', true, false, true], ['live', 'test-key', true, true, false],
  ]) await check(`Request guard: ${mode}, key=${!!key}, eligible=${eligible}, confirm=${confirm}`, async () => {
    const controls = { key, confirm, setters: [] }, requests = [];
    const Component = load('src/components/CallbackPanel.tsx', { controls, fetch: async (url, init) => {
      requests.push({ url, init }); return { ok: true, json: async () => ({}) };
    } }).default;
    const tree = Component({ incident: { ...incident, callback_status: { ...incident.callback_status, call_mode: mode, eligible } }, onChanged() {} });
    const button = find(tree, n => n.type === 'button' && n.props.children === (mode === 'live' ? 'Place one confirmed live callback' : 'Request one simulated callback'));
    assert.equal(button.props.disabled, disabled);
    button.props.onClick();
    await new Promise(setImmediate);
    assert.equal(requests.length, disabled ? 0 : 1);
    if (!disabled) {
      assert.equal(JSON.parse(requests[0].init.body).confirm_live, true);
      assert.equal(requests[0].init.headers.Authorization, 'Bearer test-key');
      assert(!requests[0].init.body.includes('test-key'));
      assert(controls.setters.some(s => s.index === 1 && s.value === ''));
    }
  });
  await check('Rapid duplicate clicks send only one request and never claim success before acknowledgment', async () => {
    const controls = { setters: [] }, requests = []; let changed = 0, resolve;
    const Component = load('src/components/CallbackPanel.tsx', { controls, fetch: (url, init) => {
      requests.push({ url, init }); return new Promise(done => { resolve = done; });
    } }).default;
    const tree = Component({ incident, onChanged() { changed++; } });
    const button = find(tree, n => n.type === 'button' && n.props.children === 'Request one simulated callback');
    button.props.onClick(); button.props.onClick();
    assert.equal(requests.length, 1); assert.equal(changed, 0);
    resolve({ ok: true, json: async () => ({}) });
    await new Promise(setImmediate);
    assert.equal(changed, 1);
  });
  await check('HTTP rejection clears credentials and does not report dispatch success', async () => {
    const controls = { setters: [] }; let changed = 0;
    const Component = load('src/components/CallbackPanel.tsx', { controls, fetch: async () => ({ ok: false, status: 409 }) }).default;
    const tree = Component({ incident, onChanged() { changed++; } });
    find(tree, n => n.type === 'button' && n.props.children === 'Request one simulated callback').props.onClick();
    await new Promise(setImmediate);
    assert.equal(changed, 0);
    assert(controls.setters.some(s => s.index === 1 && s.value === ''));
    assert(controls.setters.some(s => typeof s.value === 'string' && s.value.includes('not confirmed')));
  });
  await check('Callback API uses stored-contact endpoints and Bearer headers only', async () => {
    const seen = [];
    const api = load('src/api.ts', { fetch: async (url, init) => { seen.push({ url, init }); return { ok: true, json: async () => ({}) }; } });
    await api.requestCallback(1, 'Synthetic reviewer', 'synthetic-private-key', false);
    await api.optOutReport(5, 'Synthetic reviewer', 'synthetic-private-key');
    assert.equal(seen[0].url, '/api/incidents/1/request-callback');
    assert.equal(seen[1].url, '/api/reports/5/callback-opt-out');
    assert.equal(JSON.parse(seen[0].init.body).confirm_live, false);
    for (const r of seen) { assert(r.init.headers.Authorization); assert(!r.init.body.includes('synthetic-private-key')); assert(!r.init.body.includes('phone')); }
  });
  console.log(JSON.stringify({ checks: rows.length, passed: rows.filter(r => r.result === 'PASS').length,
    failed: rows.filter(r => r.result === 'FAIL').length, failures: rows.filter(r => r.result === 'FAIL') }, null, 2));
  process.exitCode = rows.some(r => r.result === 'FAIL') ? 1 : 0;
})();
