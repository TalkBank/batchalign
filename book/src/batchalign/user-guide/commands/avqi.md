# Measure acoustic voice quality

Install the optional Praat bindings:

```bash
pip install 'batchalign[avqi]'
```

AVQI takes two recordings: a sustained vowel and continuous speech. Pass the
vowel first:

```bash
batchalign avqi participant.sv.wav participant.cs.wav -o measurements/
```

For a collection, use two directories with mirrored relative paths:

```text
vowels/participant1/session.sv.wav
speech/participant1/session.cs.wav
vowels/participant2/session.wav
speech/participant2/session.flac
```

```bash
batchalign --parallel 4 avqi vowels/ speech/ -o measurements/
```

The command searches both directory trees concurrently. Pairing uses the
relative path without its audio extension and removes a terminal `.sv` or
`.cs` marker for the corresponding input. Directory structure is preserved
in the pair identifier, so equal filenames in different participant folders
remain separate. Multiple files mapping to the same key are an error; files are
never paired by directory listing order. Two explicit files are paired directly,
regardless of their names. Mixing a file and a directory is not supported.

## Output

The command writes `measurements/avqi.csv`, replacing it atomically after
processing. Without `-o`, it writes `avqi.csv` in the current directory.
Rows are sorted by pair identifier and include:

- `source_id`, `sv_file`, and `cs_file`: pair identity and input paths.
- `success` and `error`: processing status; failed measurements have empty numeric fields.
- `avqi`: the composite score.
- `cpps`, `hnr`, `shimmer_local`, `shimmer_local_db`, `slope`, and `tilt`: the six component measurements.
- `voiced_cs_duration` and `sv_duration`: seconds of retained speech and vowel used.
- `implementation`: extraction revision, Parselmouth version, and embedded Praat version.

Missing partners and per-pair processing failures remain visible as failed rows.
Other valid pairs continue processing. Any failed pair gives a nonzero CLI exit
status. No temporary audio files are written beside the originals.

## Input and measurement procedure

Use recordings from the same speaker and assessment session. Inputs are decoded
through Batchalign's media layer and downmixed to mono. Both sample rates must
be at least 20 kHz because the LTAS measurements use frequencies through 10 kHz.
When the rates differ, Praat resamples to the higher rate. This does not restore
bandwidth missing from the original recordings.

The sustained vowel must be at least three seconds long; its final three
seconds are used. Remove unwanted trailing silence from the input beforehand.
Silent, empty, non-finite, or unmeasurable recordings fail rather than receiving
a fabricated score.

The backend follows the supplied energy-window extraction procedure:

1. Apply a 0–34 Hz stop Hann filter to both recordings.
2. Remove speech intervals classified as silence using Praat's silence detector.
3. Retain complete 30 ms speech windows whose power exceeds 30% of the
   concatenated sounding signal's power and which contain a zero crossing.
4. Concatenate the retained speech with the final three seconds of vowel.
5. Measure CPPS, HNR, local shimmer (percent), local shimmer (dB), LTAS slope,
   and the slope of Praat's computed LTAS trend line.

The combination uses the AVQI 03.01 coefficients:

```text
(4.152 - 0.177*CPPS - 0.006*HNR - 0.037*shimmer_percent
 + 0.941*shimmer_dB + 0.010*slope + 0.093*tilt) * 2.8902
```

These coefficients are described in the
[AVQI validation literature](https://iris.unito.it/retrieve/5d9a9012-3e2b-4dd0-9475-c00bc3ec2b49/Validation%20of%20the%20AVQI.pdf).
The energy-window selector here is a versioned Batchalign implementation, not
a validated reproduction of the original AVQI script's full speech-selection
protocol. It does not enforce a language-specific speech task or balance voiced
speech to exactly three seconds. Real-audio smoke tests establish execution,
not clinical calibration or equivalence. Scores are not clamped or converted to
diagnostic labels.

Praat operations are serialized to protect its shared object state. Pipeline
workers can prepare independent pairs concurrently. Cache keys include both
decoded recordings and the backend implementation/version identity.

## Python pipeline

```python
import batchalign as ba

pipeline = ba.recipes.avqi(avqi_backend=ba.AvqiBackend(), workers=4)
inputs = [
    ba.AvqiMediaInput(
        sustained_vowel="participant.sv.wav",
        continuous_speech="participant.cs.wav",
        source_id="participant",
    )
]
for outcome in pipeline.run(inputs):
    if outcome.is_failed:
        print(outcome.source_id, outcome.error)
    else:
        print(outcome.metrics["rows"][0]["columns"])
```

`Outcome.metrics` exposes the structured metrics table without consuming the
outcome. The Rust runner prepares the audio pair; `AvqiBackend` implements the
`AVQI` backend marker and receives typed `AvqiInput` values.

## Test a clean wheel installation

From the repository, build the native wheel, then pass its path to the
installation smoke test:

```bash
just batchalign wheel
just batchalign avqi-install-test python/target/wheels/batchalign-<version>-<platform-tags>.whl
```

The test creates a disposable virtual environment, installs the wheel with its
`avqi` extra, runs `pip check`, verifies native and generated-type imports, and
processes two mirrored pairs of synthetic audio using the installed console
script outside the checkout. It requires network access for dependencies.
An optional final argument selects the Python interpreter, such as `python3.12`.
