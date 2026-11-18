import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

const stub = readFileSync(new URL('./tauri-stubs.js', import.meta.url), 'utf8');

for (const mode of ['warm', 'cold', 'failure'] as const) {
  test(`startup: ${mode}`, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    // Keep installation and overrides in one script: ordering between
    // separate addInitScript calls is deliberately unspecified.
    await page.addInitScript({ content: stub + `\n(${install.toString()})(${JSON.stringify(mode)});` });
    await page.goto('/');
    if (mode !== 'warm') {
      await expect(page.getByRole('dialog', { name: 'Loading', exact: true })).toBeVisible();
      await page.evaluate(() => (window as any).__E2E_EMIT__('daemon-progress', { line: 'Installing dependencies: 3 of 8' }));
      await expect(page.getByText('Installing dependencies: 3 of 8', { exact: true })).toBeVisible();
      await page.evaluate(({ mode }) => (window as any).__E2E_EMIT__(
        mode === 'cold' ? 'daemon-ready' : 'daemon-failed',
        mode === 'cold' ? { port: 43210 } : { reason: 'installation failed: disk full' },
      ), { mode });
    }
    if (mode === 'failure') {
      await expect(page.getByRole('dialog', { name: 'Loading failed' })).toBeVisible();
      await expect(page.getByText('installation failed: disk full', { exact: true })).toBeVisible();
    } else {
      await expect(page.getByRole('dialog')).toBeHidden();
      await page.getByRole('button', { name: 'open folder…' }).click({ trial: true });
    }
    expect(errors).toEqual([]);
  });
}

function install(mode: string) {
  const w = window as any;
  const original = w.__TAURI_INTERNALS__.invoke;
  w.__TAURI_INTERNALS__.invoke = async (command: string, args: unknown) => {
    if (command === 'ensure_daemon') {
      if (mode === 'warm') return 43210;
      throw 'daemon still starting; listen for `daemon-ready`';
    }
    if (command === 'daemon_request') return { recipes: {}, backend_kinds: {}, backends_by_task: {}, languages: [] };
    return original(command, args);
  };
}

for (const repair of [false, true]) {
  test(`failed startup can ${repair ? 'repair' : 'retry'} without relaunch`, async ({ page }) => {
    await page.addInitScript({ content: stub + `\n(${install.toString()})('failure');` });
    await page.goto('/');
    await expect(page.getByRole('dialog', { name: 'Loading', exact: true })).toBeVisible();
    await page.evaluate(() => {
      const w = window as any;
      const original = w.__TAURI_INTERNALS__.invoke;
      w.__TAURI_INTERNALS__.invoke = async (command: string, args: any) => {
        if (command === 'retry_daemon') {
          w.__REPAIR_REQUEST__ = args.repair;
          w.__E2E_EMIT__('daemon-ready', { port: 43210 });
          return;
        }
        return original(command, args);
      };
      w.__E2E_EMIT__('daemon-failed', { reason: 'installation interrupted' });
    });
    await page.getByRole('button', { name: repair ? 'Repair installation' : 'Retry', exact: true }).click();
    await expect(page.getByRole('dialog')).toBeHidden();
    expect(await page.evaluate(() => (window as any).__REPAIR_REQUEST__)).toBe(repair);
  });
}

test('Rev key is saved, cleared from the field, and configured on reopening Settings', async ({ page }) => {
  await page.addInitScript({ content: stub + `\n(${install.toString()})('warm');
    const invoke = window.__TAURI_INTERNALS__.invoke;
    let configured = false;
    window.__TAURI_INTERNALS__.invoke = async (command, args) => {
      if (command === 'daemon_request' && args.path === '/desktop/settings/revai') {
        if (args.method === 'PUT') configured = args.body.key === 'test-secret';
        return { configured, from_environment: false };
      }
      return invoke(command, args);
    };` });
  await page.goto('/');
  await page.getByRole('button', { name: 'settings', exact: true }).click();
  await page.getByText('asr engines', { exact: true }).first().click();
  const input = page.getByLabel('Rev.AI API key');
  await input.fill('test-secret');
  await page.getByRole('button', { name: 'save key', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Saved.');
  await expect(input).toHaveValue('');
  await page.getByRole('button', { name: 'close', exact: true }).click();
  await page.getByRole('button', { name: 'settings', exact: true }).click();
  await page.getByText('asr engines', { exact: true }).first().click();
  await expect(page.getByLabel('Rev.AI API key')).toHaveAttribute('placeholder', 'key configured');
});

test('a running runtime can be repaired from Settings and reports a preparation failure', async ({ page }) => {
  await page.addInitScript({ content: stub + `\n(${install.toString()})('warm');
    const invoke = window.__TAURI_INTERNALS__.invoke;
    window.__TAURI_INTERNALS__.invoke = async (command, args) => {
      if (command === 'repair_runtime') throw 'Could not prepare runtime repair: access denied';
      return invoke(command, args);
    };` });
  await page.goto('/');
  await page.getByRole('button', { name: 'settings', exact: true }).click();
  await page.getByText('paths', { exact: true }).click();
  const repair = page.getByRole('button', { name: 'Repair and restart', exact: true });
  await repair.click();
  await expect(page.getByRole('alert')).toContainText('access denied');
  await expect(repair).toBeEnabled();
});
