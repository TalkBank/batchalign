// GUI interaction/serialization tests. Native pipeline/output tests live in
// test_desktop_jobs.py; this boundary stub makes UI failures deterministic.
import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
const stub = readFileSync(new URL('./tauri-stubs.js', import.meta.url), 'utf8');
const verbs = ['transcribe', 'diarize', 'align', 'morphotag', 'translate', 'compare'];
test.setTimeout(30_000);

for (const pipeline of [...verbs.map(verb => [verb]), ['transcribe', 'align', 'morphotag', 'translate']]) {
  test(`GUI submits ${pipeline.join(' → ')}`, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.addInitScript({ content: stub + `\n(${install.toString()})();` });
    await page.goto('/');
    await page.getByRole('button', { name: 'open folder…' }).click();
    for (const verb of pipeline) {
      await page.getByRole('button', { name: '+ add step', exact: true }).click();
      await page.locator('div').filter({ hasText: new RegExp(`^${verb}$`) }).last().click();
    }
    await page.getByRole('button', { name: 'start batch', exact: true }).click();
    await expect(page.locator('tbody > tr')).toHaveCount(1);
    await expect(page.getByText('done', { exact: true }).first()).toBeVisible();
    const request = await page.evaluate(() => (window as any).__DESKTOP_REQUEST__);
    expect(request.steps.map((step: any) => step.recipe)).toEqual(pipeline);
    expect(request.source_ids).toEqual([pipeline[0] === 'transcribe' ? 'nested/é.wav' : 'nested/é.cha']);
    expect(request.in_place).toBe(true);
    expect(errors).toEqual([]);
  });
}

function install() {
  const w = window as any;
  w.__E2E_FOLDER__ = '/fixtures';
  w.__E2E_FILES__ = ['é.wav', 'é.cha', 'é.gold.cha'].map(filename => ({
    source_id: 'nested/' + filename, filename, stem: filename.replace(/\.[^.]+$/, ''),
    kind: filename.endsWith('.wav') ? 'media' : 'chat', size_bytes: 100, duration_ms: null,
  }));
  const original = w.__TAURI_INTERNALS__.invoke;
  w.__TAURI_INTERNALS__.invoke = async (cmd: string, args: any) => {
    if (cmd === 'ensure_daemon') return 43210;
    if (cmd === 'start_batch_pump') return;
    if (cmd === 'daemon_request') {
      if (args.path === '/capabilities') return { recipes: {}, backends_by_task: {} };
      if (args.path === '/desktop/jobs') {
        w.__DESKTOP_REQUEST__ = args.body;
        return { job_id: 'test-job' };
      }
      if (args.path === '/jobs/test-job') return { state: 'completed', error: null };
      throw new Error('unexpected request: ' + args.path);
    }
    return original(cmd, args);
  };
}

test('switching pipeline after transcription discovers newly created CHAT files', async ({ page }) => {
  await page.addInitScript({ content: stub + `\n(${install.toString()})();\nwindow.__E2E_FILES__ = window.__E2E_FILES__.filter(file => file.kind === 'media');` });
  await page.goto('/');
  await page.getByRole('button', { name: 'open folder…' }).click();
  await page.getByRole('button', { name: '+ add step', exact: true }).click();
  await page.locator('div').filter({ hasText: /^transcribe$/ }).last().click();
  await page.getByRole('button', { name: 'start batch', exact: true }).click();
  await expect(page.getByText('done', { exact: true }).first()).toBeVisible();
  // Model the newly written filesystem artifact at the native scan boundary.
  await page.evaluate(() => (window as any).__E2E_FILES__.push({
    source_id: 'nested/é.cha', filename: 'é.cha', stem: 'é', kind: 'chat', size_bytes: 200, duration_ms: null,
  }));
  await page.getByRole('button', { name: 'remove transcribe', exact: true }).click();
  await page.getByRole('button', { name: '+ add step', exact: true }).click();
  await page.locator('div').filter({ hasText: /^align$/ }).last().click();
  await page.getByRole('button', { name: 'start batch', exact: true }).click();
  await expect(page.getByText('done', { exact: true }).first()).toBeVisible();
  const request = await page.evaluate(() => (window as any).__DESKTOP_REQUEST__);
  expect(request.steps.map((step: any) => step.recipe)).toEqual(['align']);
  expect(request.source_ids).toEqual(['nested/é.cha']);
});
