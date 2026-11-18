// Apply a diagnostic timing change to the selected tag's test harness only.
// The released app and sidecar are supplied by the original bundle artifact.
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';

const path = process.argv[2];
assert(path, 'usage: prepare-macos-native-recheck.mjs native-webview-smoke.mjs');
let source = (await readFile(path, 'utf8')).replace(/\r\n/g, '\n');
const original = `    const created = await command('POST', '/session', { capabilities: { alwaysMatch: embedded ? {} : {
      browserName: 'wry', 'tauri:options': { application },
    } } });`;
assert(source.includes(original), 'Tagged session setup differs; review before patching');
source = source.replace(original, `    // The embedded plugin starts its HTTP server before window registration,
    // and each POST /session gives that registration only ten seconds.
    const registrationStarted = Date.now();
    let created;
    for (;;) {
      try {
        created = await command('POST', '/session', { capabilities: { alwaysMatch: embedded ? {} : {
          browserName: 'wry', 'tauri:options': { application },
        } } });
        if (report.failedCommand?.path === '/session') delete report.failedCommand;
        break;
      } catch (error) {
        if (!embedded || driver.exitCode !== null || Date.now() - registrationStarted >= 120_000 ||
            !String(error).includes('"error":"no such window"')) throw error;
        (report.windowRegistrationRetries ||= []).push({ launch, elapsedMs: Date.now() - registrationStarted });
        await delay(500);
      }
    }
    report.sessionRegistrationPolicy = 'Retry only embedded no-such-window during initial registration, bounded to 120 seconds';`);
await writeFile(path, source);
console.log('Prepared bounded embedded-window registration retry');
