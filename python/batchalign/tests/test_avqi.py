"""AVQI pairing, typed pipeline/cache behavior, and real Praat measurements."""

from __future__ import annotations

import csv
import math
import wave
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
import typer
from typer.testing import CliRunner

import batchalign as ba
from batchalign.cli import app
from batchalign.cli.avqi import pair_audio
from batchalign.backends.avqi import AvqiBackend, avqi_score


def audio_file(path: Path, *, rate=22050, seconds=3.2, channels=1, silent=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    time = np.arange(round(seconds * rate)) / rate
    phase = 130 * time + 0.02 * np.sin(2 * np.pi * 5 * time)
    signal = sum(np.sin(2 * np.pi * k * phase) / k**1.5 for k in range(1, 12))
    signal = 0.2 * signal * (1 + 0.04 * np.sin(2 * np.pi * 3 * time))
    signal += np.random.default_rng(42).normal(0, 0.002, len(time))
    if silent:
        signal[:] = 0
    pcm = np.repeat((signal * 32767).astype("<i2")[:, None], channels, axis=1)
    with wave.open(str(path), "wb") as stream:
        stream.setparams((channels, 2, rate, 0, "NONE", "not compressed"))
        stream.writeframes(pcm.tobytes())
    return path


def test_pairing_preserves_tree_and_reports_both_missing_sides(tmp_path):
    sv, cs = tmp_path / "sv", tmp_path / "cs"
    for root, names in [(sv, ["one/a.sv.wav", "two/a.wav", "vowel-only.wav"]),
                        (cs, ["one/a.cs.mp3", "two/a.wav", "speech-only.wav"])]:
        for name in names:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
    pairs = pair_audio(sv, cs)
    assert [p.key for p in pairs] == ["one/a", "speech-only", "two/a", "vowel-only"]
    assert pairs[0].continuous_speech == (cs / "one/a.cs.mp3").resolve()
    assert pairs[1].sustained_vowel is None
    assert pairs[-1].continuous_speech is None
    assert pair_audio(sv / "two/a.wav", cs / "two/a.wav")[0].key == "a"


def test_ambiguous_pair_is_rejected(tmp_path):
    sv, cs = tmp_path / "sv", tmp_path / "cs"
    sv.mkdir()
    cs.mkdir()
    (sv / "a.sv.wav").touch()
    (sv / "a.flac").touch()
    with pytest.raises(typer.BadParameter, match="Ambiguous"):
        pair_audio(sv, cs)
    with pytest.raises(typer.BadParameter, match="two audio files or two"):
        pair_audio(sv / "a.sv.wav", cs)


def test_formula_rejects_undefined_features():
    with pytest.raises(ValueError, match="finite"):
        avqi_score(cpps=float("nan"), hnr=1, shimmer_local=1,
                   shimmer_local_db=1, slope=1, tilt=1)


class RecordingBackend(ba.AVQI):
    def __init__(self):
        self.calls = []
        self.identity = uuid4().hex

    @property
    def name(self):
        return f"avqi-test:{self.identity}"

    @property
    def batch_policy(self):
        return ba.BatchPolicy.one()

    def call(self, batch, **kwargs):
        from batchalign._core.proto import AvqiInput, AvqiOutput

        results = []
        for item in batch:
            assert isinstance(item, AvqiInput)
            self.calls.append(item)
            results.append(AvqiOutput(
                source_id=item.source_id, avqi=2.5, cpps=10, hnr=15,
                shimmer_local=2, shimmer_local_db=0.3, slope=-20, tilt=-10,
                voiced_cs_duration=2.7, sv_duration=3, implementation=self.name,
            ))
        return results


def test_typed_runner_decodes_both_inputs_and_cache_tracks_both(tmp_path):
    sv = audio_file(tmp_path / "a.sv.wav", channels=2)
    cs = audio_file(tmp_path / "a.cs.wav", seconds=1.5)
    backend = RecordingBackend()
    cache = ba.CacheSpec(path=str(tmp_path / "cache"))

    def run(sid):
        pipeline = ba.recipes.avqi(avqi_backend=backend, workers=2, cache=cache)
        [outcome] = list(pipeline.run([
            ba.AvqiMediaInput(sustained_vowel=sv, continuous_speech=cs, source_id=sid)
        ]))
        assert not outcome.is_failed, outcome.error
        row = outcome.metrics["rows"][0]["columns"]
        assert row["source_id"] == sid
        assert row["sv_file"] == str(sv)
        assert row["avqi"] == 2.5
        return outcome

    run("first")
    assert len(backend.calls) == 1
    assert backend.calls[0].sustained_vowel.channels == 1
    assert backend.calls[0].continuous_speech.frame_count == round(22050 * 1.5)
    run("same-audio-new-id")
    assert len(backend.calls) == 1
    audio_file(sv, seconds=3.4)
    run("changed-vowel")
    assert len(backend.calls) == 2
    audio_file(cs, seconds=1.6)
    run("changed-speech")
    assert len(backend.calls) == 3


def test_cli_writes_sorted_csv_with_missing_and_failed_rows(tmp_path, monkeypatch):
    sv, cs, out = tmp_path / "sv", tmp_path / "cs", tmp_path / "out"
    audio_file(sv / "nested/a.sv.wav")
    audio_file(cs / "nested/a.cs.wav")
    audio_file(sv / "missing.wav")
    audio_file(sv / "broken.wav")
    broken = cs / "broken.wav"
    broken.write_bytes(b"not audio")
    backend = RecordingBackend()
    monkeypatch.setattr(ba, "AvqiBackend", lambda: backend)
    result = CliRunner().invoke(app, [
        "--plain", "--parallel", "2", "avqi", str(sv), str(cs), "-o", str(out),
    ])
    assert result.exit_code != 0
    with (out / "avqi.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert [r["source_id"] for r in rows] == ["broken", "missing", "nested/a"]
    assert [r["success"] for r in rows] == ["False", "False", "True"]
    assert rows[0]["avqi"] == rows[1]["avqi"] == ""
    assert "audio_prep" in rows[0]["error"]
    assert "Missing" in rows[1]["error"]
    assert rows[2]["avqi"] == "2.5"
    assert not list(out.glob(".avqi-*"))


def test_real_praat_pipeline_and_stereo_input(tmp_path):
    sv = audio_file(tmp_path / "vowel.wav", channels=2)
    cs = audio_file(tmp_path / "speech.wav", seconds=2.2, rate=44100)
    pipeline = ba.recipes.avqi(avqi_backend=AvqiBackend(), cache=ba.CacheSpec.bypass())
    [outcome] = list(pipeline.run([
        ba.AvqiMediaInput(sustained_vowel=sv, continuous_speech=cs, source_id="real")
    ]))
    assert not outcome.is_failed, outcome.error
    row = outcome.metrics["rows"][0]["columns"]
    for key in ("avqi", "cpps", "hnr", "shimmer_local", "shimmer_local_db", "slope", "tilt"):
        assert math.isfinite(row[key]), (key, row)
    assert row["sv_duration"] == pytest.approx(3)
    assert 0 < row["voiced_cs_duration"] <= 2.2
    assert row["slope"] != pytest.approx(row["tilt"])
    assert "praat-" in row["implementation"]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["speech.wav", "vowel.wav"]


@pytest.mark.parametrize("kind", ["silent", "short", "low_rate"])
def test_real_praat_invalid_input_has_no_metrics(tmp_path, kind):
    sv = audio_file(tmp_path / "vowel.wav", seconds=1 if kind == "short" else 3.2)
    cs = audio_file(tmp_path / "speech.wav", silent=kind == "silent",
                    rate=16000 if kind == "low_rate" else 22050)
    pipeline = ba.recipes.avqi(avqi_backend=AvqiBackend(), cache=ba.CacheSpec.bypass())
    [outcome] = list(pipeline.run([
        ba.AvqiMediaInput(sustained_vowel=sv, continuous_speech=cs, source_id=kind)
    ]))
    assert outcome.is_failed
    assert outcome.metrics is None
    expected = {"silent": "silent", "short": "3 seconds", "low_rate": "20000"}
    assert expected[kind] in outcome.error


def test_avqi_help_does_not_construct_backend(monkeypatch):
    monkeypatch.setattr(ba, "AvqiBackend", lambda: pytest.fail("help must not load Praat"))
    result = CliRunner().invoke(app, ["avqi", "--help"])
    assert result.exit_code == 0
    assert "sustained_vowel" in result.output
