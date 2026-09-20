"""Desktop orchestration tests. Fakes test ordering/storage, not ML accuracy."""
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from batchalign import api
from batchalign.desktop import DesktopRequest, _sources


@pytest.fixture
def desktop(tmp_path, monkeypatch):
    monkeypatch.setenv("BATCHALIGN_API_ALLOW_PATHS", "1")
    source = tmp_path / "input" / "nested space" / "é.cha"
    source.parent.mkdir(parents=True)
    source.write_text("original", encoding="utf-8")
    request = {"folder": str(tmp_path / "input"), "source_ids": ["nested space/é.cha"],
               "output_path": str(tmp_path / "output"), "steps": [
                   {"recipe": "morphotag", "kwargs": {"stanza_backend": {"kind": "StanzaBackend"}}},
                   {"recipe": "translate", "kwargs": {"translate_backend": {"kind": "GoogleTranslateBackend"}}},
               ]}
    monkeypatch.setattr(api, "build_backend", lambda spec: object())
    with TestClient(api.app) as client:
        yield client, request, source


def run(client, request):
    response = client.post("/desktop/jobs", json=request)
    assert response.status_code == 200, response.text
    job_id = response.json()["job_id"]
    stream = client.get(f"/jobs/{job_id}/events")
    assert "event: done" in stream.text
    return client.get(f"/jobs/{job_id}").json(), stream.text, job_id


def recipe(name, seen, fail=False):
    class Pipeline:
        def run(self, inputs, callbacks, outcome_callback, retain_outcomes):
            # Match the compiled PyO3 contract (Vec<(String, callback)>).
            assert isinstance(callbacks, list)
            assert retain_outcomes is False
            for inp in inputs:
                seen.append((name, Path(inp.path).read_text(), str(inp.source_id)))
                def write(path, *, strip_word_timing):
                    Path(path).write_text(Path(inp.path).read_text() + f"/{name}")
                outcome_callback(SimpleNamespace(source_id=inp.source_id,
                    is_failed=fail, error="model failed" if fail else "", write=write))
    return lambda **kwargs: Pipeline()


@pytest.mark.parametrize("in_place", [False, True])
def test_all_selected_steps_execute_and_publish(desktop, monkeypatch, in_place):
    client, request, source = desktop
    request["in_place"] = in_place
    seen = []
    for name in ("morphotag", "translate"):
        monkeypatch.setitem(api.RECIPES, name, recipe(name, seen))
    state, events, job_id = run(client, request)
    assert state["state"] == "completed", state
    assert seen == [("morphotag", "original", str(source)),
                    ("translate", "original/morphotag", str(source))]
    target = source if in_place else Path(request["output_path"]) / request["source_ids"][0]
    assert target.read_text() == "original/morphotag/translate"
    if not in_place:
        assert source.read_text() == "original"
    assert events.count('"kind": "SourceCompleted"') == 1
    assert '"source_id": "nested space/\\u00e9.cha"' in events
    result = client.get(f"/jobs/{job_id}/result").json()
    assert result["outcomes"] == [{"source_id": request["source_ids"][0], "path": str(target)}]
    assert not api.JOBS[job_id].workdir.exists()


def test_failed_step_never_replaces_original_or_reports_success(desktop, monkeypatch):
    client, request, source = desktop
    request["in_place"] = True
    seen = []
    monkeypatch.setitem(api.RECIPES, "morphotag", recipe("morphotag", seen))
    monkeypatch.setitem(api.RECIPES, "translate", recipe("translate", seen, fail=True))
    state, events, _ = run(client, request)
    assert state["state"] == "failed"
    assert "model failed" in state["error"]
    assert "SourceCompleted" not in events
    assert source.read_text() == "original"


def test_model_construction_failure_is_a_failed_job(desktop, monkeypatch):
    client, request, source = desktop
    def fail(**kwargs):
        raise RuntimeError("model is unavailable")
    monkeypatch.setitem(api.RECIPES, "morphotag", fail)
    state, events, _ = run(client, request)
    assert state["state"] == "failed"
    assert "model is unavailable" in state["error"]
    assert "StageFailed" in events
    assert source.read_text() == "original"


def test_force_cpu_and_worker_count_reach_stanza_pipeline(desktop, monkeypatch):
    client, request, _ = desktop
    request.update(force_cpu=True, workers=1)
    request["steps"] = request["steps"][:1]
    constructed = []
    options = []
    monkeypatch.setattr(api, "build_backend", lambda spec: constructed.append(spec) or object())
    factory = recipe("morphotag", [])
    def make_pipeline(**kwargs):
        options.append(kwargs)
        return factory(**kwargs)
    monkeypatch.setitem(api.RECIPES, "morphotag", make_pipeline)
    state, _, _ = run(client, request)
    assert state["state"] == "completed", state
    assert constructed == [{"kind": "StanzaBackend", "kwargs": {"device": "cpu"}}]
    assert options[0]["workers"] == 1


def test_local_access_is_required(desktop, monkeypatch):
    client, request, _ = desktop
    monkeypatch.delenv("BATCHALIGN_API_ALLOW_PATHS")
    assert client.post("/desktop/jobs", json=request).status_code == 403


@pytest.mark.parametrize("source_id", ["../outside.cha", "/outside.cha", "nested space/missing.cha"])
def test_invalid_paths_are_rejected_before_job_creation(desktop, source_id):
    client, request, _ = desktop
    request["source_ids"] = [source_id]
    before = set(api.JOBS)
    assert client.post("/desktop/jobs", json=request).status_code == 400
    assert set(api.JOBS) == before


def test_transcribe_output_collisions_are_rejected(tmp_path):
    for name in ("same.wav", "same.mp3"):
        (tmp_path / name).touch()
    req = DesktopRequest(folder=str(tmp_path), source_ids=["same.wav", "same.mp3"],
                         in_place=True, steps=[{"recipe": "transcribe"}])
    with pytest.raises(ValueError, match="multiple inputs"):
        _sources(req)


def test_native_compare_writes_chat_and_metrics(tmp_path, monkeypatch):
    """Exercise the compiled pipeline and writer, with no mocked backend."""
    from batchalign.tests.fixture_paths import fixture_root
    monkeypatch.setenv("BATCHALIGN_API_ALLOW_PATHS", "1")
    fixture = fixture_root("parity") / "english_aphasia_short.cha"
    # The larger regression corpus intentionally contains an invalid reversed
    # bullet near its end. Use its opening, valid three-utterance excerpt.
    text = "\n".join(fixture.read_text(encoding="utf-8").splitlines()[:11]) + "\n@End\n"
    source = tmp_path / "input" / "clip.cha"
    source.parent.mkdir()
    source.write_text(text, encoding="utf-8")
    source.with_name("clip.gold.cha").write_text(text, encoding="utf-8")
    request = {"folder": str(source.parent), "source_ids": ["clip.cha"],
               "output_path": str(tmp_path / "output"),
               "steps": [{"recipe": "compare", "kwargs": {}, "use_cache": False}]}
    with TestClient(api.app) as client:
        state, events, job_id = run(client, request)
        assert state["state"] == "completed", (state, events)
        result = client.get(f"/jobs/{job_id}/result").json()["outcomes"]
    output = tmp_path / "output" / "clip.cha"
    assert output.is_file()
    assert "%xs" in output.read_text(encoding="utf-8")
    metrics = output.with_suffix(".compare.csv")
    assert metrics.is_file()
    import csv
    with metrics.open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["file"] == "clip.cha"
    assert float(rows[0]["wer"]) == 0
    assert float(rows[0]["accuracy"]) == 1
    assert {item["path"] for item in result} == {str(output), str(metrics)}
    assert "StageStarted" in events and "SourceCompleted" in events
    assert source.read_text(encoding="utf-8") == text


def test_native_progress_enums_match_the_gui_wire_contract():
    from batchalign._core import ProgressKind, Task, SourceId
    payload = api._event_to_dict(SimpleNamespace(source_id=SourceId('nested/clip.cha'),
        kind=ProgressKind.StageStarted, task=Task.Compare, completed=0, total=1, label='loading'))
    assert payload == {'source_id': 'nested/clip.cha', 'kind': 'StageStarted',
                       'task': 'Compare', 'completed': 0, 'total': 1, 'label': 'loading'}


def test_native_parse_failure_is_reported_without_overwriting_input(tmp_path, monkeypatch):
    monkeypatch.setenv('BATCHALIGN_API_ALLOW_PATHS', '1')
    source = tmp_path / 'broken.cha'
    source.write_text('this is not a CHAT transcript')
    source.with_name('broken.gold.cha').write_text('not CHAT either')
    request = {'folder': str(tmp_path), 'source_ids': ['broken.cha'], 'in_place': True,
               'steps': [{'recipe': 'compare', 'kwargs': {}, 'use_cache': False}]}
    with TestClient(api.app) as client:
        state, events, _ = run(client, request)
    assert state['state'] == 'failed'
    assert 'parse' in state['error'].lower()
    assert 'StageFailed' in events
    assert 'SourceCompleted' not in events
    assert source.read_text() == 'this is not a CHAT transcript'


def test_in_place_chat_suffix_is_preserved(desktop, monkeypatch):
    client, request, source = desktop
    renamed = source.with_suffix('.chat')
    source.rename(renamed)
    request['source_ids'] = ['nested space/é.chat']
    request['in_place'] = True
    for name in ('morphotag', 'translate'):
        monkeypatch.setitem(api.RECIPES, name, recipe(name, []))
    state, _, _ = run(client, request)
    assert state['state'] == 'completed', state
    assert renamed.read_text() == 'original/morphotag/translate'
    assert not source.exists()
