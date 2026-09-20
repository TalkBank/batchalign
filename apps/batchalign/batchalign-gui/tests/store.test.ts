import { expect, test } from 'vitest';
import fc from 'fast-check';
import { reducer, useStore, type AppState, type Batch, type FileRow } from '../src/store';
import type { ProgressEvent } from '../src/protocol/events';

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

test('random progress cannot corrupt another batch, revive terminal files, or escape percentage bounds', () => {
  const event = fc.record({
    kind: fc.constantFrom<ProgressEvent['kind']>('StageStarted', 'StageInjected', 'StageSkipped', 'StageFailed', 'SourceCompleted'),
    task: fc.constantFrom<ProgressEvent['task']>('Morphosyntax', 'Translate'),
    completed: fc.integer({ min: -10000, max: 10000 }),
    total: fc.integer({ min: -10, max: 10000 }),
    stale: fc.boolean(),
    label: fc.string({ maxLength: 80 }),
  });
  fc.assert(fc.property(fc.array(event, { minLength: 1, maxLength: 150 }), events => {
    const file: FileRow = { source_id: 'nested/é.cha', filename: 'é.cha', stem: 'é',
      kind: 'chat', sizeBytes: 1, durationMs: null, status: 'queued', log: [],
      stages: [{ verb: 'morphotag', state: 'queued', pct: 0 }, { verb: 'translate', state: 'queued', pct: 0 }] };
    let state: AppState = useStore.getInitialState();
    for (const id of ['a', 'b']) {
      state = reducer(state, { type: 'BATCH_OPENED', batch: { ...batch(id),
        pipeline: ['morphotag', 'translate'], files: { [file.source_id]: structuredClone(file) },
        fileOrder: [file.source_id], jobId: 'current', state: 'running' } });
    }
    const untouched = state.batches.b;
    for (const { stale, ...progress } of events) {
      const before = state;
      const row = before.batches.a.files[file.source_id];
      state = reducer(state, { type: 'PROGRESS_V2', batchId: 'a', jobId: stale ? 'old' : 'current',
        event: { ...progress, source_id: file.source_id } });
      expect(state.batches.b).toBe(untouched);
      if (stale || ['done', 'failed'].includes(row.status)) expect(state).toBe(before);
      const after = state.batches.a.files[file.source_id];
      expect(after.log.length).toBeLessThanOrEqual(200);
      for (const stage of after.stages) {
        expect(Number.isFinite(stage.pct)).toBe(true);
        expect(stage.pct).toBeGreaterThanOrEqual(0);
        expect(stage.pct).toBeLessThanOrEqual(100);
      }
    }
  }), { numRuns: 1000, seed: 20260921 });
});
