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


class EchoChat:
    async def stream_chat(self, messages):
        yield "The password is on the fridge [1]."


def test_ask_streams_server_sent_events(settings, embedder):
    app = create_app(settings, embedder=embedder, chat=EchoChat(), index_on_startup=False)
    with TestClient(app) as client:
        client.post("/index/rescan")
        wait_for_idle(client)

        response = client.post("/ask", json={"question": "Where is the wifi password?"})

    assert response.headers["content-type"].startswith("text/event-stream")
    events = [
        line.removeprefix("event: ")
        for line in response.text.splitlines()
        if line.startswith("event:")
    ]
    assert events == ["sources", "token", "done"]
    assert '"cited": [1]' in response.text


def test_ask_rejects_empty_questions(client):
    assert client.post("/ask", json={"question": ""}).status_code == 422
