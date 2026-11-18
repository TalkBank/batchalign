"""Credential persistence is exercised through the actual local HTTP routes."""
from fastapi.testclient import TestClient
from batchalign import api, config


def test_saved_key_reaches_future_workers_and_is_not_returned(monkeypatch, tmp_path):
    path = tmp_path / ".batchalign.ini"
    path.write_text("[other]\nkeep = yes\n", encoding="utf-8")
    monkeypatch.setattr(config, "CONFIG_PATH", path)
    monkeypatch.delenv("BATCHALIGN_REVAI_KEY", raising=False)
    monkeypatch.setenv("BATCHALIGN_API_ALLOW_PATHS", "1")
    client = TestClient(api.app)
    assert not client.get("/desktop/settings/revai").json()["configured"]
    response = client.put("/desktop/settings/revai", json={"key": "test-secret"})
    assert response.status_code == 200
    assert response.json() == {"configured": True, "from_environment": False}
    assert "test-secret" not in response.text
    # Workers independently load this same file, without parent process memory.
    assert config.get_api_key("revai", path=path) == "test-secret"
    assert config.get("other", "keep", path=path) == "yes"


def test_remote_mode_and_environment_override_cannot_modify_key(monkeypatch, tmp_path):
    path = tmp_path / ".batchalign.ini"
    monkeypatch.setattr(config, "CONFIG_PATH", path)
    monkeypatch.setenv("BATCHALIGN_API_ALLOW_PATHS", "0")
    client = TestClient(api.app)
    assert client.put("/desktop/settings/revai", json={"key": "test-secret"}).status_code == 403
    monkeypatch.setenv("BATCHALIGN_API_ALLOW_PATHS", "1")
    monkeypatch.setenv("BATCHALIGN_REVAI_KEY", "environment-secret")
    assert client.put("/desktop/settings/revai", json={"key": "test-secret"}).status_code == 409
    assert not path.exists()


def test_bad_config_is_preserved_and_error_does_not_leak_credentials(monkeypatch, tmp_path):
    path = tmp_path / ".batchalign.ini"
    original = "secret-in-malformed-config\n"
    path.write_text(original)
    monkeypatch.setattr(config, "CONFIG_PATH", path)
    monkeypatch.delenv("BATCHALIGN_REVAI_KEY", raising=False)
    monkeypatch.setenv("BATCHALIGN_API_ALLOW_PATHS", "1")
    response = TestClient(api.app).put("/desktop/settings/revai", json={"key": "new-secret"})
    assert response.status_code == 500
    assert "secret-in-malformed-config" not in response.text
    assert "new-secret" not in response.text
    assert path.read_text() == original
