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
