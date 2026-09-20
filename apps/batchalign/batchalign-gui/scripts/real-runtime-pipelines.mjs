// Real inference against the bundled daemon. No model/provider mocks.
import assert from 'node:assert/strict';
import { copyFile, mkdir, readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';

function words(chat) {
  return [...chat.matchAll(/^\*[^:]+:\s*(.*)$/gm)].flatMap(match =>
    match[1].replace(/\x15[^\x15]*\x15/g, '').replace(/&-\S+/g, '').toLowerCase().match(/[a-z]+(?:'[a-z]+)?/g) || []);
}
function wordErrorRate(gold, actual) {
  let previous = Array.from({ length: actual.length + 1 }, (_, i) => i);
  for (let i = 1; i <= gold.length; i++) {
    const row = [i];
    for (let j = 1; j <= actual.length; j++) row[j] = Math.min(
      row[j - 1] + 1, previous[j] + 1, previous[j - 1] + (gold[i - 1] === actual[j - 1] ? 0 : 1));
    previous = row;
  }
  return previous[actual.length] / gold.length;
}

export async function testRealPipelines(base, root, repository, results) {
  const input = join(root, 'real-model-input');
  await mkdir(input, { recursive: true });
  for (const name of ['en.cha', 'en.wav']) await copyFile(join(repository, 'scripts/parity/fixtures/align', name), join(input, name));
  await copyFile(join(repository, 'scripts/parity/fixtures/translate/es.cha'), join(input, 'es.cha'));
  const gold = await readFile(join(input, 'en.cha'), 'utf8');
  results.realPipelines = {};
  async function run(recipe, source, kwargs) {
    const output = join(root, 'real-model-output', recipe);
    const started = Date.now();
    const submitted = await fetch(`${base}/desktop/jobs`, { method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ folder: input, source_ids: [source], output_path: output,
        workers: 1, force_cpu: true, steps: [{ recipe, kwargs, use_cache: false }] }),
      signal: AbortSignal.timeout(30_000),
    });
    const job = await submitted.json();
    assert.equal(submitted.status, 200, JSON.stringify(job));
    const deadline = Date.now() + 30 * 60_000;
    let status;
    while (Date.now() < deadline) {
      const response = await fetch(`${base}/jobs/${job.job_id}`, { signal: AbortSignal.timeout(30_000) });
      assert(response.ok, `status ${response.status}`);
      status = await response.json();
      if (['completed', 'failed', 'cancelled'].includes(status.state)) break;
      await delay(1000);
    }
    results.realPipelines[recipe] = { kwargs, status, durationMs: Date.now() - started };
    assert.equal(status?.state, 'completed', `${recipe}: ${JSON.stringify(status)}`);
    const chat = await readFile(join(output, source.replace(/\.wav$/, '.cha')), 'utf8');
    await writeFile(join(root, `${recipe}-evidence.cha`), chat);
    results.realPipelines[recipe].chat = chat;
    return chat;
  }

  async function check(recipe, test) {
    try { await test(); }
    catch (error) {
      results.realPipelines[recipe] = { ...results.realPipelines[recipe], error: String(error) };
      console.error(`${recipe}: ${error}`);
    }
  }

  await check('transcribe', async () => {
  const asr = await run('transcribe', 'en.wav', {
    asr_backend: { kind: 'WhisperBackend', kwargs: { language: 'eng' } },
  });
  const wer = wordErrorRate(words(gold), words(asr));
  results.realPipelines.transcribe.wer = wer;
  assert(words(asr).length > 20, 'transcription must contain the spoken content');
  assert(wer <= 0.3, `transcription differs substantially from reference: WER=${wer}`);
  assert.match(asr, /\x15\d+_\d+\x15/, 'transcription must include timing');

  });

  await check('align', async () => {
  const aligned = await run('align', 'en.cha', {
    fa_backend: { kind: 'Wav2Vec2FaBackend', kwargs: {} },
  });
  assert.deepEqual(words(aligned), words(gold), 'alignment changed the spoken words');
  assert([...aligned.matchAll(/^%wor:/gm)].length >= 3, 'alignment must write word timing for all utterances');
  for (const [, start, end] of aligned.matchAll(/\x15(\d+)_(\d+)\x15/g)) {
    assert(Number(end) >= Number(start), `reversed timing ${start}_${end}`);
    assert(Number(end) <= 20500, `timing exceeds fixture duration: ${end}`);
  }

  });

  await check('diarize', async () => {
  const diarized = await run('diarize', 'en.cha', {
    speaker_backend: { kind: 'PyannoteBackend', kwargs: { num_speakers: 1 } },
  });
  assert.deepEqual(words(diarized), words(gold), 'diarization lost or changed words');
  const speakers = [...diarized.matchAll(/^\*([^:]+):/gm)].map(match => match[1]);
  assert.equal(speakers.length, 3, 'diarization lost utterances');
  assert.equal(new Set(speakers).size, 1, 'single-speaker fixture received multiple speakers');

  });

  await check('translate', async () => {
  const translated = await run('translate', 'es.cha', {
    translate_backend: { kind: 'GoogleTranslateBackend', kwargs: { target: 'eng' } },
  });
  assert.match(translated.toLowerCase(), /red apple/, 'missing translated sentence meaning');
  assert.match(translated.toLowerCase(), /song/, 'second utterance was not translated');
  });
  assert.equal(await readFile(join(input, 'en.cha'), 'utf8'), gold, 'source CHAT was modified');
}
