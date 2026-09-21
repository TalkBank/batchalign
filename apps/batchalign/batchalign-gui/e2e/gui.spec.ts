// Real packaged-daemon integration. Only OS picker/IPC transport is stubbed;
// backend construction, model inference, HTTP/SSE and output writes are real.
import { test, expect } from '@playwright/test';
import { mkdtempSync, readFileSync, writeFileSync, mkdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const port = Number(process.env.BATCHALIGN_E2E_DAEMON_PORT);
const stub = readFileSync(new URL('./tauri-stubs.js', import.meta.url), 'utf8');

test('real morphotag → compare writes valid CHAT and correct metrics', async ({ page }, testInfo) => {
  test.setTimeout(15 * 60_000);
  expect(port, 'run through the packaged-sidecar harness with BATCHALIGN_SMOKE_GUI=1').toBeGreaterThan(0);
  const root = mkdtempSync(join(tmpdir(), 'batchalign-gui-real-'));
  const nested = join(root, 'nested space');
  mkdirSync(nested);
  const transcript = '@UTF8\n@Begin\n@Languages:\teng\n@Participants:\tPAR Participant\n@ID:\teng|test|PAR|||||Participant|||\n*PAR:\tthe cat sleeps .\n@End\n';
  const source = join(nested, 'é.cha');
  const gold = join(nested, 'é.gold.cha');
  writeFileSync(source, transcript);
  writeFileSync(gold, transcript);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  try {
    await page.addInitScript(({ port, root }) => {
      const w = window as any;
      w.__E2E_DAEMON_PORT__ = port;
      w.__E2E_FOLDER__ = root;
      w.__E2E_FILES__ = ['é.cha', 'é.gold.cha'].map(filename => ({
        source_id: `nested space/${filename}`, filename, stem: filename.slice(0, -4),
        kind: 'chat', size_bytes: 150, duration_ms: null,
      }));
    }, { port, root });
    await page.addInitScript({ content: stub });
    await page.goto('/');
    await expect(page.getByRole('dialog', { name: 'Loading', exact: true })).toHaveCount(0);
    await page.getByRole('button', { name: 'open folder…' }).click();
    await page.getByRole('button', { name: '+ add step', exact: true }).click();
    await page.locator('div').filter({ hasText: /^morphotag$/ }).last().click();
    const morphologySubmitted = page.waitForRequest(request => request.url().endsWith('/desktop/jobs') && request.method() === 'POST');
    await page.getByRole('button', { name: 'start batch', exact: true }).click();
    expect((await morphologySubmitted).postDataJSON().steps.map((step: any) => step.recipe)).toEqual(['morphotag']);
    await expect(page.locator('tbody > tr').getByText('done', { exact: true }).first()).toBeVisible({ timeout: 14 * 60_000 });
    const morphology = readFileSync(source, 'utf8');
    expect(morphology).toContain('%mor:');
    expect(morphology).toContain('%gra:');
    await testInfo.attach('morphology.cha', { body: morphology, contentType: 'text/plain' });
    await expect(page.getByRole('button', { name: 'start batch', exact: true })).toBeEnabled();

    await page.getByRole('button', { name: '+ add step', exact: true }).click();
    await page.locator('div').filter({ hasText: /^compare$/ }).last().click();
    const submitted = page.waitForRequest(request => request.url().endsWith('/desktop/jobs') && request.method() === 'POST');
    await page.getByRole('button', { name: 'start batch', exact: true }).click();
    const request = (await submitted).postDataJSON();
    expect(request.steps.map((step: any) => step.recipe)).toEqual(['morphotag', 'compare']);
    expect(request.source_ids).toEqual(['nested space/é.cha']);
    await expect(page.locator('tbody > tr').getByText('done', { exact: true }).first()).toBeVisible({ timeout: 14 * 60_000 });
    const output = readFileSync(source, 'utf8');
    expect(output).toContain('%mor:');
    // Compare intentionally retains morphology but strips grammar tiers,
    // matching the BA2 output contract. Verify grammar before this step.
    expect(output).not.toContain('%gra:');
    expect(output).toContain('%xs');
    const csv = readFileSync(join(nested, 'é.compare.csv'), 'utf8');
    const [header, row] = csv.trim().split(/\r?\n/).map(line => line.split(','));
    expect(row[header.indexOf('file')]).toBe('é.cha');
    expect(Number(row[header.indexOf('wer')])).toBe(0);
    expect(Number(row[header.indexOf('accuracy')])).toBe(1);
    expect(readFileSync(gold, 'utf8')).toBe(transcript);
    expect(errors).toEqual([]);
    await testInfo.attach('output.cha', { body: output, contentType: 'text/plain' });
    await testInfo.attach('comparison.csv', { body: csv, contentType: 'text/csv' });
    await page.screenshot({ path: testInfo.outputPath('completed.png'), fullPage: true });
  } finally { rmSync(root, { recursive: true, force: true }); }
});
