import { test, expect, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
// Exported by isolated backend pytest, never from a resident's database.
const fixture = JSON.parse(fs.readFileSync(new URL('./fixtures/operations.json', import.meta.url), 'utf8'));

const privateTranscript = 'Agent: SYNTHETIC PRIVATE CONVERSATION\nUser: possible danger; yes to callback.';
function scenario() {
  const data = structuredClone(fixture) as any;
  data.state.call_mode = 'simulate';
  const power = data.state.incidents.find((i: any) => i.hazard_type === 'downed_line');
  const accepted = data.state.incidents.find((i: any) => i.hazard_type === 'pothole');
  accepted.accepted = true; accepted.status = 'accepted'; accepted.next_step_at = null;
  accepted.why = 'Responsibility accepted by the named reviewer. Resolution has not been verified.';
  accepted.debts = accepted.debts.filter((d: any) => d.kind !== 'no_owner');
  accepted.assignment.accepted_at = data.state.now; accepted.assignment.accepted_by = accepted.owner;
  data.details[String(accepted.id)] = { ...data.details[String(accepted.id)], ...accepted };
  power.critical = true; power.priority = 'critical'; power.status = 'escalated'; power.ladder_step = 5;
  power.why = 'Caller reports possible electrical sparking near a downed power line.';
  data.details[String(power.id)] = { ...data.details[String(power.id)], ...power };
  data.state.critical_alerts = [{ incident_id: power.id, title: power.title, reason: power.why, quote: privateTranscript, evidence: ['report:7'], since: data.state.now, accepted: false, owner: power.owner }];
  data.state.supervisor_queue = [power.id];
  data.state.alerts = [];
  return data;
}
async function mock(page: Page, data = scenario(), options: { failActions?: boolean; offline?: boolean } = {}) {
  const writes: any[] = [];
  await page.route('**/api/**', async route => {
    const request = route.request(); const url = new URL(request.url());
    // All API traffic is intercepted. Never forward to the real local backend.
    if (options.offline) return route.abort('failed');
    if (request.method() === 'POST') {
      writes.push({ path: url.pathname, body: request.postDataJSON(), auth: request.headers().authorization });
      if (options.failActions) return route.fulfill({ status: 401, json: { detail: 'Unauthorized' } });
      const id = url.pathname.split('/')[3]; const detail = data.details[id];
      if (detail && url.pathname.endsWith('/acknowledge')) {
        detail.acknowledged = true; detail.assignment.acknowledged_by = request.postDataJSON().by; detail.assignment.acknowledged_at = data.state.now;
      }
      if (detail && url.pathname.endsWith('/accept')) {
        detail.accepted = true; detail.status = 'accepted'; detail.assignment.accepted_by = request.postDataJSON().owner; detail.assignment.accepted_at = data.state.now;
      }
      if (detail && url.pathname.endsWith('/reassign')) {
        const body = request.postDataJSON(); const target = data.state.departments.find((d: any) => d.name === body.department);
        const staff = target.staff.find((s: any) => s.name === body.owner);
        detail.assignment_history.push(structuredClone(detail.assignment));
        detail.assignment = { ...detail.assignment, id: detail.assignment.id + 100, department: body.department, department_display_name: target.display_name, operational_unit: target.operational_unit, owner: body.owner, owner_display_name: body.owner, owner_role: staff?.role, accepted_at: null, accepted_by: null, acknowledged_at: null, acknowledged_by: null };
        detail.department = body.department; detail.owner = body.owner; detail.accepted = false; detail.acknowledged = false;
      }
      return route.fulfill({ json: detail ?? { ok: true } });
    }
    if (url.pathname === '/api/state') return route.fulfill({ json: data.state });
    if (url.pathname === '/api/assignment-history') return route.fulfill({ json: data.history });
    const match = url.pathname.match(/^\/api\/incidents\/(\d+)(\/.*)?$/);
    if (match) {
      const detail = data.details[match[1]];
      if (!detail) return route.fulfill({ status: 404, json: { detail: 'Not found' } });
      if (match[2] === '/assignment-options') return route.fulfill({ json: { recommended_department: detail.department, fictional_roster: true, area: 'Highland Park', departments: data.state.departments.map((d: any) => ({ department: d.name, owners: d.staff.map((p: any) => p.name), staff: d.staff })) } });
      if (match[2] === '/evidence') {
        expect(request.headers().authorization).toBe('Bearer synthetic-browser-reviewer');
        const evidence = structuredClone(detail); evidence.reports[0].transcript = privateTranscript;
        return route.fulfill({ json: evidence });
      }
      return route.fulfill({ json: detail });
    }
    return route.fulfill({ status: 404, json: { detail: 'Unexpected mocked route' } });
  });
  return writes;
}
for (const width of [1440, 1920, 1024, 768]) {
  test(`operations layout and logo at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1100 });
    const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
    const data = scenario(); await mock(page, data); await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Operations Dashboard', exact: true })).toBeVisible();
    await expect(page.locator('.metric strong')).toHaveText(['5', '4', '1', '1']);
    await expect(page.locator('.incident-list .card')).toHaveCount(5);
    await expect(page.locator('.brand-surface img')).toHaveJSProperty('naturalWidth', 1024);
    const brand = page.locator('.brand-surface img');
    const ratio = await brand.evaluate((img: HTMLImageElement) => img.clientWidth / img.clientHeight);
    expect(Math.abs(ratio - 1024 / 687)).toBeLessThan(.02);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await expect(page.locator('body')).not.toContainText('SYNTHETIC PRIVATE CONVERSATION');
    expect(errors).toEqual([]);
    if (width >= 1440) {
      fs.mkdirSync(path.resolve('artifacts/redesign'), { recursive: true });
      await page.screenshot({ path: `artifacts/redesign/operations-${width}.png`, fullPage: true });
    }
  });
}
test('search, department, priority, ownership, sort, metrics and clear filters', async ({ page }) => {
  await mock(page); await page.goto('/');
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('button', { name: 'Incidents', exact: true }).click();
  await page.getByRole('searchbox', { name: 'Search incidents' }).fill('Elena Morales');
  await expect(page.locator('.incident-list .card')).toHaveCount(1);
  await page.getByRole('searchbox').fill('no-such-location');
  await expect(page.getByText('No incidents match your filters')).toBeVisible();
  await page.getByRole('button', { name: 'Clear filters' }).click();
  await page.getByRole('combobox', { name: 'Department', exact: true }).selectOption('Urban Forestry');
  await expect(page.locator('.incident-list .card')).toHaveCount(1);
  await expect(page.locator('.incident-list')).toContainText('Urban Forestry Response');
  await page.getByRole('combobox', { name: 'Department', exact: true }).selectOption('');
  await page.getByRole('combobox', { name: 'Priority', exact: true }).selectOption('critical');
  await expect(page.locator('.incident-list .card')).toHaveCount(1);
  await page.getByRole('combobox', { name: 'Priority', exact: true }).selectOption('');
  await page.getByRole('combobox', { name: 'Ownership', exact: true }).selectOption('accepted');
  await expect(page.locator('.incident-list .card')).toHaveCount(1);
  await expect(page.locator('.incident-list')).toContainText('Acceptance');
  await page.getByRole('combobox', { name: 'Sort by' }).selectOption('age');
  await page.getByRole('button', { name: /Active Incidents/ }).click();
  await expect(page.locator('.incident-list .card')).toHaveCount(5);
});
test('departments expose backend units and staff responsibilities; audit trail opens detail', async ({ page }) => {
  await mock(page); await page.goto('/');
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('button', { name: 'Departments', exact: true }).click();
  await expect(page.locator('.department-profile')).toHaveCount(5);
  await expect(page.getByText('Electrical & Utility Coordination', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Elena Morales/ }).click();
  await expect(page.getByRole('region', { name: 'Staff responsibility' })).toContainText('Current assigned cases: 1');
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('button', { name: 'Assignment History', exact: true }).click();
  await expect(page.locator('tbody tr')).toHaveCount(fixture.history.entries.length);
  await page.locator('tbody').getByRole('button').first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape'); await expect(page.getByRole('dialog')).toHaveCount(0);
});
test('evidence remains locked and complete source appears only after reviewer authorization', async ({ page }) => {
  const writes = await mock(page); await page.goto('/');
  await page.getByRole('button', { name: 'Review incident evidence' }).click();
  const dialog = page.getByRole('dialog'); await expect(dialog).toBeVisible();
  for (const section of ['Overview', 'Responsibility', 'Assignment History', 'Follow-up', 'Evidence']) await expect(dialog.getByRole('link', { name: section, exact: true })).toBeVisible();
  await expect(page.locator('body')).not.toContainText('SYNTHETIC PRIVATE CONVERSATION');
  await dialog.getByRole('link', { name: 'Evidence', exact: true }).click();
  await dialog.getByLabel('Reviewer access key', { exact: true }).fill('synthetic-browser-reviewer');
  await dialog.getByRole('button', { name: 'Unlock incident evidence' }).click();
  await expect(dialog.locator('.transcript')).toContainText([privateTranscript]);
  await expect(dialog.getByLabel('Reviewer access key', { exact: true })).toHaveCount(0);
  await dialog.getByRole('button', { name: 'Lock evidence' }).click();
  await expect(page.locator('body')).not.toContainText('SYNTHETIC PRIVATE CONVERSATION');
  expect(writes).toEqual([]);
});
test('human acknowledgment and acceptance require identity plus authorization and never run on open', async ({ page }) => {
  const writes = await mock(page); await page.goto('/');
  await page.locator('.incident-list .card').filter({ hasText: 'Downed tree' }).getByRole('button', { name: 'Review incident' }).click();
  const actions = page.getByRole('region', { name: 'Record responsibility actions' });
  await expect(actions.getByRole('button', { name: 'Accept responsibility' })).toBeDisabled();
  expect(writes).toHaveLength(0);
  await actions.getByLabel('Your name', { exact: true }).fill('Synthetic supervisor');
  await actions.getByLabel('Reviewer authorization key', { exact: true }).fill('synthetic-browser-reviewer');
  await actions.getByRole('button', { name: 'Record acknowledgment' }).click();
  await expect(page.getByRole('dialog')).toContainText('Acknowledged · awaiting acceptance');
  await expect(actions.getByLabel('Reviewer authorization key')).toHaveValue('');
  expect(writes[0].auth).toBe('Bearer synthetic-browser-reviewer');
  expect(JSON.stringify(writes[0].body)).not.toContain('synthetic-browser-reviewer');
  await actions.getByLabel('Reviewer authorization key').fill('synthetic-browser-reviewer');
  await actions.getByRole('button', { name: 'Accept responsibility' }).click();
  await expect(page.getByRole('dialog')).toContainText('Accepted by Synthetic supervisor');
  expect(writes.map(w => w.path.split('/').pop())).toEqual(['acknowledge', 'accept']);
});
test('authorized reassignment uses roster and resets receipt and acceptance', async ({ page }) => {
  const writes = await mock(page); await page.goto('/');
  await page.locator('.incident-list .card').filter({ hasText: 'Pothole' }).getByRole('button', { name: 'Review incident' }).click();
  const actions = page.getByRole('region', { name: 'Record responsibility actions' });
  await actions.getByText('Assign or reassign responsibility', { exact: true }).click();
  await actions.getByLabel('Your name', { exact: true }).fill('Synthetic supervisor');
  await actions.getByRole('combobox', { name: 'Responsible department', exact: true }).selectOption('Urban Forestry');
  await actions.getByRole('combobox', { name: 'Assigned individual · configured demo roster', exact: true }).selectOption('Olivia Torres');
  await actions.getByLabel('Reason for assignment change').fill('Configured supporting team takes primary responsibility');
  await actions.getByLabel('Reviewer authorization key').fill('synthetic-browser-reviewer');
  await actions.getByRole('button', { name: 'Save assignment' }).click();
  await expect(page.getByRole('dialog').locator('.responsibility').first()).toContainText('Olivia Torres');
  await expect(page.getByRole('dialog').locator('.responsibility').first()).toContainText('Not accepted');
  expect(writes[0].body.owner).toBe('Olivia Torres');
});
test('authorization errors stay visible and never imply successful acceptance', async ({ page }) => {
  await mock(page, scenario(), { failActions: true }); await page.goto('/');
  await page.locator('.incident-list .card').filter({ hasText: 'Downed tree' }).getByRole('button', { name: 'Review incident' }).click();
  const actions = page.getByRole('region', { name: 'Record responsibility actions' });
  await actions.getByLabel('Your name', { exact: true }).fill('Synthetic supervisor');
  await actions.getByLabel('Reviewer authorization key').fill('synthetic-browser-reviewer');
  await actions.getByRole('button', { name: 'Accept responsibility' }).click();
  await expect(actions.getByRole('alert')).toContainText('Action was not confirmed');
  await expect(page.getByRole('dialog').locator('.responsibility').first()).toContainText('Not accepted');
});
test('all critical alerts remain visible beyond top ten and after acceptance', async ({ page }) => {
  const data = scenario(); const base = data.state.critical_alerts[0];
  data.state.critical_alerts = Array.from({ length: 12 }, (_,n) => ({ ...base, incident_id: n + 100, title: `Synthetic critical case ${n + 1}`, accepted: true }));
  data.state.supervisor_queue = [];
  await mock(page, data); await page.goto('/');
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('button', { name: /Critical Review/ }).click();
  await expect(page.getByRole('button', { name: 'Review incident evidence' })).toHaveCount(12);
  await expect(page.getByText('Synthetic critical case 12', { exact: true })).toBeVisible();
  await expect(page.locator('body')).not.toContainText('SYNTHETIC PRIVATE CONVERSATION');
});
test('live demo reset is disabled and typing t in fields never opens controls', async ({ page }) => {
  const data = scenario(); data.state.call_mode = 'live'; data.state.automatic_live_enabled = true;
  const writes = await mock(page, data); await page.goto('/');
  await page.getByRole('searchbox').fill('tree');
  await expect(page.getByRole('region', { name: 'Demo controls' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Demo controls', exact: true }).click();
  await page.getByText('Reset demonstration data', { exact: true }).click();
  await expect(page.getByRole('button', { name: 'Reset: storm night' })).toBeDisabled();
  expect(writes).toEqual([]);
});
test('outage state has an honest connection message and no fake incident metrics', async ({ page }) => {
  await mock(page, scenario(), { offline: true }); await page.goto('/');
  await expect(page.getByRole('alert')).toContainText('Backend unreachable');
  await expect(page.locator('.metric')).toHaveCount(0);
});
test('age and update sorting follow backend timestamps, including stable risk ties', async ({ page }) => {
  const data = scenario();
  data.state.incidents.forEach((i: any, index: number) => { i.created_at = `2026-10-17T0${index + 1}:00:00Z`; i.updated_at = `2026-10-17T0${index + 1}:30:00Z`; });
  await mock(page, data); await page.goto('/');
  await page.getByRole('combobox', { name: 'Sort by' }).selectOption('updated');
  await expect(page.locator('.incident-list .card').first()).toContainText(data.state.incidents.at(-1).title);
  await page.getByRole('combobox', { name: 'Sort by' }).selectOption('age');
  await expect(page.locator('.incident-list .card').first()).toContainText(data.state.incidents[0].title);
});
test('global audit history loads earlier pages without losing previous entries', async ({ page }) => {
  const data = scenario(); await mock(page, data);
  await page.route('**/api/assignment-history*', route => route.fulfill({ json: new URL(route.request().url()).searchParams.has('before_id')
    ? { entries: data.history.entries.slice(2), next_before_id: null } : { entries: data.history.entries.slice(0,2), next_before_id: data.history.entries[1].assignment.id } }));
  await page.goto('/');
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('button', { name: 'Assignment History', exact: true }).click();
  await expect(page.locator('tbody tr')).toHaveCount(2);
  await page.getByRole('button', { name: 'Load earlier assignments' }).click();
  await expect(page.locator('tbody tr')).toHaveCount(data.history.entries.length);
  await expect(page.getByRole('button', { name: 'Load earlier assignments' })).toHaveCount(0);
});
test('official logo opens legibly, keeps keyboard focus, and restores it on close', async ({ page }) => {
  await mock(page); await page.goto('/');
  const button = page.getByRole('button', { name: 'View complete official HandoffProof logo' });
  await button.click(); const dialog = page.getByRole('dialog', { name: 'Official HandoffProof identity' });
  await expect(dialog).toBeVisible(); await expect(dialog.getByRole('img')).toHaveJSProperty('naturalWidth', 1024);
  await page.keyboard.press('Tab'); await expect(dialog.getByRole('button')).toBeFocused();
  await page.keyboard.press('Escape'); await expect(dialog).toHaveCount(0); await expect(button).toBeFocused();
});
