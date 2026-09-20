import { beforeEach, expect, test, vi } from 'vitest';
import fc from 'fast-check';

const native = vi.hoisted(() => ({ listen: vi.fn(), invoke: vi.fn() }));
vi.mock('@tauri-apps/api/event', () => ({ listen: native.listen }));
vi.mock('@tauri-apps/api/core', () => ({ invoke: native.invoke }));
import { bootBridge } from '../src/bridge';
import { useStore } from '../src/store';

const initial = useStore.getInitialState();
const capabilities = { recipes: {}, backends: {}, backends_by_task: {} };
let listeners: Map<string, Set<(event: { payload: any }) => void>>;
const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };
function emit(event: string, payload: unknown) {
  for (const cb of listeners.get(event) ?? []) cb({ payload });
}

beforeEach(() => {
  vi.resetAllMocks();
  useStore.setState(initial, true);
  listeners = new Map();
  native.listen.mockImplementation(async (event, cb) => {
    const callbacks = listeners.get(event) ?? new Set();
    callbacks.add(cb);
    listeners.set(event, callbacks);
    return () => callbacks.delete(cb);
  });
  native.invoke.mockImplementation(async (command) => {
    if (command === 'ensure_daemon') throw 'daemon still starting';
    return capabilities;
  });
});

test('warm startup uses the returned port when the event was missed', async () => {
  native.invoke.mockImplementation(async command => command === 'ensure_daemon' ? 1234 : capabilities);
  const cleanup = bootBridge();
  await flush();
  expect(useStore.getState().daemon.ready).toBe(true);
  expect(useStore.getState().capabilities).toEqual(capabilities);
  cleanup();
});

test('a late capabilities response cannot undo a daemon failure', async () => {
  let resolve!: (value: unknown) => void;
  native.invoke.mockImplementation(async command => {
    if (command === 'ensure_daemon') throw 'daemon still starting';
    return new Promise(r => { resolve = r; });
  });
  const cleanup = bootBridge();
  await flush();
  emit('daemon-ready', { port: 1234 });
  emit('daemon-failed', { reason: 'process exited' });
  resolve(capabilities);
  await flush();
  expect(useStore.getState().capabilities).toBeNull();
  expect(useStore.getState().daemon.error).toBe('process exited');
  cleanup();
});

test('registration that finishes after unmount is immediately cleaned up', async () => {
  const registrations: Array<() => void> = [];
  const off = vi.fn();
  native.listen.mockImplementation(() => new Promise(resolve => registrations.push(() => resolve(off))));
  const cleanup = bootBridge();
  cleanup();
  registrations.forEach(resolve => resolve());
  await flush();
  expect(off).toHaveBeenCalledTimes(4);
  expect(native.invoke).not.toHaveBeenCalled();
});

test('randomized remounts and duplicate readiness keep one subscription and one handshake', async () => {
  await fc.assert(fc.asyncProperty(
    fc.array(fc.boolean(), { minLength: 1, maxLength: 40 }),
    fc.integer({ min: 1, max: 65535 }),
    async (settleBeforeUnmount, port) => {
      useStore.setState(initial, true);
      for (const settle of settleBeforeUnmount) {
        const dispose = bootBridge();
        if (settle) await flush();
        dispose();
      }
      const cleanup = bootBridge();
      await flush();
      for (const callbacks of listeners.values()) expect(callbacks.size).toBe(1);
      const before = native.invoke.mock.calls.filter(([c]) => c === 'daemon_request').length;
      for (let i = 0; i < 5; i++) emit('daemon-ready', { port });
      await flush();
      expect(native.invoke.mock.calls.filter(([c]) => c === 'daemon_request').length - before).toBe(1);
      expect(useStore.getState().daemon.port).toBe(port);
      cleanup();
      await flush();
      for (const callbacks of listeners.values()) expect(callbacks.size).toBe(0);
    },
  ), { numRuns: 100, seed: 20260920 });
});
