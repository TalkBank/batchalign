// Drives the unmodified installed app through tauri-driver/WebKit or WebView2.
// First launch bootstraps a fresh environment; the second reuses it.
// No Tauri IPC mocks or test hooks are injected into the production bundle.
import assert from 'node:assert/strict';
import { execFile, spawn } from 'node:child_process';
import { once } from 'node:events';
import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { access, mkdtemp, mkdir, readFile, readlink, realpath, writeFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import { prepareWindowsCleanroom } from './windows-cleanroom.mjs';
import { testRealPipelines } from './real-runtime-pipelines.mjs';

const execute = promisify(execFile);

const application = resolve(process.argv[2] || '');
const embedded = process.argv[4] === '--embedded';
// A separate warm run can exercise models without repeating dependency setup.
// It never counts as evidence of a cold bootstrap.
const warm = process.argv.includes('--warm');
if (warm) assert.equal(process.platform, 'win32');
const sidecarReport = JSON.parse(await readFile(process.argv[3], 'utf8'));
assert(process.argv[2] && sidecarReport.root, 'usage: native-webview-smoke.mjs installed-app packaged-report.json');
const evidence = resolve(process.env.BATCHALIGN_NATIVE_EVIDENCE || 'native-webview-evidence');
await mkdir(evidence, { recursive: true });
let environment;
if (process.platform === 'win32') {
  // Exercise the installed app's default path, not a shorter test override.
  const hash = createHash('sha256');
  for await (const chunk of createReadStream(sidecarReport.binary)) hash.update(chunk);
  environment = join(process.env.LOCALAPPDATA, 'Batchalign', 'r', hash.digest('hex').slice(0, 32));
  if (warm) await access(join(environment, 'python', 'python.exe'));
  else await assert.rejects(access(environment), { code: 'ENOENT' }, 'Windows default runtime must start cold');
} else {
  environment = join(await mkdtemp(join(sidecarReport.root, 'native-cleanroom-')), 'environment');
}
const report = { application, environment, initiallyCold: !warm, launches: [], startupProgress: [] };
const cleanroom = process.platform === 'win32' ? await prepareWindowsCleanroom() : null;
if (cleanroom) report.cleanroom = cleanroom.evidence;
async function checkpoint() {
  if (cleanroom) await writeFile(join(evidence, 'report.json'), JSON.stringify(report, null, 2));
}
await checkpoint();
let tail = '';
let driverError;
// Xvfb supplies a display, but no title-bar/window-manager lifecycle.
const windowManager = process.platform === 'linux'
  ? spawn('openbox', [], { stdio: 'ignore' }) : null;
windowManager?.on('error', error => { driverError = error; });
function startDriver() {
  const env = {
    ...process.env, PYAPP_INSTALL_DIR_BATCHALIGN: environment,
    XDG_CACHE_HOME: join(sidecarReport.root, 'cache'), HF_HOME: join(sidecarReport.root, 'models'),
    PYTHONNOUSERSITE: '1', TAURI_WEBDRIVER_PORT: '4444',
  };
  if (cleanroom) {
    for (const key of Object.keys(env)) delete env[key];
    Object.assign(env, cleanroom.env, { TAURI_WEBDRIVER_PORT: '4444' });
  }
  const child = spawn(embedded ? application : cleanroom ? cleanroom.driver : 'tauri-driver', [], {
    stdio: ['ignore', 'pipe', 'pipe'], env,
    ...(cleanroom ? { cwd: cleanroom.evidence.root } : {}),
  });
  for (const pipe of [child.stdout, child.stderr]) pipe.on('data', data => {
    tail = (tail + data).slice(-32768);
  });
  child.on('error', error => { driverError = error; });
  return child;
}
report.instrumentation = embedded ? 'macOS QA build with embedded WebDriver feature' : 'unmodified release app with external WebDriver';
let driver = startDriver();
let session;
async function command(method, path, body) {
  const response = await fetch(`http://127.0.0.1:4444${path}`, {
    method, headers: { 'content-type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(60_000),
  });
  const result = await response.json();
  if (!response.ok || result.error || result.value?.error) {
    report.failedCommand ||= { method, path, script: body?.script };
    throw new Error(JSON.stringify(result));
  }
  return result.value;
}
async function script(code, args = [], async = false) {
  if (embedded && !async) {
    // The macOS plugin's synchronous endpoint stores results in a page global
    // and polls evaluateJavaScript. Its direct-eval endpoint instead keeps the
    // headless WebKit run loop active and delivers results through a native
    // message handler. Restrict that endpoint's re-dispatch to read-only probes:
    // application IPC (including job submission) keeps the async session path.
    return command('POST', '/wdio/eval', {
      timeout_ms: 45000,
      script: `const done = arguments[arguments.length - 1];
        try {
          const value = (function() { ${code} }).apply(null, ${JSON.stringify(args)});
          done({ ok: true, value: value === undefined ? null : value });
        } catch (error) { done({ ok: false, error: String(error) }); }`,
    });
  }
  return command('POST', `/session/${session}/execute/${async ? 'async' : 'sync'}`, { script: code, args });
}
async function invoke(name, args = {}) {
  const result = await script(`const done = arguments[arguments.length - 1];
    window.__TAURI_INTERNALS__.invoke(arguments[0], arguments[1]).then(
      value => done({ value }), error => done({ error: String(error) }));`, [name, args], true);
  assert(!result.error, result.error);
  return result.value;
}
async function screenshot(name) {
  const image = await command('GET', `/session/${session}/screenshot`);
  await writeFile(join(evidence, name), Buffer.from(image, 'base64'));
}
async function clickXPath(xpath) {
  const element = await command('POST', `/session/${session}/element`, { using: 'xpath', value: xpath });
  await command('POST', `/session/${session}/element/${element['element-6066-11e4-a52e-4f735466cecf']}/click`, {});
}
async function waitForUiBatch(timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const state = await script(`const rows = [...document.querySelectorAll('tbody > tr')];
      return { done: rows.some(row => /\\bdone\\b/.test(row.innerText)),
        failed: rows.some(row => /\\bfailed\\b/.test(row.innerText)),
        ready: [...document.querySelectorAll('button')].some(b => b.textContent.trim() === 'start batch' && !b.disabled) };`);
    if (state.failed) throw new Error(await script('return document.body.innerText'));
    if (state.done && state.ready) return;
    await delay(250);
  }
  throw new Error(`UI batch did not finish: ${await script('return document.body.innerText')}`);
}
async function windowsUiComparison(text) {
  const folder = join(sidecarReport.root, 'native-ui-input');
  await mkdir(folder, { recursive: true });
  const fixture = process.env.BATCHALIGN_SMOKE_MODELS === '1' && process.env.BATCHALIGN_NATIVE_CHAT;
  const morphologyInput = fixture ? await readFile(fixture, 'utf8') : text;
  if (fixture) report.chatFixture = { path: resolve(fixture), sha256: createHash('sha256').update(morphologyInput).digest('hex') };
  await writeFile(join(folder, 'é.cha'), morphologyInput);
  await writeFile(join(folder, 'é.gold.cha'), text);
  await clickXPath("//button[contains(., 'open folder')]");
  const { stdout } = await execute('powershell.exe', ['-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File',
    fileURLToPath(new URL('./windows-folder-picker.ps1', import.meta.url)),
    '-Application', application, '-Folder', folder], { timeout: 60_000 });
  report.folderPicker = stdout.trim();
  for (let i = 0; i < 100; i++) {
    if (await script("return [...document.querySelectorAll('button')].some(b => b.textContent.trim() === '+ add command')")) break;
    await delay(200);
  }
  await clickXPath("//button[normalize-space(.)='+ add command']");
  if (process.env.BATCHALIGN_SMOKE_MODELS === '1') {
    await clickXPath("//div[normalize-space(.)='morphotag' and not(*)]");
    await clickXPath("//*[normalize-space(.)='use cache' and not(*)]/parent::div/following-sibling::div/div");
    await clickXPath("//button[normalize-space(.)='start batch']");
    await waitForUiBatch(15 * 60_000);
    const morphology = await readFile(join(folder, 'é.cha'), 'utf8');
    assert.match(morphology, /%mor:/);
    assert.match(morphology, /%gra:/);
    await writeFile(join(evidence, 'windows-ui-morphology.cha'), morphology);
    report.uiMorphology = { folder, completed: true };
    await screenshot('windows-ui-morphology.png');
    await checkpoint();
    // Comparison uses its known exact-match fixture. Real conversations with
    // repeated phrases are a separate comparison-quality test.
    await writeFile(join(folder, 'é.cha'), text);
    if (fixture) assert.equal(await readFile(fixture, 'utf8'), morphologyInput);
    await clickXPath("//button[normalize-space(.)='+ add command']");
  }
  await clickXPath("//div[normalize-space(.)='compare' and not(*)]");
  await clickXPath("//button[normalize-space(.)='start batch']");
  await waitForUiBatch(120_000);
  const chat = await readFile(join(folder, 'é.cha'), 'utf8');
  const csv = await readFile(join(folder, 'é.compare.csv'), 'utf8');
  const [header, row] = csv.trim().split(/\r?\n/).map(line => line.split(','));
  assert.match(chat, /%xs/);
  assert.equal(Number(row[header.indexOf('wer')]), 0);
  assert.equal(Number(row[header.indexOf('accuracy')]), 1);
  assert.equal(await readFile(join(folder, 'é.gold.cha'), 'utf8'), text);
  report.uiComparison = { folder, wer: 0, accuracy: 1, goldUnchanged: true };
  await screenshot('windows-ui-completed.png');
  await checkpoint();
}
async function closeWindowsApplication() {
  // Edge's WebDriver window is the WebView2 target, not necessarily the host
  // HWND. Send the same WM_CLOSE as the native title-bar button and establish
  // that the host exited before asserting daemon cleanup.
  const closer = spawn('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', `
    $ErrorActionPreference = 'Stop'
    $name = [IO.Path]::GetFileNameWithoutExtension($env:BATCHALIGN_NATIVE_APPLICATION)
    $apps = @(Get-Process -Name $name -ErrorAction SilentlyContinue | Where-Object {
      $_.Path -and [String]::Equals($_.Path, $env:BATCHALIGN_NATIVE_APPLICATION,
        [StringComparison]::OrdinalIgnoreCase)
    })
    if ($apps.Count -ne 1) { throw "Expected one installed app process, found $($apps.Count)" }
    $app = $apps[0]
    if (!$app.CloseMainWindow()) { throw "Could not request native window close for $($app.Id)" }
    if (!$app.WaitForExit(10000)) { throw "Native app survived WM_CLOSE: $($app.Id)" }
    Write-Output "Native app exited after WM_CLOSE: $($app.Id)"
  `], { env: { ...process.env, BATCHALIGN_NATIVE_APPLICATION: application },
    stdio: ['ignore', 'pipe', 'pipe'] });
  let output = '';
  for (const pipe of [closer.stdout, closer.stderr]) pipe.on('data', data => { output += data; });
  const [code] = await once(closer, 'exit');
  (report.nativeCloses ||= []).push({ code, output });
  assert.equal(code, 0, output);
}
async function closeLinuxApplication() {
  const { stdout } = await execute('wmctrl', ['-lp'], { timeout: 10000 });
  const executable = await realpath(application);
  const matches = [];
  for (const line of stdout.trim().split('\n')) {
    const [window, , pid] = line.trim().split(/\s+/);
    if (!/^\d+$/.test(pid || '')) continue;
    try {
      if (await readlink(`/proc/${pid}/exe`) === executable) matches.push({ window, pid });
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
  }
  assert.equal(matches.length, 1, `expected one installed app window: ${JSON.stringify(matches)}`);
  const { window, pid } = matches[0];
  // Ask the window manager to deliver the native close protocol, then prove
  // host exit before ending the WebDriver session or checking the daemon.
  await execute('wmctrl', ['-ic', window], { timeout: 10000 });
  let exited = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    try { await readlink(`/proc/${pid}/exe`); }
    catch (error) {
      if (error.code !== 'ENOENT') throw error;
      exited = true;
      break;
    }
    await delay(100);
  }
  (report.nativeCloses ||= []).push({ pid, window, exited });
  assert(exited, `native app ${pid} survived window-manager close`);
}
async function waitForDriver() {
  for (let i = 0; i < 100; i++) {
    if (driverError) throw driverError;
    if (driver.exitCode !== null) throw new Error(`driver exited: ${tail}`);
    try { await command('GET', '/status'); return; } catch { await delay(200); }
  }
  throw new Error(`driver never became ready: ${tail}`);
}
try {
  await waitForDriver();
  for (let launch = 0; launch < 2; launch++) {
    if (launch > 0 && embedded) { driver = startDriver(); await waitForDriver(); }
    const started = Date.now();
    const created = await command('POST', '/session', { capabilities: { alwaysMatch: embedded ? {} : {
      browserName: 'wry', 'tauri:options': { application },
    } } });
    session = created.sessionId;
    assert(session, JSON.stringify(created));
    await command('POST', `/session/${session}/timeouts`, { script: 45000,
      ...(cleanroom ? { implicit: 10000 } : {}) });
    await screenshot(`launch-${launch}.png`);
    let bridgeReady = false;
    for (let i = 0; i < 100; i++) {
      bridgeReady = await script('return Boolean(window.__TAURI_INTERNALS__?.invoke)');
      if (bridgeReady) break;
      await delay(200);
    }
    assert(bridgeReady, 'native IPC bridge did not initialize');
    let ready = false;
    const deadline = Date.now() + (launch === 0 && !warm ? 16 * 60_000 : 60_000);
    while (Date.now() < deadline) {
      const view = await script(`const overlay = document.querySelector('[role="dialog"][aria-modal="true"]');
        return { ready: !overlay && Array.from(document.querySelectorAll('button')).some(button => button.textContent.includes('open folder')),
          progress: overlay?.querySelector('[aria-live="polite"][title]')?.textContent || null,
          error: overlay?.querySelector('pre')?.textContent || null };`);
      assert(!view.error, view.error);
      if (view.progress && report.startupProgress.at(-1)?.line !== view.progress) {
        report.startupProgress.push({ launch, elapsedMs: Date.now() - started, line: view.progress });
        await checkpoint();
        if (report.startupProgress.length === 1) await screenshot('cold-start-progress.png');
      }
      if (view.ready) { ready = true; break; }
      await delay(500);
    }
    assert(ready, await script('return document.body.innerText'));
    if (launch === 0 && !warm) assert(report.startupProgress.length > 0, 'cold startup showed no bootstrap progress');
    const port = await invoke('ensure_daemon');
    assert(Number.isInteger(port) && port > 0);
    const capabilities = await invoke('daemon_request', { method: 'GET', path: '/capabilities', body: null });
    if (process.platform === 'win32') await access(join(environment, 'python', 'python.exe'));
    for (const recipe of ['transcribe', 'diarize', 'align', 'morphotag', 'translate', 'compare']) {
      assert(recipe in capabilities.recipes, `missing ${recipe}`);
    }
    await screenshot(`ready-${launch}.png`);
    report.launches.push({ port, durationMs: Date.now() - started });
    await checkpoint();
    if (launch === 0) {
      const folder = join(sidecarReport.root, 'native-input');
      await mkdir(folder, { recursive: true });
      const text = '@UTF8\n@Begin\n@Languages:\teng\n@Participants:\tPAR Participant\n@ID:\teng|test|PAR|||||Participant|||\n*PAR:\thello world .\n@End\n';
      await writeFile(join(folder, 'é.cha'), text);
      await writeFile(join(folder, 'é.gold.cha'), text);
      const files = await invoke('list_folder_files', { path: folder });
      assert(files.files.some(file => file.source_id === 'é.cha'));
      const output = join(sidecarReport.root, 'native-output');
      const job = await invoke('daemon_request', { method: 'POST', path: '/desktop/jobs', body: {
        folder, source_ids: ['é.cha'], output_path: output, workers: 1,
        steps: [{ recipe: 'compare', kwargs: {}, use_cache: false }],
      } });
      let status;
      for (let i = 0; i < 240; i++) {
        status = await invoke('daemon_request', { method: 'GET', path: `/jobs/${job.job_id}`, body: null });
        if (['completed', 'failed', 'cancelled'].includes(status.state)) break;
        await delay(250);
      }
      assert.equal(status.state, 'completed', JSON.stringify(status));
      const chat = await readFile(join(output, 'é.cha'), 'utf8');
      const csv = await readFile(join(output, 'é.compare.csv'), 'utf8');
      assert.match(chat, /%xs/);
      const [header, row] = csv.trim().split(/\r?\n/).map(line => line.split(','));
      assert.equal(Number(row[header.indexOf('wer')]), 0);
      assert.equal(Number(row[header.indexOf('accuracy')]), 1);
      assert.equal(await readFile(join(folder, 'é.cha'), 'utf8'), text);
      await writeFile(join(evidence, 'output.cha'), chat);
      await writeFile(join(evidence, 'comparison.csv'), csv);
      report.comparison = status;
      if (cleanroom) await windowsUiComparison(text);
      if (cleanroom && process.env.BATCHALIGN_SMOKE_MODELS === '1') {
        const repository = fileURLToPath(new URL('../../../../', import.meta.url));
        await testRealPipelines(`http://127.0.0.1:${port}`, sidecarReport.root, repository, report, checkpoint);
        for (const [recipe, result] of Object.entries(report.realPipelines)) assert(!result.error, `${recipe}: ${result.error}`);
      }
    }
    if (embedded) {
      // Closing the last window stops the embedded server along with the app;
      // its HTTP response may therefore be interrupted by normal shutdown.
      await command('DELETE', `/session/${session}/window`).catch(() => {});
      if (driver.exitCode === null) await Promise.race([once(driver, 'exit'), delay(5000)]);
      assert(driver.exitCode !== null, 'macOS app survived closing its last window');
    } else if (process.platform === 'win32') {
      await closeWindowsApplication();
      await command('DELETE', `/session/${session}`).catch(() => {});
    } else {
      await closeLinuxApplication();
      await command('DELETE', `/session/${session}`).catch(() => {});
    }
    session = undefined;
    // Closing the real window must terminate its daemon, not just its webview.
    let stopped = false;
    for (let i = 0; i < 40; i++) {
      try { await fetch(`http://127.0.0.1:${port}/capabilities`, { signal: AbortSignal.timeout(500) }); }
      catch { stopped = true; break; }
      await delay(250);
    }
    assert(stopped, `daemon ${port} survived app exit`);
    if (cleanroom) { report.launches.at(-1).daemonStoppedAfterClose = true; await checkpoint(); }
  }
} catch (error) {
  report.error = String(error);
  if (session) await screenshot('failure.png').catch(() => {});
  process.exitCode = 1;
} finally {
  if (session) await command('DELETE', `/session/${session}`).catch(() => {});
  windowManager?.kill();
  driver.kill();
  await Promise.race([once(driver, 'exit').catch(() => {}), delay(5000)]);
  report.driverLog = tail;
  if (cleanroom) {
    try {
      await cleanroom.restore();
      report.cleanroom.restoredAt = new Date().toISOString();
    } catch (error) {
      report.error ||= `cleanroom cache restoration failed: ${error}`;
      process.exitCode = 1;
    }
  }
  await writeFile(join(evidence, 'report.json'), JSON.stringify(report, null, 2));
  assert(!report.error, report.error);
}
