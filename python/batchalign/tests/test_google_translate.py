"""Exercise real googletrans parsing/error handling with a controlled HTTP transport."""
from copy import deepcopy

import httpx
import pytest

from batchalign.backends.translate.google import GoogleTranslateBackend


@pytest.mark.parametrize('status', [403, 429, 503])
def test_free_translation_http_errors_never_become_successful_echoes(monkeypatch, status):
    clients = []
    original = httpx.AsyncClient

    def client(**kwargs):
        value = original(**kwargs, transport=httpx.MockTransport(
            lambda request: httpx.Response(status, text='unavailable')))
        clients.append(value)
        return value

    monkeypatch.setattr(httpx, 'AsyncClient', client)
    backend = GoogleTranslateBackend(force_free=True)
    with pytest.raises(Exception, match=str(status)):
        backend._translate_many(['hola mundo'], source='spa', target='eng')
    assert len(clients) == 1
    assert clients[0].is_closed


def test_free_translation_parses_response_and_closes_each_client(monkeypatch):
    from googletrans.constants import DUMMY_DATA
    clients = []
    requests = []
    original = httpx.AsyncClient

    def respond(request):
        requests.append(request)
        data = deepcopy(DUMMY_DATA)
        data[0][0][0] = 'the child eats the red apple.'
        data[2] = 'es'
        return httpx.Response(200, json=data)

    def client(**kwargs):
        value = original(**kwargs, transport=httpx.MockTransport(respond))
        clients.append(value)
        return value

    monkeypatch.setattr(httpx, 'AsyncClient', client)
    backend = GoogleTranslateBackend(force_free=True)
    for _ in range(2):
        assert backend._translate_many(['el niño come la manzana roja.'], source='spa', target='eng') == [
            'the child eats the red apple .']
    assert all(client.is_closed for client in clients)
    assert len(clients) == 2
    assert all(request.url.params['sl'] == 'es' and request.url.params['tl'] == 'en' for request in requests)


def test_translation_target_changes_do_not_reuse_wrong_language_cache(tmp_path, monkeypatch):
    from batchalign._core import Pipeline, Task, CacheSpec
    from batchalign.inputs import chat_from_path

    source = tmp_path / 'source.cha'
    source.write_text('@UTF8\n@Begin\n@Languages:\tspa\n@Participants:\tPAR Participant\n'
                      '@ID:\tspa|test|PAR|||||Participant|||\n*PAR:\thola .\n@End\n')
    calls = []

    def translate(self, texts, *, source, target):
        calls.append(target)
        return [{'eng': 'hello .', 'fra': 'bonjour .'}[target] for _ in texts]

    monkeypatch.setattr(GoogleTranslateBackend, '_translate_many', translate)
    cache = CacheSpec(path=str(tmp_path / 'cache'))
    for index, target in enumerate(['eng', 'fra', 'eng']):
        backend = GoogleTranslateBackend(target=target, force_free=True)
        pipeline = Pipeline(tasks=[Task.Translate], backends=[backend], workers=1, cache=cache)
        outcome, = pipeline.run([chat_from_path(source, source_id=str(source))])
        assert not outcome.is_failed, outcome.error
        output = tmp_path / f'output-{index}.cha'
        outcome.write(str(output))
        assert f"%xtra:\t{'hello' if target == 'eng' else 'bonjour'} ." in output.read_text()
    assert calls == ['eng', 'fra']  # Third job uses the correct English cache.
