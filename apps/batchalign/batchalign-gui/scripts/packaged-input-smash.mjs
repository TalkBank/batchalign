// Exercise the installed native parser and atomic publication on every OS.
// Small byte buffers, two workers, reproducible seeds; no model allocations.
import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';

export async function testPackagedInputSmash(base, root, results) {
  const folder = join(root, 'smash input é');
  const output = join(root, 'smash output');
  await mkdir(folder);
  await mkdir(output);
  const valid = Buffer.from('@UTF8\n@Begin\n@Languages:\teng\n@Participants:\tPAR Participant\n@ID:\teng|test|PAR|||||Participant|||\n*PAR:\thello world .\n@End\n');
  const sentinel = Buffer.from('previous output must survive failure');
  const samples = [valid, Buffer.from('not CHAT'), Buffer.from([255, 254, 0])];
  // Keep valid structural variations too, so the corpus exercises the
  // comparison/writer rather than stopping entirely at parser rejection.
  for (let i = 0; i < 64; i++) {
    const sentence = `${'hello '.repeat(1 + i % 12)}world .`;
    samples.push(Buffer.from(valid.toString().replace('hello world .', sentence)
      .replace('@End', `%com:\tUnicode note é ${i}\n@End`)));
  }
  const seeds = [20260920, 731, 65537];
  const fragments = ['\0', '\x15-1_0\x15', '\n@End\n', '\n%mor:\t', '[', ']', '\r\n', 'é', '\n%gra:\t1|1|ROOT']
    .map(text => Buffer.from(text)).concat([Buffer.from([255])]);
  for (const seed of seeds) {
    let state = seed;
    const random = n => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return state % n; };
    for (let i = 0; i < 64; i++) {
      let bytes = valid;
      const edits = 1 + random(8);
      for (let j = 0; j < edits; j++) {
        const start = random(bytes.length + 1);
        const end = Math.min(bytes.length, start + random(20));
        bytes = Buffer.concat([bytes.subarray(0, start), fragments[random(fragments.length)], bytes.subarray(end)]);
      }
      samples.push(bytes);
    }
  }
  const names = samples.map((_, i) => `case-${i}.cha`);
  for (const [i, bytes] of samples.entries()) {
    await writeFile(join(folder, names[i]), bytes);
    await writeFile(join(folder, `case-${i}.gold.cha`), valid);
    await writeFile(join(output, names[i]), sentinel);
  }
  const request = { folder, source_ids: names, output_path: output, workers: 2,
    steps: [{ recipe: 'compare', kwargs: {}, use_cache: false }] };
  const post = body => fetch(`${base}/desktop/jobs`, { method: 'POST',
    headers: { 'content-type': 'application/json' }, body: JSON.stringify(body),
    signal: AbortSignal.timeout(30_000) });
  // Invalid requests must fail before work is scheduled, including traversal.
  for (const source_ids of [[], [names[0], names[0]], ['../outside.cha'], [null], 'case-0.cha']) {
    const response = await post({ ...request, source_ids });
    assert([400, 422].includes(response.status), `invalid input accepted: ${JSON.stringify(source_ids)}: ${response.status}`);
    await response.text();
  }
  async function run(body) {
    const response = await post(body);
    const job = await response.json();
    assert.equal(response.status, 200, JSON.stringify(job));
    const deadline = Date.now() + 120_000;
    while (Date.now() < deadline) {
      const response = await fetch(`${base}/jobs/${job.job_id}`, { signal: AbortSignal.timeout(30_000) });
      assert(response.ok, `job status HTTP ${response.status}`);
      const status = await response.json();
      if (['completed', 'failed', 'cancelled'].includes(status.state)) return status;
      await delay(100);
    }
    throw new Error('native input smash exceeded its deadline');
  }
  const status = await run(request);
  assert.equal(status.state, 'failed', 'known invalid members must fail');
  let completed = 0;
  let preservedFailures = 0;
  for (const [i, bytes] of samples.entries()) {
    assert.deepEqual(await readFile(join(folder, names[i])), bytes, `source changed: ${names[i]}`);
    assert.deepEqual(await readFile(join(folder, `case-${i}.gold.cha`)), valid, `gold changed: ${names[i]}`);
    const actual = await readFile(join(output, names[i]));
    if (actual.equals(sentinel)) preservedFailures++;
    else {
      assert.match(actual.toString(), /%xcmp:/, `partial output published: ${names[i]}`);
      completed++;
    }
    if (i === 0) assert(!actual.equals(sentinel), 'valid member did not complete');
    if (i === 1 || i === 2) assert.deepEqual(actual, sentinel, 'invalid member overwrote prior output');
  }
  assert(completed >= 65 && preservedFailures >= 2);
  const recovered = await run({ ...request, source_ids: [names[0]] });
  assert.equal(recovered.state, 'completed', 'parser failures poisoned the next job');
  results.inputSmash = { seeds, samples: samples.length, rejectedRequests: 5,
    completed, preservedFailures, recovery: recovered.state };
}
