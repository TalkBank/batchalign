// Isolate native Windows acceptance runs from the developer environment.
// Run exclusively: PyApp and pip use Windows known folders even when their
// LOCALAPPDATA/PIP_CACHE_DIR environment variables are overridden.
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { copyFile, lstat, mkdir, mkdtemp, rename } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { promisify } from 'node:util';

const execute = promisify(execFile);

export async function prepareWindowsCleanroom() {
  assert.equal(process.platform, 'win32');
  const root = await mkdtemp(join(tmpdir(), 'ba-clean-'));
  const drivers = join(root, 'drivers');
  await mkdir(drivers);
  const system = join(process.env.SystemRoot, 'System32');
  for (const name of ['tauri-driver.exe', 'msedgedriver.exe']) {
    const { stdout } = await execute(join(system, 'where.exe'), [name]);
    await copyFile(stdout.trim().split(/\r?\n/)[0], join(drivers, name));
  }
  const env = {};
  for (const name of ['SystemRoot', 'WINDIR', 'SystemDrive', 'COMSPEC', 'USERPROFILE',
    'USERNAME', 'HOMEDRIVE', 'HOMEPATH', 'LOCALAPPDATA', 'APPDATA', 'PROGRAMDATA',
    'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMW6432']) {
    const key = Object.keys(process.env).find(key => key.toLowerCase() === name.toLowerCase());
    if (key) env[name] = process.env[key];
  }
  Object.assign(env, {
    PATH: [drivers, system, process.env.SystemRoot].join(';'),
    TEMP: root, TMP: root, PYTHONNOUSERSITE: '1', PYTHONFAULTHANDLER: '1',
    HF_HOME: join(root, 'models'), XDG_CACHE_HOME: join(root, 'cache'),
    STANZA_RESOURCES_DIR: join(root, 'stanza'), NLTK_DATA: join(root, 'nltk'),
    PYANNOTE_CACHE: join(root, 'pyannote'), TORCH_HOME: join(root, 'torch'),
    // Keep setuptools from discovering the host Visual Studio installation.
    DISTUTILS_USE_SDK: '1', MSSdk: '1',
  });
  for (const tool of ['python.exe', 'pip.exe', 'uv.exe', 'cargo.exe', 'cl.exe']) {
    await assert.rejects(execute(join(system, 'where.exe'), [tool], { env, cwd: root }),
      `host build tool available in cleanroom: ${tool}`);
  }

  const caches = [];
  async function restore() {
    for (const entry of [...caches].reverse()) {
      // Retain the test-created cache as evidence; restore the original cache.
      try { await rename(entry.path, entry.generated); }
      catch (error) { if (error.code !== 'ENOENT') throw error; }
      if (entry.hadOriginal) await rename(entry.backup, entry.path);
    }
  }
  try {
    for (const [name, parts] of [['pip', ['pip', 'Cache']], ['pyapp', ['pyapp', 'cache']]]) {
      const path = resolve(process.env.LOCALAPPDATA, ...parts);
      const local = resolve(process.env.LOCALAPPDATA);
      assert(path.toLowerCase().startsWith(`${local.toLowerCase()}\\`));
      const entry = { path, backup: join(root, `${name}-original`),
        generated: join(root, `${name}-generated`), hadOriginal: false };
      try {
        const stat = await lstat(path);
        assert(stat.isDirectory() && !stat.isSymbolicLink(), `unexpected cache path: ${path}`);
        await rename(path, entry.backup);
        entry.hadOriginal = true;
      } catch (error) { if (error.code !== 'ENOENT') throw error; }
      caches.push(entry);
      await assert.rejects(lstat(path), { code: 'ENOENT' });
    }
  } catch (error) {
    await restore();
    throw error;
  }
  return {
    env, driver: join(drivers, 'tauri-driver.exe'), restore,
    evidence: { root, path: env.PATH, caches, freshModelCache: env.HF_HOME,
      pyannoteCache: env.PYANNOTE_CACHE, torchCache: env.TORCH_HOME,
      hostToolsAbsent: ['python', 'pip', 'uv', 'cargo', 'cl'],
      inheritedPythonSettings: false, startedAt: new Date().toISOString() },
  };
}
