import time

import pytest
from fastapi.testclient import TestClient

from indexmind.api import create_app
from indexmind.settings import Settings


@pytest.fixture
def settings(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "faq.md").write_text("# Wifi\nThe wifi password is on the fridge.")
    return Settings(docs_dir=docs, data_dir=tmp_path / "data")


@pytest.fixture
def client(settings, embedder):
    app = create_app(settings, embedder=embedder, chat=object(), index_on_startup=False)
    with TestClient(app) as client:
        yield client


def test_health_reports_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_rescan_indexes_the_documents_folder(client):
    assert client.post("/index/rescan").status_code == 202

    status = wait_for_idle(client)

    assert status["state"] == "idle"
    assert status["files"] == 1


def wait_for_idle(client, timeout=5.0):
    deadline = time.monotonic() + timeout
    while True:
        status = client.get("/index/status").json()
        if status["state"] != "indexing" or time.monotonic() > deadline:
            return status
        time.sleep(0.02)
