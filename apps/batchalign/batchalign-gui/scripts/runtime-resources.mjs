// External sampling stays responsive even when a model holds Python's GIL.
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execute = promisify(execFile);

export async function monitorRuntimeResources(results) {
  if (process.platform !== 'darwin') return async () => {};
  let pending;
  async function sample() {
    const commands = [
      ['/usr/bin/vm_stat', []],
      ['/usr/sbin/sysctl', ['vm.swapusage']],
      // Exclude command arguments and environment variables from diagnostics.
      ['/bin/ps', ['-axo', 'pid,ppid,rss,%cpu,comm']],
    ];
    const readings = await Promise.allSettled(commands.map(([file, args]) =>
      execute(file, args, { timeout: 5000, maxBuffer: 256 * 1024 })));
    const values = readings.map((reading, index) => {
      if (reading.status === 'rejected') return { error: String(reading.reason) };
      const output = reading.value.stdout.trim();
      return index === 2
        ? output.split('\n').filter((line, i) => i === 0 || /python|sidecar|batchalign/i.test(line)).join('\n')
        : output;
    });
    const entry = { at: new Date().toISOString(), pipeline: results.activePipeline,
      vm: values[0], swap: values[1], processes: values[2] };
    (results.resourceSamples ||= []).push(entry);
    console.log(`[runtime-resources] ${JSON.stringify(entry)}`);
  }
  await sample();
  const timer = setInterval(() => {
    if (!pending) pending = sample().finally(() => { pending = undefined; });
  }, 60_000);
  timer.unref();
  return async () => {
    clearInterval(timer);
    await pending;
  };
}
