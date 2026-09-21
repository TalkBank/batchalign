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
    if (cmd === 'list_folder_files' && w.__SCAN_FAILURE__) throw new Error('folder unavailable');
    if (cmd === 'ensure_daemon') return 43210;
    if (cmd === 'reveal_in_file_manager') {
      if (w.__REVEAL_FAILURE__) throw new Error('folder opener unavailable');
      w.__REVEALED_PATH__ = args.path;
      return;
    }
    if (cmd === 'start_batch_pump') { w.__CURRENT_JOB__ = args; return; }
    if (cmd === 'daemon_request') {
      if (args.path === '/capabilities') return { recipes: {}, backends_by_task: {} };
      if (args.path === '/desktop/jobs') {
        w.__DESKTOP_REQUEST__ = args.body;
        w.__SUBMISSIONS__ = (w.__SUBMISSIONS__ || 0) + 1;
        return { job_id: 'test-job' };
      }
      if (args.path === '/jobs/test-job') return { state: w.__JOB_STATE__ || 'completed', error: null };
      throw new Error('unexpected request: ' + args.path);
    }
    return original(cmd, args);
};
}

for (const outputPath of [null, '/outputs with spaces/é', 'C:\\Outputs with spaces\\é']) {
  test(`reveal outputs opens the completed job destination (${outputPath ?? 'in place'})`, async ({ page }) => {
    await page.addInitScript({ content: stub + `\n(${install.toString()})();` });
    await page.goto('/');
    await page.getByRole('button', { name: 'open folder…' }).click();
    if (outputPath) {
      await page.getByText('in place', { exact: true }).click();
      await page.getByRole('textbox').last().fill(outputPath);
    }
    await page.getByRole('button', { name: '+ add step', exact: true }).click();
    await page.locator('div').filter({ hasText: /^compare$/ }).last().click();
    await page.getByRole('button', { name: 'start batch', exact: true }).click();
    const reveal = page.getByRole('button', { name: 'reveal outputs', exact: true });
    await expect(reveal).toBeVisible();
    // Editing the next job's destination must not change where completed files live.
    if (!outputPath) await page.getByText('in place', { exact: true }).click();
    await page.getByRole('textbox').last().fill('/next job');
    await page.evaluate(() => { (window as any).__REVEAL_FAILURE__ = true; });
    await reveal.click();
    await expect(page.getByRole('alert')).toContainText('folder opener unavailable');
    await page.evaluate(() => { (window as any).__REVEAL_FAILURE__ = false; });
    await reveal.click();
    await expect.poll(() => page.evaluate(() => (window as any).__REVEALED_PATH__)).toBe(outputPath ?? '/fixtures');
    await expect(page.getByRole('alert')).toHaveCount(0);
  });
}

test('completed file waits for terminal job status before the next batch', async ({ page }) => {
  await page.addInitScript({ content: stub + `\n(${install.toString()})();\nwindow.__JOB_STATE__ = 'running';` });
  await page.goto('/');
  await page.getByRole('button', { name: 'open folder…' }).click();
  await page.getByRole('button', { name: '+ add step', exact: true }).click();
  await page.locator('div').filter({ hasText: /^morphotag$/ }).last().click();
  await page.getByRole('button', { name: 'start batch', exact: true }).click();
  await expect.poll(() => page.evaluate(() => Boolean((window as any).__CURRENT_JOB__))).toBe(true);
  await page.evaluate(() => {
    const w = window as any;
    w.__E2E_EMIT__('progress-v2', { ...w.__CURRENT_JOB__, event: {
      source_id: 'nested/é.cha', kind: 'SourceCompleted', task: 'Morphosyntax',
      completed: 1, total: 1, label: null,
    } });
  });
  await expect(page.locator('tbody > tr').getByText('done', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'running…', exact: true })).toBeDisabled();
  await page.evaluate(() => (window as any).__JOB_STATE__ = 'completed');
  await expect(page.getByRole('button', { name: 'start batch', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: '+ add step', exact: true }).click();
  await page.locator('div').filter({ hasText: /^compare$/ }).last().click();
  await page.getByRole('button', { name: 'start batch', exact: true }).click();
  await expect.poll(() => page.evaluate(() => (window as any).__SUBMISSIONS__)).toBe(2);
  await expect(page.getByRole('button', { name: 'start batch', exact: true })).toBeEnabled();
});

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

test('folder refresh failure is visible and a new first step retries discovery', async ({ page }) => {
  await page.addInitScript({ content: stub + `\n(${install.toString()})();` });
  await page.goto('/');
  await page.getByRole('button', { name: 'open folder…' }).click();
  await page.evaluate(() => (window as any).__SCAN_FAILURE__ = true);
  await page.getByRole('button', { name: '+ add step', exact: true }).click();
  await page.locator('div').filter({ hasText: /^morphotag$/ }).last().click();
  await expect(page.getByText(/folder refresh failed:.*folder unavailable/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'start batch', exact: true })).toBeDisabled();
  await page.evaluate(() => (window as any).__SCAN_FAILURE__ = false);
  await page.getByRole('button', { name: 'remove morphotag', exact: true }).click();
  await page.getByRole('button', { name: '+ add step', exact: true }).click();
  await page.locator('div').filter({ hasText: /^compare$/ }).last().click();
  await expect(page.getByText(/folder refresh failed:/)).toHaveCount(0);
  await page.getByRole('button', { name: 'start batch', exact: true }).click();
  await expect(page.getByText('done', { exact: true }).first()).toBeVisible();
});

for (const seed of [20260920, 0xdeadbeef, 0x12345678]) {
  test(`seeded pipeline interaction stress (${seed})`, async ({ page }) => {
    test.setTimeout(90_000);
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.addInitScript({ content: stub + `\n(${install.toString()})();` });
    await page.goto('/');
    await page.getByRole('button', { name: 'open folder…' }).click();
    let state = seed >>> 0;
    const next = (limit: number) => {
      state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
      return state % limit;
    };
    let chain: string[] = [];
    for (let action = 0; action < 80; action++) {
      // Transcription consumes media and must remain first, as the API requires.
      const unused = verbs.filter(verb => !chain.includes(verb) && (verb !== 'transcribe' || chain.length === 0));
      if (!chain.length || (unused.length && next(3) === 0)) {
        const verb = unused[next(unused.length)];
        await page.getByRole('button', { name: '+ add step', exact: true }).click();
        if (chain.length && !chain.includes('transcribe')) {
          await expect(page.locator('div').filter({ hasText: /^transcribe$/ })).toHaveCount(0);
        }
        await page.locator('div').filter({ hasText: new RegExp(`^${verb}$`) }).last().click();
        chain.push(verb);
      } else {
        const verb = chain[next(chain.length)];
        await page.getByRole('button', { name: verb, exact: true }).click();
        if (next(2) === 0) {
          await page.getByRole('button', { name: `remove ${verb}`, exact: true }).click();
          chain = chain.filter(item => item !== verb);
        }
      }
      for (const verb of verbs) {
        await expect(page.getByRole('button', { name: verb, exact: true })).toHaveCount(chain.includes(verb) ? 1 : 0);
      }
      if (chain.length && action % 8 === 0) {
        await page.getByRole('button', { name: 'start batch', exact: true }).click();
        await expect(page.getByText('done', { exact: true }).first()).toBeVisible();
        const submitted = await page.evaluate(() => (window as any).__DESKTOP_REQUEST__);
        expect(submitted.steps.map((step: any) => step.recipe)).toEqual(chain);
        expect(submitted.source_ids).toEqual([chain[0] === 'transcribe' ? 'nested/é.wav' : 'nested/é.cha']);
      }
    }
    expect(errors).toEqual([]);
  });
}
