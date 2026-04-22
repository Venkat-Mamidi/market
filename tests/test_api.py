import json

from fastapi.testclient import TestClient

import api.main as api_main


def write_replay(path, current_timestamp):
    path.write_text(
        json.dumps(
            {
                "current_timestamp": current_timestamp,
                "trades": [],
                "snapshots": [],
                "agents": [],
            }
        ),
        encoding="utf-8",
    )


def test_health_endpoint_returns_ok():
    client = TestClient(api_main.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_replays_returns_json_files(tmp_path, monkeypatch):
    replay_dir = tmp_path / "replays"
    replay_dir.mkdir()
    write_replay(replay_dir / "a.json", 1)
    write_replay(replay_dir / "b.json", 2)
    (replay_dir / "ignore.txt").write_text("nope", encoding="utf-8")
    monkeypatch.setattr(api_main, "REPLAY_DIR", replay_dir)
    client = TestClient(api_main.app)

    response = client.get("/replays")

    assert response.status_code == 200
    assert response.json() == {"replays": ["a.json", "b.json"]}


def test_latest_replay_returns_most_recent_file(tmp_path, monkeypatch):
    replay_dir = tmp_path / "replays"
    replay_dir.mkdir()
    old_file = replay_dir / "old.json"
    new_file = replay_dir / "new.json"
    write_replay(old_file, 1)
    write_replay(new_file, 2)
    monkeypatch.setattr(api_main, "REPLAY_DIR", replay_dir)
    client = TestClient(api_main.app)

    response = client.get("/replays/latest")

    assert response.status_code == 200
    assert response.json()["filename"] == "new.json"
    assert response.json()["data"]["current_timestamp"] == 2


def test_get_replay_returns_named_file(tmp_path, monkeypatch):
    replay_dir = tmp_path / "replays"
    replay_dir.mkdir()
    write_replay(replay_dir / "demo.json", 5)
    monkeypatch.setattr(api_main, "REPLAY_DIR", replay_dir)
    client = TestClient(api_main.app)

    response = client.get("/replays/demo.json")

    assert response.status_code == 200
    assert response.json()["filename"] == "demo.json"
    assert response.json()["data"]["current_timestamp"] == 5


def test_get_replay_rejects_non_json_file(tmp_path, monkeypatch):
    replay_dir = tmp_path / "replays"
    replay_dir.mkdir()
    (replay_dir / "demo.txt").write_text("nope", encoding="utf-8")
    monkeypatch.setattr(api_main, "REPLAY_DIR", replay_dir)
    client = TestClient(api_main.app)

    response = client.get("/replays/demo.txt")

    assert response.status_code == 404
