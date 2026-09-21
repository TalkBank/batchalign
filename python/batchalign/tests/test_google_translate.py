"""Exercise real googletrans parsing/error handling with a controlled HTTP transport."""
from copy import deepcopy

import httpx
import pytest

from batchalign.backends.translate.google import GoogleTranslateBackend


def test_rate_limit_fallback_replaces_partial_google_output_and_records_provider(tmp_path, monkeypatch):
    from unittest.mock import AsyncMock
    from googletrans.constants import DUMMY_DATA
    from batchalign._core import Pipeline, Task, CacheSpec
    from batchalign._core.proto import TranslateOutput
    from batchalign.inputs import chat_from_path

    monkeypatch.setattr('batchalign.backends.translate.google.asyncio.sleep', AsyncMock())
    requests = []
    fallback_calls = []
    original = httpx.AsyncClient

    def respond(request):
        requests.append(request)
        if len(requests) == 1:
            data = deepcopy(DUMMY_DATA)
            data[0][0][0] = 'partial google result'
            data[2] = 'es'
            return httpx.Response(200, json=data)
        return httpx.Response(429)

    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(
        **kwargs, transport=httpx.MockTransport(respond)))

    class Local:
        name = 'nllb:test-provider:eng'
        def __init__(self, *, target, device):
            assert (target, device) == ('eng', 'cpu')
        def call(self, batch, **kwargs):
            fallback_calls.extend(batch)
            return [TranslateOutput(source_id=item.source_id, utterances=['hello .', 'goodbye .']) for item in batch]

    monkeypatch.setattr('batchalign.backends.translate.nllb.NllbTranslateBackend', Local)
    source = tmp_path / 'source.cha'
    source.write_text('@UTF8\n@Begin\n@Languages:\tspa\n@Participants:\tPAR Participant\n'
                      '@ID:\tspa|test|PAR|||||Participant|||\n*PAR:\thola .\n*PAR:\tadiós .\n@End\n')
    cache = CacheSpec(path=str(tmp_path / 'cache'))
    for attempt in range(2):
        backend = GoogleTranslateBackend(force_free=True, fallback_on_rate_limit=True)
        pipeline = Pipeline(tasks=[Task.Translate], backends=[backend], workers=1, cache=cache)
        outcome, = pipeline.run([chat_from_path(source, source_id=str(source))])
        assert not outcome.is_failed, outcome.error
        output = tmp_path / f'output-{attempt}.cha'
        outcome.write(str(output))
        text = output.read_text()
        assert '%xtra:\thello .' in text and '%xtra:\tgoodbye .' in text
        assert 'translate-provider: nllb:test-provider:eng' in text
        assert 'partial google result' not in text
    assert len(requests) == 4  # One success, then three rate-limit attempts.
    assert len(fallback_calls) == 1  # Cache preserves the actual provider too.
    assert fallback_calls[0].utterances == ['hola .', 'adiós .']


@pytest.mark.parametrize('status,language,enabled', [
    (403, 'spa', True), (503, 'spa', True), (429, 'ara', True),
    (429, None, True), (429, 'spa', False),
])
def test_fallback_does_not_hide_other_errors_or_guess_languages(monkeypatch, status, language, enabled):
    from unittest.mock import AsyncMock
    from batchalign._core.proto import TranslateInput

    monkeypatch.setattr('batchalign.backends.translate.google.asyncio.sleep', AsyncMock())
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(
        **kwargs, transport=httpx.MockTransport(lambda _: httpx.Response(status))))
    def unexpected(**kwargs):
        pytest.fail('must not construct the local model')
    monkeypatch.setattr('batchalign.backends.translate.nllb.NllbTranslateBackend', unexpected)
    backend = GoogleTranslateBackend(force_free=True, fallback_on_rate_limit=enabled)
    item = TranslateInput(source_id='test', utterances=['hola .'],
                          source={'kind': 'code', 'value': language} if language else {'kind': 'auto'},
                          target='eng')
    with pytest.raises(httpx.HTTPStatusError, match=str(status)):
        backend.call([item])


@pytest.mark.parametrize('status', [403, 429, 503])
def test_free_translation_http_errors_never_become_successful_echoes(monkeypatch, status):
    from unittest.mock import AsyncMock
    monkeypatch.setattr('batchalign.backends.translate.google.asyncio.sleep', AsyncMock())
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
    assert len(clients) == (1 if status == 403 else 3)
    assert all(client.is_closed for client in clients)


def test_rate_limit_retry_respects_provider_delay_and_then_translates(monkeypatch):
    from unittest.mock import AsyncMock
    from googletrans.constants import DUMMY_DATA
    sleep = AsyncMock()
    monkeypatch.setattr('batchalign.backends.translate.google.asyncio.sleep', sleep)
    original = httpx.AsyncClient
    requests = []
    clients = []

    def respond(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(429, headers={'Retry-After': '12'})
        data = deepcopy(DUMMY_DATA)
        data[0][0][0] = 'hello world'
        data[2] = 'es'
        return httpx.Response(200, json=data)

    def client(**kwargs):
        value = original(**kwargs, transport=httpx.MockTransport(respond))
        clients.append(value)
        return value

    monkeypatch.setattr(httpx, 'AsyncClient', client)
    backend = GoogleTranslateBackend(force_free=True)
    assert backend._translate_many(['hola mundo'], source='spa', target='eng') == ['hello world']
    sleep.assert_awaited_once_with(12.0)
    assert len(requests) == 2
    assert all(client.is_closed for client in clients)


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
