import { expect, test } from 'vitest';
import fc from 'fast-check';
import { reducer, useStore, type AppState, type Batch } from '../src/store';

function batch(id: string): Batch {
  return { id, name: id, folderPath: '/fixtures', inPlace: true, outputPath: null,
    pipeline: [], config: { transcribe: {}, diarize: {}, align: {}, morphotag: {}, translate: {}, compare: {} },
    files: {}, fileOrder: [], state: 'idle', jobId: null, startedAt: null,
    finishedAt: null, expandedFileId: null };
}

test('tab actions preserve a valid active tab and never duplicate tabs', () => {
  fc.assert(fc.property(fc.array(fc.record({
    type: fc.constantFrom('open', 'close', 'activate'),
    id: fc.constantFrom('a', 'b', 'c'),
  }), { maxLength: 100 }), actions => {
    let state: AppState = useStore.getInitialState();
    for (const { type, id } of actions) {
      const before = structuredClone(state.batches);
      const oldState = state;
      state = reducer(state, type === 'open' ? { type: 'BATCH_OPENED', batch: batch(id) }
        : { type: type === 'close' ? 'BATCH_CLOSED' : 'BATCH_ACTIVATED', batchId: id });
      expect(oldState.batches).toEqual(before);
      expect(new Set(state.tabOrder).size).toBe(state.tabOrder.length);
      expect([...state.tabOrder].sort()).toEqual(Object.keys(state.batches).sort());
      if (state.activeBatchId !== null) expect(state.batches[state.activeBatchId]).toBeDefined();
    }
  }), { numRuns: 500, seed: 20260920 });
});

test('daemon restart cannot expose capabilities from its previous process', () => {
  let state: AppState = { ...useStore.getInitialState(), capabilities: {
    api_version: 'old', recipes: {}, backends: {}, backends_by_task: {},
    input_kinds: [], job_states: [], endpoints: {},
  }};
  state = reducer(state, { type: 'DAEMON_FAILED', reason: 'crash' });
  state = reducer(state, { type: 'DAEMON_READY', port: 1234 });
  expect(state.capabilities).toBeNull();
});
