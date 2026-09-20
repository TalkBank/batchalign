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
    if (command === 'daemon_request') return { recipes: {}, backend_kinds: {}, languages: [] };
    return original(command, args);
  };
}
