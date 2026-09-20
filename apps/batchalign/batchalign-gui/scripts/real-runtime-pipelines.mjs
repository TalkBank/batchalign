// Real inference against the bundled daemon. No model/provider mocks.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
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
  // A lost submission/status response does not prove the model worker stopped.
  // Only terminal job state permits another memory-heavy test in this daemon.
  let workerMayBeRunning = false;
  async function run(recipe, source, kwargs, evidenceKey = recipe) {
    const output = join(root, 'real-model-output', evidenceKey);
    const started = Date.now();
    workerMayBeRunning = true;
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
      if (['completed', 'failed', 'cancelled'].includes(status.state)) {
        workerMayBeRunning = false;
        break;
      }
      await delay(1000);
    }
    results.realPipelines[evidenceKey] = { kwargs, status, durationMs: Date.now() - started };
    assert.equal(status?.state, 'completed', `${recipe}: ${JSON.stringify(status)}`);
    const chat = await readFile(join(output, source.replace(/\.wav$/, '.cha')), 'utf8');
    await writeFile(join(root, `${evidenceKey}-evidence.cha`), chat);
    results.realPipelines[evidenceKey].chat = chat;
    return chat;
  }

  async function check(recipe, test) {
    try { await test(); }
    catch (error) {
      results.realPipelines[recipe] = { ...results.realPipelines[recipe], error: String(error) };
      console.error(`${recipe}: ${error}`);
      if (workerMayBeRunning) throw new Error(
        `${recipe}: worker termination is unconfirmed; stopping daemon before further model tests`,
        { cause: error });
    }
  }

  await check('transcribe', async () => {
  const asr = await run('transcribe', 'en.wav', {
    asr_backend: { kind: 'WhisperBackend', kwargs: { language: 'eng' } },
    speaker_backend: { kind: 'PyannoteBackend', kwargs: { num_speakers: 1 } },
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

  await check('diarize-speakers', async () => {
    // Upstream's public telephone-conversation example includes timed
    // reference turns. Download only this small, immutable fixture on CI.
    const fixture = 'https://raw.githubusercontent.com/pyannote/pyannote-audio/b749285c5cdd4636b2edc7f766f1352c8dde9369/src/pyannote/audio/sample';
    const assets = [
      ['wav', 'c319b4abca767b124e41432d364fd7df006cb26bb79d09326c487d606a134e6e'],
      ['stm', 'f861f3004927e1c4429199f9695bfd252def75d7d5e4bdf735d3d85fd4a667f7'],
    ];
    for (const [extension, checksum] of assets) {
      const response = await fetch(`${fixture}/sample.${extension}`, { signal: AbortSignal.timeout(60_000) });
      assert(response.ok, `speaker fixture HTTP ${response.status}`);
      const bytes = Buffer.from(await response.arrayBuffer());
      assert.equal(createHash('sha256').update(bytes).digest('hex'), checksum, 'speaker fixture changed');
      await writeFile(join(input, `speakers.${extension}`), bytes);
    }
    const reference = (await readFile(join(input, 'speakers.stm'), 'utf8')).trim().split(/\r?\n/).map(line => {
      const [, , speaker, start, end, ...text] = line.split(/\s+/);
      return { speaker, start: Math.round(Number(start) * 1000), end: Math.round(Number(end) * 1000),
        text: text.join(' ').replace(/[^a-zA-Z' ]/g, ' ').replace(/\s+/g, ' ').trim() };
    });
    assert.equal(reference.length, 13);
    const source = '@UTF8\n@Begin\n@Languages:\teng\n@Participants:\tPAR Participant\n'
      + '@ID:\teng|test|PAR|||||Participant|||\n@Media:\tspeakers, audio\n'
      + reference.map(turn => `*PAR:\t${turn.text} . \x15${turn.start}_${turn.end}\x15\n`).join('') + '@End\n';
    await writeFile(join(input, 'speakers.cha'), source);
    const diarized = await run('diarize', 'speakers.cha', {
      speaker_backend: { kind: 'PyannoteBackend', kwargs: { num_speakers: 2 } },
    }, 'diarize-speakers');
    assert.deepEqual(words(diarized), words(source), 'speaker separation changed the spoken words');
    // The native runner may split turns at detected speaker boundaries.
    // Compare labels per preserved word so legitimate splitting is allowed.
    const actual = [...diarized.matchAll(/^\*([^:]+):[^\n]*$/gm)]
      .flatMap(match => words(match[0]).map(() => match[1]));
    const expected = reference.flatMap(turn => words(`*PAR:\t${turn.text} .`).map(() => turn.speaker));
    assert.equal(actual.length, expected.length);
    const labels = [...new Set(actual)];
    assert.equal(labels.length, 2, 'distinct speakers collapsed into one label');
    const goldLabels = [...new Set(reference.map(turn => turn.speaker))];
    const direct = actual.filter((label, index) => labels.indexOf(label) === goldLabels.indexOf(expected[index])).length;
    const agreement = Math.max(direct, expected.length - direct) / expected.length;
    results.realPipelines['diarize-speakers'].wordSpeakerAgreement = agreement;
    results.realPipelines['diarize-speakers'].referenceSpeakers = reference.map(turn => turn.speaker);
    assert(agreement >= 0.8, `speaker assignments disagree with reference: ${agreement}`);
    assert.equal(await readFile(join(input, 'speakers.cha'), 'utf8'), source);
  });

  await check('translate', async () => {
  const translated = await run('translate', 'es.cha', {
    translate_backend: { kind: 'GoogleTranslateBackend', kwargs: { target: 'eng' } },
  });
  assert.match(translated.toLowerCase(), /red apple/, 'missing translated sentence meaning');
  assert.match(translated.toLowerCase(), /song/, 'second utterance was not translated');
  });
  await check('translate-nllb', async () => {
  const translated = await run('translate', 'es.cha', {
    translate_backend: { kind: 'NllbTranslateBackend', kwargs: { target: 'eng' } },
  }, 'translate-nllb');
  assert.match(translated.toLowerCase(), /red apple/, 'local translation lost sentence meaning');
  assert.match(translated.toLowerCase(), /song/, 'local translation lost the second utterance');
  });
  assert.equal(await readFile(join(input, 'en.cha'), 'utf8'), gold, 'source CHAT was modified');
}
