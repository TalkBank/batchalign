import assert from 'node:assert/strict';
import { setTimeout as delay } from 'node:timers/promises';

// Retry only this read-only observation, never the job submission. A closed
// keep-alive socket does not establish that the model worker has died.
export async function readRuntimeStatus(url, deadline, onRetry = () => {}) {
  for (let attempt = 0; attempt < 3; attempt++) {
    const remaining = deadline - Date.now();
    assert(remaining > 0, 'pipeline deadline exceeded while reading status');
    let response;
    try {
      response = await fetch(url, {
        headers: { connection: 'close' },
        signal: AbortSignal.timeout(Math.min(30_000, remaining)),
      });
    } catch (error) {
      if (attempt === 2 || !(error instanceof TypeError || error.name === 'TimeoutError')) throw error;
      onRetry({ attempt: attempt + 1, error: String(error), cause: String(error.cause || '') });
      await delay(Math.min(250, Math.max(0, deadline - Date.now())));
      continue;
    }
    assert(response.ok, `status ${response.status}`);
    return await response.json();
  }
}
