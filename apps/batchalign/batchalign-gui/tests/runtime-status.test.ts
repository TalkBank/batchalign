import { createServer } from 'node:http';
import { afterEach, expect, test } from 'vitest';
import { readRuntimeStatus } from '../scripts/runtime-status.mjs';

const servers: ReturnType<typeof createServer>[] = [];
afterEach(async () => {
  await Promise.all(servers.splice(0).map(server => new Promise<void>(resolve => server.close(() => resolve()))));
});

async function serve(handler: Parameters<typeof createServer>[0]) {
  const server = createServer(handler);
  servers.push(server);
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  const address = server.address() as { port: number };
  return `http://127.0.0.1:${address.port}/jobs/test`;
}

test('a closed status socket is retried without submitting another job', async () => {
  let requests = 0;
  const methods: string[] = [];
  const url = await serve((request, response) => {
    methods.push(request.method!);
    if (++requests === 1) request.socket.destroy();
    else response.end(JSON.stringify({ state: 'completed', id: 'original' }));
  });
  const retries: unknown[] = [];
  expect(await readRuntimeStatus(url, Date.now() + 5000, retry => retries.push(retry)))
    .toEqual({ state: 'completed', id: 'original' });
  expect(methods).toEqual(['GET', 'GET']);
  expect(retries).toHaveLength(1);
});

test('a persistently unavailable daemon still fails after bounded attempts', async () => {
  let requests = 0;
  const url = await serve(request => { requests++; request.socket.destroy(); });
  await expect(readRuntimeStatus(url, Date.now() + 5000)).rejects.toThrow('fetch failed');
  expect(requests).toBe(3);
});

test('HTTP errors are not treated as transient transport errors', async () => {
  let requests = 0;
  const url = await serve((_request, response) => { requests++; response.writeHead(500).end(); });
  await expect(readRuntimeStatus(url, Date.now() + 5000)).rejects.toThrow('status 500');
  expect(requests).toBe(1);
});

test('an expired pipeline deadline is not extended by retries', async () => {
  await expect(readRuntimeStatus('http://127.0.0.1:1', Date.now() - 1))
    .rejects.toThrow('pipeline deadline exceeded');
});
