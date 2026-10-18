import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
const stub = readFileSync(new URL('./tauri-stubs.js', import.meta.url), 'utf8');

test.beforeEach(async ({ page }) => {
  await page.addInitScript({ content: stub + `\n(${install.toString()})();` });
  await page.goto('/');
  await expect(page.getByRole('dialog')).toBeHidden();
  await expect.poll(() => page.evaluate(() => (window as any).__E2E_EVENT_LISTENERS__.get('tauri://drag-drop')?.length ?? 0)).toBe(1);
});

async function drop(page: import('@playwright/test').Page, path = '/recordings') {
  await page.evaluate(path => (window as any).__E2E_EMIT__('tauri://drag-drop', { paths: [path] }), path);
}
async function add(page: import('@playwright/test').Page, command: string) {
  await page.getByRole('button', { name: '+ add command', exact: true }).click();
  await page.getByText(command, { exact: true }).first().click();
}

test('folder drops replace the current folder and close returns to the drop zone', async ({ page }) => {
  await drop(page, '/bad');
  await expect(page.getByRole('alert')).toContainText('not a directory');
  await expect(page.getByText('drop a folder', { exact: true })).toBeVisible();
  await drop(page);
  await expect(page.getByRole('textbox').first()).toHaveValue('/recordings');
  await add(page, 'speaker');
  await expect(page.getByRole('button', { name: 'speaker', exact: true })).toBeVisible();
  await expect(page.getByText('Speaker recognition identifies', { exact: false })).toBeVisible();
  await expect(page.getByRole('columnheader', { name: 'command', exact: true })).toBeVisible();
  await drop(page, '/second');
  await expect(page.getByRole('textbox').first()).toHaveValue('/second');
  await page.getByRole('button', { name: 'close', exact: true }).click();
  await expect(page.getByText('drop a folder', { exact: true })).toBeVisible();
});

test('language gates and reorders ASR engines, and elapsed ticks without progress events', async ({ page }) => {
  await drop(page);
  await add(page, 'transcribe');
  await expect(page.getByText('Enter a language to see recommended engines.')).toBeVisible();
  await expect(page.getByText('Google GenAI', { exact: false })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'start batch', exact: true })).toBeDisabled();
  await page.getByRole('combobox', { name: 'language', exact: true }).fill('eng');
  await expect(page.getByText('CHAT-Whisper (local)', { exact: true })).toBeVisible();
  await expect(page.getByText('Huggingface Whisper', { exact: false })).toHaveCount(0);
  await page.getByRole('combobox', { name: 'language', exact: true }).fill('yue');
  await expect(page.getByRole('radio', { name: 'Aliyun (cloud)', exact: true })).toBeVisible();
  await expect(page.getByRole('radio', { name: 'FunASR (local)', exact: true })).toBeVisible();
  await expect(page.getByText('CHAT-Whisper (local)', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'start batch', exact: true })).toBeDisabled();
  await page.getByRole('radio', { name: 'Aliyun (cloud)', exact: true }).check();
  await page.getByRole('button', { name: 'start batch', exact: true }).click();
  await expect(page.getByRole('button', { name: 'close', exact: true })).toBeDisabled();
  const elapsed = page.getByText('elapsed', { exact: true }).locator('..');
  await expect(elapsed).toContainText('0:00');
  await expect(elapsed).not.toContainText('0:00', { timeout: 5000 });
  await page.evaluate(() => { (window as any).__JOB_DONE__ = true; });
  await expect(page.getByRole('button', { name: 'reveal outputs' })).toBeVisible();
});

function install() {
  const w = window as any;
  w.__E2E_FILES__ = [{ source_id: 'clip.wav', stem: 'clip', filename: 'clip.wav', size_bytes: 1024, duration_ms: null, kind: 'media' }];
  const original = w.__TAURI_INTERNALS__.invoke;
  w.__TAURI_INTERNALS__.invoke = async (cmd: string, args: any) => {
    if (cmd === 'ensure_daemon') return 43210;
    if (cmd === 'list_folder_files' && args.path === '/bad') throw 'not a directory: /bad';
    if (cmd === 'start_batch_pump') return;
    if (cmd === 'daemon_request') {
      if (args.path === '/capabilities') return { backends_by_task: { ASR: ['WhisperBackend', 'ChatWhisperBackend', 'AliyunAsrBackend', 'FunAudioBackend', 'FunAsrBackend', 'GoogleGenAIBackend', 'OpenAIWhisperBackend', 'Qwen3AsrBackend', 'RevAI', 'TencentAsrBackend', 'QwenAsrBackend', 'MalayalamWav2Vec2Backend'], Speaker: ['PyannoteAIBackend', 'PyannoteBackend'] } };
      if (args.path === '/desktop/jobs') { w.__REQUEST__ = args.body; return { job_id: 'job' }; }
      if (args.path === '/jobs/job') return { state: w.__JOB_DONE__ ? 'completed' : 'running', error: null };
    }
    return original(cmd, args);
  };
}

test('language autocomplete validates codes and recommendations never select an ASR engine', async ({ page }) => {
  await drop(page);
  await add(page, 'transcribe');
  const language = page.getByRole('combobox', { name: 'language', exact: true });
  const start = page.getByRole('button', { name: 'start batch', exact: true });
  await expect(language).toHaveAttribute('placeholder', 'click and enter a three-letter language code.');
  await expect(language).toHaveAttribute('autocorrect', 'off');
  await expect(language).toHaveAttribute('autocapitalize', 'none');
  await expect(language).toHaveAttribute('spellcheck', 'false');
  await language.fill('Chinese');
  await expect(start).toBeDisabled();
  await page.getByRole('option', { name: 'zho — Chinese', exact: true }).click();
  await expect(language).toHaveValue('zho');
  await expect(language).toHaveAttribute('aria-invalid', 'false');
  const recommended = page.getByRole('group', { name: 'Recommended engines' });
  await expect(recommended.getByRole('radio', { name: 'Paraformer-zh (local)', exact: true })).toBeVisible();
  await expect(page.getByRole('radio', { name: 'Rev.AI (cloud)', exact: true })).toBeVisible();
  await expect(page.getByRole('radio', { checked: true })).toHaveCount(0);
  await expect(start).toBeDisabled();
  await page.getByRole('radio', { name: 'Paraformer-zh (local)', exact: true }).check();
  await expect(page.getByText('Recognition engine', { exact: true })).toBeVisible();
  await expect(page.getByRole('radio', { name: 'pyannoteAI (cloud)', exact: true })).toBeChecked();
  await expect(start).toBeEnabled();
  await language.fill('zzz');
  await expect(language).toHaveAttribute('aria-invalid', 'true');
  await expect(page.getByRole('alert')).toContainText('valid three-letter language code');
  await expect(start).toBeDisabled();
  await expect(page.getByRole('radio', { name: 'Rev.AI (cloud)', exact: true })).toHaveCount(0);
  await language.fill('zho');
  await language.press('ArrowDown');
  await language.press('Enter');
  await expect(language).toHaveValue('zho');
  await start.click();
  const request = await page.evaluate(() => (window as any).__REQUEST__);
  expect(request.steps[0].language).toBe('zho');
  expect(request.steps[0].kwargs.asr_backend.kwargs.language).toBe('zho');
  expect(request.steps[0].kwargs.speaker_backend.kind).toBe('PyannoteAIBackend');
});
