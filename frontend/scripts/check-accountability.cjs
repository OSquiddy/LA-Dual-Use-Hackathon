// Synthetic rendering and action tests; no browser, database writes or live calls.
const assert = require('assert/strict');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const ts = require('typescript');
const root = process.cwd();
const baseState = JSON.parse(fs.readFileSync('src/fixtures/state.json', 'utf8'));
const baseDetail = JSON.parse(fs.readFileSync('src/fixtures/incident.json', 'utf8'));
const stamp = '2026-10-18T02:15:00Z';
const assignment = { ...baseDetail.assignment, department: 'Synthetic response department', owner: 'Synthetic roster person', id: 42,
  assigned_at: stamp, acknowledged_at: null, acknowledged_by: null, accepted_at: null, accepted_by: null };
const base = { ...baseDetail, id: 9, department: assignment.department, owner: assignment.owner, assignment, assignment_history: [assignment],
  accepted: false, acknowledged: false, status: 'open', closed_at: null, closed_by: null };
const scenarios = [
  ['Awaiting department assignment', { ...base, department: null, owner: null, assignment: null, assignment_history: [] }],
  ['Department assigned · individual not assigned', { ...base, owner: null, assignment: { ...assignment, owner: null } }],
  ['Individual assigned · awaiting acknowledgment', base],
  ['Acknowledged · awaiting acceptance', { ...base, acknowledged: true, assignment: { ...assignment, acknowledged_at: stamp, acknowledged_by: 'Synthetic receipt clerk' } }],
  ['Accepted by Synthetic accepting person', { ...base, accepted: true, status: 'accepted', assignment: { ...assignment, accepted_at: stamp, accepted_by: 'Synthetic accepting person' } }],
  ['Closed by Synthetic closing reviewer', { ...base, status: 'closed', closed_by: 'Synthetic closing reviewer', closed_at: stamp }],
];

function load(entry, { incident = base, fetch, manualActions = null } = {}) {
  const cache = {};
  function module(file) {
    if (cache[file]) return cache[file];
    const source = fs.readFileSync(file, 'utf8').replace(/import\.meta\.env\.VITE_API/g, '"live"');
    const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } }).outputText;
    const exports = {}; cache[file] = exports;
    function req(name) {
      if (name === 'react' && file.endsWith('/IncidentDetail.tsx')) return { ...React, useState(initial) {
        const [value, setter] = React.useState(initial); return [initial === null ? incident : value, setter];
      } };
      if (name === 'react' && manualActions && file.endsWith('/AssignmentActions.tsx')) {
        let index = 0;
        const values = [manualActions.actor ?? '', manualActions.department ?? incident.department,
          manualActions.owner ?? '', 'Synthetic reason', manualActions.options ?? null, false, false, '', '', manualActions.reviewerKey ?? ''];
        return { ...React, useEffect() {}, useRef: () => ({ current: true }), useState(initial) {
          const slot = index++;
          return [slot < values.length ? values[slot] : initial, value => manualActions.setters.push({ slot, value })];
        } };
      }
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
const rows = [];
async function check(name, action) {
  try { await action(); rows.push({ name, result: 'PASS' }); }
  catch (error) { rows.push({ name, result: 'FAIL', error: error.message }); }
}
function find(node, predicate) {
  if (!node || typeof node !== 'object') return null;
  if (Array.isArray(node)) return node.map(n => find(n, predicate)).find(Boolean);
  return predicate(node) ? node : find(node.props?.children, predicate);
}

(async () => {
  for (const [status, incident] of scenarios) {
    for (const component of ['DepartmentQueue', 'SupervisorQueue', 'CriticalAlerts', 'IncidentDetail']) {
      await check(`${component}: ${status}`, () => {
        const state = { ...baseState, incidents: [incident], supervisor_queue: [incident.id] };
        const Component = load(`src/components/${component}.tsx`, { incident }).default;
        const props = component === 'IncidentDetail' ? { id: incident.id, onClose() {} }
          : component === 'CriticalAlerts' ? { alerts: [{ incident_id: incident.id, title: incident.title, reason: 'Possible danger reported', evidence: [] }], incidents: [incident], onOpen() {} }
          : { state, onOpen() {} };
        const html = renderToStaticMarkup(React.createElement(Component, props));
        for (const label of ['Responsible department', 'Assigned individual', 'Acknowledgment', 'Acceptance', 'Assigned at', status]) assert(html.includes(label), `Absent: ${label}`);
        if (incident.department) assert(html.includes(incident.department));
        if (incident.owner) assert(html.includes(incident.owner));
        if (incident.assignment) assert(html.includes(stamp));
        assert(html.includes('fictional demo personnel'));
      });
    }
  }
  await check('Acceptance does not infer acknowledgment from legacy flat booleans', () => {
    const Component = load('src/components/AssignmentSummary.tsx').default;
    const incident = { ...scenarios[4][1], acknowledged: true };
    const html = renderToStaticMarkup(React.createElement(Component, { incident }));
    assert(html.includes('Acknowledgment</dt><dd>Not recorded'));
    assert(!html.includes('Acknowledged · awaiting acceptance'));
  });
  await check('Current null ownership and missing accepting actor never invent an individual from old flat fields', () => {
    const Component = load('src/components/AssignmentSummary.tsx').default;
    const unassigned = { ...base, owner: 'Stale previous person', assignment: { ...assignment, owner: null } };
    const html = renderToStaticMarkup(React.createElement(Component, { incident: unassigned }));
    assert(!html.includes('Stale previous person'));
    assert(html.includes('Department assigned · individual not assigned'));
    const accepted = { ...base, assignment: { ...assignment, accepted_at: stamp, accepted_by: null } };
    const acceptedHtml = renderToStaticMarkup(React.createElement(Component, { incident: accepted }));
    assert(acceptedHtml.includes('accepting individual not recorded'));
    assert(!acceptedHtml.includes('Accepted by Synthetic roster person'));
  });
  await check('Department-card Accept opens the incident without writing a generic desk acceptance', () => {
    const opened = [], requests = [];
    const Component = load('src/components/DepartmentQueue.tsx', { fetch: (...args) => requests.push(args) }).default;
    const tree = Component({ state: { ...baseState, incidents: [base] }, onOpen: id => opened.push(id) });
    const card = find(tree, node => node.type?.name === 'IncidentCard');
    assert(card); card.props.onAccept(base);
    assert.equal(opened[0], base.id); assert.equal(requests.length, 0);
  });
  await check('Unnamed human actions are disabled and rendering performs no write', () => {
    const manualActions = { actor: '   ', setters: [] }, requests = [];
    const Component = load('src/components/AssignmentActions.tsx', { manualActions, fetch: (...args) => requests.push(args) }).default;
    const tree = Component({ incident: base, onChanged() {} });
    const button = find(tree, node => node.type === 'button' && node.props.children === 'Accept responsibility');
    assert(button.props.disabled); assert.equal(requests.length, 0);
  });
  await check('Named acceptance sends the actual person and assignment ID, updating only after server confirmation', async () => {
    const requests = [], manualActions = { actor: 'Synthetic actual person', setters: [] };
    let resolve, changed = 0;
    const Component = load('src/components/AssignmentActions.tsx', { manualActions, fetch: (url, init) => {
      requests.push({ url, init }); return new Promise(done => { resolve = done; });
    } }).default;
    const tree = Component({ incident: base, onChanged() { changed++; } });
    const button = find(tree, node => node.type === 'button' && node.props.children === 'Accept responsibility');
    assert(!button.props.disabled); button.props.onClick();
    assert.equal(changed, 0);
    const body = JSON.parse(requests[0].init.body);
    assert.equal(body.owner, 'Synthetic actual person'); assert.equal(body.expected_assignment_id, 42);
    resolve({ ok: true, json: async () => ({}) });
    await new Promise(setImmediate);
    assert.equal(changed, 1);
  });
  await check('A rejected action never claims acceptance or refreshes as a success', async () => {
    const manualActions = { actor: 'Synthetic person', setters: [] }; let changed = 0;
    const Component = load('src/components/AssignmentActions.tsx', { manualActions, fetch: async () => ({ ok: false, status: 409 }) }).default;
    const tree = Component({ incident: base, onChanged() { changed++; } });
    find(tree, node => node.type === 'button' && node.props.children === 'Accept responsibility').props.onClick();
    await new Promise(setImmediate);
    assert.equal(changed, 0);
    assert(manualActions.setters.some(s => typeof s.value === 'string' && s.value.includes('not confirmed')));
    assert(!manualActions.setters.some(s => typeof s.value === 'string' && s.value.includes('Acceptance recorded')));
  });
  await check('Assignment API uses backend options and sends explicit reassignment audit data', async () => {
    const seen = [];
    const api = load('src/api.ts', { fetch: async (url, init) => { seen.push({ url, init }); return { ok: true, json: async () => ({}) }; } });
    await api.fetchAssignmentOptions(9);
    await api.acknowledgeIncident(9, 'Synthetic clerk', 42);
    await api.reassignIncident(9, { department: 'Synthetic department', owner: 'Synthetic roster person', by: 'Synthetic supervisor', reason: 'Verified routing change', expected_assignment_id: 42 }, 'synthetic-reviewer-key');
    assert.equal(seen[0].url, '/api/incidents/9/assignment-options');
    assert.equal(JSON.parse(seen[1].init.body).by, 'Synthetic clerk');
    assert.equal(JSON.parse(seen[2].init.body).reason, 'Verified routing change');
    assert.equal(JSON.parse(seen[2].init.body).expected_assignment_id, 42);
    assert.equal(seen[2].init.headers.Authorization, 'Bearer synthetic-reviewer-key');
    assert.equal(seen[2].init.headers['Content-Type'], 'application/json');
    assert(!seen[0].init.headers.Authorization && !seen[1].init.headers.Authorization);
    assert(!seen[2].init.body.includes('synthetic-reviewer-key') && !seen[2].url.includes('synthetic-reviewer-key'));
  });
  const reassignment = { actor: 'Synthetic supervisor', department: 'Other synthetic department', owner: 'Other synthetic roster person',
    options: { recommended_department: base.department, departments: [{ department: 'Other synthetic department', owners: ['Other synthetic roster person'] }] } };
  await check('Reassignment requires a reviewer key even when the actor and roster choices are present', () => {
    const manualActions = { ...reassignment, setters: [] }, requests = [];
    const Component = load('src/components/AssignmentActions.tsx', { manualActions, fetch: (...args) => requests.push(args) }).default;
    const tree = Component({ incident: base, onChanged() {} });
    const button = find(tree, node => node.type === 'button' && node.props.children === 'Save assignment');
    assert(button.props.disabled);
    assert(find(tree, node => node.type === 'input' && node.props.type === 'password'));
    button.props.onClick(); // The handler also guards programmatically triggered requests.
    assert.equal(requests.length, 0);
    assert(manualActions.setters.some(s => typeof s.value === 'string' && s.value.includes('authorization is required')));
  });
  await check('Authorized reassignment sends credentials in the header and clears them after confirmation', async () => {
    const manualActions = { ...reassignment, reviewerKey: 'synthetic-private-reviewer-key', setters: [] }, requests = [];
    let resolve, changed = 0;
    const Component = load('src/components/AssignmentActions.tsx', { manualActions, fetch: (url, init) => {
      requests.push({ url, init }); return new Promise(done => { resolve = done; });
    } }).default;
    const tree = Component({ incident: base, onChanged() { changed++; } });
    const button = find(tree, node => node.type === 'button' && node.props.children === 'Save assignment');
    assert(!button.props.disabled); button.props.onClick();
    assert.equal(changed, 0);
    assert.equal(requests[0].init.headers.Authorization, 'Bearer synthetic-private-reviewer-key');
    assert(!requests[0].init.body.includes(manualActions.reviewerKey));
    resolve({ ok: true, json: async () => ({}) });
    await new Promise(setImmediate);
    assert.equal(changed, 1);
    assert(manualActions.setters.some(s => s.slot === 9 && s.value === ''));
  });
  for (const status of [401, 503]) await check(`Reassignment HTTP ${status} never reports success and clears the credential`, async () => {
    const manualActions = { ...reassignment, reviewerKey: 'synthetic-private-reviewer-key', setters: [] }; let changed = 0;
    const Component = load('src/components/AssignmentActions.tsx', { manualActions, fetch: async () => ({ ok: false, status }) }).default;
    const tree = Component({ incident: base, onChanged() { changed++; } });
    find(tree, node => node.type === 'button' && node.props.children === 'Save assignment').props.onClick();
    await new Promise(setImmediate);
    assert.equal(changed, 0);
    assert(manualActions.setters.some(s => s.slot === 9 && s.value === ''));
    assert(manualActions.setters.some(s => typeof s.value === 'string' && s.value.includes('Reassignment was not confirmed')));
    assert(!manualActions.setters.some(s => typeof s.value === 'string' && s.value.includes('Assignment updated')));
  });
  await check('Assignment history keeps previous acceptance and the new unaccepted owner visible', () => {
    const Component = load('src/components/AssignmentHistory.tsx').default;
    const old = { ...assignment, id: 41, owner: 'Previous synthetic person', accepted_at: stamp, accepted_by: 'Previous synthetic person' };
    const incident = { ...base, assignment_history: [old, assignment] };
    const html = renderToStaticMarkup(React.createElement(Component, { incident }));
    assert(html.includes('Previous synthetic person') && html.includes('Synthetic roster person'));
    assert(html.includes('Not accepted') && html.includes(stamp));
  });
  console.log(JSON.stringify({ checks: rows.length, passed: rows.filter(r => r.result === 'PASS').length,
    failed: rows.filter(r => r.result === 'FAIL').length, failures: rows.filter(r => r.result === 'FAIL') }, null, 2));
  process.exitCode = rows.some(row => row.result === 'FAIL') ? 1 : 0;
})();
