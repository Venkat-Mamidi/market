from fastapi.testclient import TestClient

import api.main as api_main
import asyncio


def test_websocket_connects_and_sends_status():
    client = TestClient(api_main.app)

    with client.websocket_connect("/ws") as websocket:
        message = websocket.receive_json()

    assert message["type"] == "status"
    assert message["message"] == "connected"


def test_live_default_agents_returns_configs():
    client = TestClient(api_main.app)

    response = client.get("/live/default-agents")

    assert response.status_code == 200
    assert len(response.json()["agents"]) >= 1
    assert "agent_type" in response.json()["agents"][0]
    assert "agent_id" in response.json()["agents"][0]


def test_live_start_validates_num_ticks():
    client = TestClient(api_main.app)

    response = client.post(
        "/live/start",
        json={
            "num_ticks": 0,
            "tick_delay_ms": 10,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "num_ticks must be positive"


def test_live_stop_when_nothing_is_running():
    client = TestClient(api_main.app)

    response = client.post("/live/stop")

    assert response.status_code == 409
    assert response.json()["detail"] == "No live simulation is running"


def test_run_live_simulation_saves_replay(tmp_path, monkeypatch):
    monkeypatch.setattr(api_main, "REPLAY_DIR", tmp_path)

    async def no_broadcast(_message):
        return None

    monkeypatch.setattr(api_main.manager, "broadcast", no_broadcast)

    request = api_main.LiveSimulationRequest(num_ticks=1, tick_delay_ms=0)

    asyncio.run(api_main.run_live_simulation(request))

    saved_files = list(tmp_path.glob("live_*.json"))
    assert len(saved_files) == 1
