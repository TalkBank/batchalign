// Drives the unmodified installed app through tauri-driver/WebKit or WebView2.
// The warm environment came from this bundle's cleanroom sidecar check.
// No Tauri IPC mocks or test hooks are injected into the production bundle.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';

const application = resolve(process.argv[2] || '');
const embedded = process.argv[4] === '--embedded';
const sidecarReport = JSON.parse(await readFile(process.argv[3], 'utf8'));
assert(process.argv[2] && sidecarReport.root, 'usage: native-webview-smoke.mjs installed-app packaged-report.json');
const evidence = resolve('native-webview-evidence');
await mkdir(evidence, { recursive: true });
const report = { application, environment: 'warm bundle-specific cleanroom environment', launches: [] };
let tail = '';
let driverError;
function startDriver() {
  const child = spawn(embedded ? application : process.platform === 'win32' ? 'tauri-driver.exe' : 'tauri-driver', [], {
    stdio: ['ignore', 'pipe', 'pipe'], env: {
      ...process.env, PYAPP_INSTALL_DIR_BATCHALIGN: join(sidecarReport.root, 'environment'),
      XDG_CACHE_HOME: join(sidecarReport.root, 'cache'), HF_HOME: join(sidecarReport.root, 'models'),
      PYTHONNOUSERSITE: '1', TAURI_WEBDRIVER_PORT: '4444',
    },
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
  if (!response.ok || result.value?.error) throw new Error(JSON.stringify(result));
  return result.value;
}
async function script(code, args = [], async = false) {
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
    await command('POST', `/session/${session}/timeouts`, { script: 45000 });
    await screenshot(`launch-${launch}.png`);
    let bridgeReady = false;
    for (let i = 0; i < 100; i++) {
      bridgeReady = await script('return Boolean(window.__TAURI_INTERNALS__?.invoke)');
      if (bridgeReady) break;
      await delay(200);
    }
    assert(bridgeReady, 'native IPC bridge did not initialize');
    const port = await invoke('ensure_daemon');
    assert(Number.isInteger(port) && port > 0);
    const capabilities = await invoke('daemon_request', { method: 'GET', path: '/capabilities', body: null });
    for (const recipe of ['transcribe', 'diarize', 'align', 'morphotag', 'translate', 'compare']) {
      assert(recipe in capabilities.recipes, `missing ${recipe}`);
    }
    let ready = false;
    for (let i = 0; i < 100; i++) {
      ready = await script(`return !document.querySelector('[role="dialog"][aria-modal="true"]') &&
        Array.from(document.querySelectorAll('button')).some(button => button.textContent.includes('open folder'));`);
      if (ready) break;
      await delay(200);
    }
    assert(ready, await script('return document.body.innerText'));
    await screenshot(`ready-${launch}.png`);
    report.launches.push({ port, durationMs: Date.now() - started });
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
    }
    if (embedded) {
      // Closing the last window stops the embedded server along with the app;
      // its HTTP response may therefore be interrupted by normal shutdown.
      await command('DELETE', `/session/${session}/window`).catch(() => {});
      if (driver.exitCode === null) await Promise.race([once(driver, 'exit'), delay(5000)]);
      assert(driver.exitCode !== null, 'macOS app survived closing its last window');
    } else {
      await command('DELETE', `/session/${session}`);
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
  }
} catch (error) {
  report.error = String(error);
  if (session) await screenshot('failure.png').catch(() => {});
  process.exitCode = 1;
} finally {
  if (session) await command('DELETE', `/session/${session}`).catch(() => {});
  driver.kill();
  await Promise.race([once(driver, 'exit').catch(() => {}), delay(5000)]);
  report.driverLog = tail;
  await writeFile(join(evidence, 'report.json'), JSON.stringify(report, null, 2));
  assert(!report.error, report.error);
}
