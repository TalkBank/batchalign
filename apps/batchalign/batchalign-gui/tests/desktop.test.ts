import { beforeEach, expect, test, vi } from 'vitest';
import fc from 'fast-check';
const native = vi.hoisted(() => ({ invoke: vi.fn() }));
vi.mock('@tauri-apps/api/core', () => ({ invoke: native.invoke }));
import { buildDesktopRequest, buildRecipeKwargs } from '../src/desktop';
import { startBatch } from '../src/hooks/useStartBatch';
import { filterFilesForVerb } from '../src/hooks/useFilteredFiles';
import { useStore, type Batch, type FileRow, type VerbStep } from '../src/store';

const verbs: VerbStep[] = ['transcribe', 'diarize', 'align', 'morphotag', 'translate', 'compare'];
function file(id: string, kind: 'media' | 'chat'): FileRow {
  return { source_id: id, filename: id.split('/').at(-1)!, stem: 'clip', kind,
    sizeBytes: 1, durationMs: null, status: 'queued', stages: [], log: [] };
}
function batch(pipeline: VerbStep[] = ['morphotag', 'translate']): Batch {
  const files = {
    'nested space/é.cha': file('nested space/é.cha', 'chat'),
    'nested space/é.wav': file('nested space/é.wav', 'media'),
    'nested space/é.gold.cha': file('nested space/é.gold.cha', 'chat'),
  };
  return { id: 'batch', name: 'batch', folderPath: '/input', outputPath: '/output', inPlace: false,
    pipeline, config: { transcribe: {}, diarize: {}, align: {}, morphotag: {}, translate: {}, compare: {} },
    files, fileOrder: Object.keys(files), state: 'idle', jobId: null, startedAt: null,
    finishedAt: null, expandedFileId: null };
}

beforeEach(() => {
  vi.resetAllMocks();
  useStore.setState(useStore.getInitialState(), true);
});

test('every selected pipeline step is sent in order with nested source identities', () => {
  fc.assert(fc.property(fc.shuffledSubarray(verbs, { minLength: 1 }), pipeline => {
    const value = batch(pipeline);
    const request = buildDesktopRequest(value, useStore.getInitialState().settings);
    expect(request.steps.map(step => step.recipe)).toEqual(pipeline);
    expect(request.source_ids).toEqual([pipeline[0] === 'transcribe' ? 'nested space/é.wav' : 'nested space/é.cha']);
    expect(request.in_place).toBe(false);
    expect(request.output_path).toBe('/output');
  }), { numRuns: 200, seed: 20260920 });
});

test('alignment uses the choice actually stored by its panel', () => {
  expect(buildRecipeKwargs('align', { aligner: 'WhisperFaBackend' })).toEqual({
    fa_backend: { kind: 'WhisperFaBackend', kwargs: {} },
  });
  expect(buildRecipeKwargs('align', {})).toEqual({
    fa_backend: { kind: 'Wav2Vec2FaBackend', kwargs: {} },
  });
});

test('gold references, output options, cache, and worker settings reach the daemon', () => {
  const value = batch(['align', 'compare']);
  value.config.align = { write_wor: false, use_cache: false };
  value.config.compare = { gold_path: '/gold' };
  const req = buildDesktopRequest(value, { ...useStore.getInitialState().settings, forceCpu: true, defaultWorkers: 1 });
  expect(req.steps[0]).toMatchObject({ strip_word_timing: true, use_cache: false });
  expect(req.steps[1].gold_path).toBe('/gold');
  expect(req).toMatchObject({ workers: 1, force_cpu: true });
});

test('alignment and comparison process main CHAT once, never audio or gold as primary inputs', () => {
  const value = batch();
  for (const verb of ['align', 'compare'] as const) {
    expect(filterFilesForVerb(value.files, value.fileOrder, verb)).toEqual(['nested space/é.cha']);
  }
});

test('double-click submits once and polling recovers terminal status without SSE', async () => {
  const value = batch();
  useStore.getState().dispatch({ type: 'BATCH_OPENED', batch: value });
  native.invoke.mockImplementation(async (command, args) => {
    if (command === 'start_batch_pump') return;
    if (args.path === '/desktop/jobs') return { job_id: 'job' };
    return { state: 'completed', error: null };
  });
  await Promise.all([startBatch(value.id), startBatch(value.id)]);
  expect(native.invoke.mock.calls.filter(([, args]) => args?.path === '/desktop/jobs')).toHaveLength(1);
  expect(useStore.getState().batches.batch.state).toBe('done');
  expect(useStore.getState().batches.batch.files['nested space/é.cha'].stages.map(stage => stage.state)).toEqual(['done', 'done']);
});

test('submission rejection appears in the existing file error log and supports retry', async () => {
  const value = batch();
  useStore.getState().dispatch({ type: 'BATCH_OPENED', batch: value });
  native.invoke.mockRejectedValue(new Error('no output folder'));
  await startBatch(value.id);
  const failed = useStore.getState().batches.batch;
  expect(failed.state).toBe('failed');
  expect(failed.files['nested space/é.cha'].log.at(-1)?.text).toContain('no output folder');
  native.invoke.mockImplementation(async (_, args) => args.path === '/desktop/jobs' ? { job_id: 'retry' } : { state: 'completed' });
  await startBatch(value.id);
  expect(useStore.getState().batches.batch.state).toBe('done');
});

test('late progress from a previous job or a finished file cannot regress the UI', () => {
  const value = batch(['morphotag']);
  const store = useStore.getState();
  store.dispatch({ type: 'BATCH_OPENED', batch: value });
  const row = { ...value.files['nested space/é.cha'], stages: [{ verb: 'morphotag' as const, state: 'queued' as const, pct: 0 }] };
  store.dispatch({ type: 'BATCH_STARTED', batchId: value.id, jobId: 'new', files: [row] });
  const event = { source_id: row.source_id, kind: 'SourceCompleted' as const,
    task: 'Morphosyntax' as const, completed: 1, total: 1, label: null };
  store.dispatch({ type: 'PROGRESS_V2', batchId: value.id, jobId: 'old', event });
  expect(useStore.getState().batches.batch.files[row.source_id].status).toBe('queued');
  store.dispatch({ type: 'PROGRESS_V2', batchId: value.id, jobId: 'new', event });
  store.dispatch({ type: 'PROGRESS_V2', batchId: value.id, jobId: 'new', event: { ...event, kind: 'StageStarted' } });
  expect(useStore.getState().batches.batch.files[row.source_id].status).toBe('done');
});
