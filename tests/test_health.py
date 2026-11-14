from __future__ import annotations


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_redirects_to_workspace(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "http://127.0.0.1:8501"


def test_root_redirects_to_render_workspace_when_hosted(client, monkeypatch):
    monkeypatch.delenv("ACME_UI_URL", raising=False)
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://api.onrender.com")

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "https://acme-support-ui.onrender.com"
