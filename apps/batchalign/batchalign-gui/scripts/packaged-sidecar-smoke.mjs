// Run on disposable CI runners against the sidecar extracted from a bundle.
// This proves cold/warm bootstrap + native comparison/output, not webview UI.
import { spawn } from 'node:child_process';
import { mkdtemp, mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { once } from 'node:events';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { testRealPipelines } from './real-runtime-pipelines.mjs';
import { testPackagedInputSmash } from './packaged-input-smash.mjs';
import { monitorRuntimeResources } from './runtime-resources.mjs';

const cli = process.argv[2] === '--cli';
const binary = cli ? 'just' : resolve(process.argv[2] || '');
const repository = resolve(dirname(fileURLToPath(import.meta.url)), '../../../..');
assert(process.argv[2], 'usage: node packaged-sidecar-smoke.mjs /path/to/packaged/sidecar (or --cli to validate the harness)');
const root = await mkdtemp(join(tmpdir(), 'batchalign-packaged-'));
const reportPath = resolve(process.env.BATCHALIGN_SMOKE_REPORT || 'packaged-sidecar-report.json');
const results = { mode: cli ? 'cli-harness' : 'packaged-sidecar', binary, root, launches: [], processes: [], comparison: null };
async function checkpoint() {
  const temporary = `${reportPath}.tmp`;
  await writeFile(temporary, JSON.stringify(results, null, 2));
  await rename(temporary, reportPath);
}
let child;
let exited;
let tail = '';
const env = { ...process.env, BATCHALIGN_API_ALLOW_PATHS: '1',
  PYAPP_INSTALL_DIR_BATCHALIGN: join(root, 'environment'),
  XDG_CACHE_HOME: join(root, 'cache'), HF_HOME: join(root, 'models'),
  PYTHONNOUSERSITE: '1', PYTHONFAULTHANDLER: '1', BATCHALIGN_DIAGNOSTIC_TRACEBACKS: '1' };

async function stop() {
  if (!child?.pid || child.exitCode !== null) return;
  results.processes.findLast(process => process.pid === child.pid).requestedStop = true;
  if (process.platform === 'win32') {
    const killer = spawn('taskkill', ['/pid', String(child.pid), '/T', '/F']);
    await once(killer, 'exit');
  } else {
    try { process.kill(-child.pid, 'SIGTERM'); } catch (error) { if (error.code !== 'ESRCH') throw error; }
    const timer = setTimeout(() => {
      try { process.kill(-child.pid, 'SIGKILL'); } catch {}
    }, 5000);
    await exited;
    clearTimeout(timer);
  }
}

async function boot() {
  const started = Date.now();
  tail = '';
  const prefix = cli ? ['--justfile', join(repository, 'justfile'), 'batchalign', 'cli', 'daemon'] : [];
  child = spawn(binary, [...prefix, '--port', '0', '--host', '127.0.0.1', '--no-access-log'], {
    env, cwd: root, detached: process.platform !== 'win32', stdio: ['ignore', 'pipe', 'pipe'],
  });
  const processRecord = { pid: child.pid, startedAt: new Date().toISOString(), requestedStop: false };
  results.processes.push(processRecord);
  child.once('exit', (code, signal) => Object.assign(processRecord, {
    code, signal, exitedAt: new Date().toISOString(),
  }));
  exited = once(child, 'exit');
  // Install error handlers immediately, including executable/spawn failures.
  exited.catch(() => {});
  const port = await new Promise((accept, reject) => {
    let stdout = '';
    const timeout = setTimeout(() => reject(new Error(`bootstrap exceeded 20 minutes\n${tail}`)), 20 * 60_000);
    const settle = callback => value => { clearTimeout(timeout); callback(value); };
    child.once('error', settle(reject));
    child.once('exit', (code, signal) => settle(reject)(new Error(`sidecar exited ${code}/${signal}\n${tail}`)));
    for (const pipe of [child.stdout, child.stderr]) pipe.on('data', chunk => {
      tail = (tail + chunk.toString()).slice(-32_768);
      process.stdout.write(chunk);
    });
    child.stdout.on('data', chunk => {
      stdout = (stdout + chunk.toString()).slice(-4096);
      const match = stdout.match(/(?:^|\n)DAEMON_PORT=(\d+)\r?\n/);
      if (match && Number(match[1]) > 0) settle(accept)(Number(match[1]));
    });
  });
  const base = `http://127.0.0.1:${port}`;
  const response = await fetch(`${base}/capabilities`, { signal: AbortSignal.timeout(30_000) });
  if (!response.ok) throw new Error(`capabilities: ${response.status} ${await response.text()}`);
  const caps = await response.json();
  for (const verb of ['transcribe', 'diarize', 'align', 'morphotag', 'translate', 'compare']) {
    assert(verb in caps.recipes, `missing recipe ${verb}`);
  }
  results.launches.push({ durationMs: Date.now() - started, port });
  await checkpoint();
  return base;
}

try {
  await boot();
  await stop();
  const base = await boot();
  const input = join(root, 'input', 'nested space');
  await mkdir(input, { recursive: true });
  const transcript = '@UTF8\n@Begin\n@Languages:\teng\n@Participants:\tPAR Participant\n@ID:\teng|test|PAR|||||Participant|||\n*PAR:\thello world .\n@End\n';
  await writeFile(join(input, 'é.cha'), transcript);
  await writeFile(join(input, 'é.gold.cha'), transcript);
  const output = join(root, 'output');
  const response = await fetch(`${base}/desktop/jobs`, { method: 'POST',
    headers: { 'content-type': 'application/json' }, body: JSON.stringify({
      folder: dirname(input), source_ids: ['nested space/é.cha'], output_path: output,
      steps: [{ recipe: 'compare', kwargs: {}, use_cache: false }], workers: 1,
    }), signal: AbortSignal.timeout(30_000) });
  const body = await response.json();
  assert.equal(response.status, 200, JSON.stringify(body));
  const events = await fetch(`${base}/jobs/${body.job_id}/events`, { signal: AbortSignal.timeout(120_000) });
  const eventText = await events.text();
  assert.match(eventText, /SourceCompleted/);
  assert.match(eventText, /data: completed/);
  const status = await (await fetch(`${base}/jobs/${body.job_id}`)).json();
  assert.equal(status.state, 'completed', JSON.stringify(status));
  const chat = await readFile(join(output, 'nested space', 'é.cha'), 'utf8');
  const csv = await readFile(join(output, 'nested space', 'é.compare.csv'), 'utf8');
  assert.match(chat, /%xs/);
  assert.match(csv, /wer/);
  const [header, row] = csv.trim().split(/\r?\n/).map(line => line.split(','));
  assert.equal(row[header.indexOf('file')], 'é.cha');
  assert.equal(Number(row[header.indexOf('wer')]), 0);
  assert.equal(Number(row[header.indexOf('accuracy')]), 1);
  assert.equal(await readFile(join(input, 'é.cha'), 'utf8'), transcript);
  results.comparison = { status, chat, csv, events: eventText };
  await checkpoint();
  await testPackagedInputSmash(base, root, results);
  await checkpoint();
  if (process.env.BATCHALIGN_SMOKE_MODELS === '1') {
    const stopMonitoring = await monitorRuntimeResources(results);
    try { await testRealPipelines(base, root, repository, results, checkpoint); }
    finally { await stopMonitoring(); }
  }
  if (process.env.BATCHALIGN_SMOKE_GUI === '1') {
    const gui = resolve(dirname(fileURLToPath(import.meta.url)), '..');
    const browser = spawn(process.execPath, [join(gui, 'node_modules/playwright/cli.js'),
      'test', 'e2e/gui.spec.ts', '--project=chromium'], {
      cwd: gui, stdio: 'inherit',
      env: { ...process.env, BATCHALIGN_E2E_DAEMON_PORT: String(new URL(base).port) },
    });
    const [code] = await once(browser, 'exit');
    assert.equal(code, 0, 'real-daemon GUI pipeline test failed');
    results.gui = 'passed: morphotag → compare with real outputs';
  }
  for (const [recipe, result] of Object.entries(results.realPipelines || {})) {
    assert(!result.error, `${recipe}: ${result.error}`);
  }
} catch (error) {
  results.error = String(error);
  results.errorDetail = { stack: error.stack, cause: error.cause?.stack || String(error.cause || '') };
  results.tail = tail;
  process.exitCode = 1;
} finally {
  await stop();
  await checkpoint();
  console.log(`Smoke report: ${reportPath}`);
}
