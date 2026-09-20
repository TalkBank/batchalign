// Read-only diagnostics for intermittent Windows WebKit teardown hangs.
// Preserve exit codes, streams, and normal Playwright shutdown behavior.
if (process.platform === 'win32') {
  const childProcess = require('node:child_process');
  const spawn = childProcess.spawn;
  childProcess.spawn = function (command, ...args) {
    const child = spawn.call(this, command, ...args);
    if (!/[\\/]webkit-[^\\/]+[\\/]Playwright\.exe$/i.test(String(command))) return child;
    const log = (event, detail) => process.stderr.write(
      `[webkit-process] ${JSON.stringify({ event, pid: child.pid, ...detail })}\n`);
    const streams = () => child.stdio.map((stream, fd) => stream ? {
      fd, destroyed: stream.destroyed, readableEnded: stream.readableEnded,
      writableFinished: stream.writableFinished,
    } : { fd, absent: true });
    log('spawn', {});
    child.once('close', (code, signal) => log('close', { code, signal, streams: streams() }));
    child.once('exit', (code, signal) => {
      log('exit', { code, signal, streams: streams() });
      const timer = setTimeout(() => {
        log('after-exit', { streams: streams() });
        childProcess.execFile('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command',
          "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(conhost|Playwright|WebKit.*)\\.exe$' } | Select-Object ProcessId,ParentProcessId,Name | ConvertTo-Json -Compress"],
        { timeout: 10_000 }, (error, stdout, stderr) => log('remaining-processes', {
          error: error?.message, stdout: stdout.trim(), stderr: stderr.trim(),
        }));
      }, 2000);
      timer.unref();
    });
    return child;
  };
}
