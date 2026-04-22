import asyncio
from datetime import datetime
from pathlib import Path
import json
from typing import Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.agents.market_maker import MarketMaker
from core.agents.mean_reversion import MeanReversionTrader
from core.agents.momentum import MomentumTrader
from core.agents.noise import NoiseTrader
from core.replay import save_simulation, simulation_to_dict

app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent.parent
REPLAY_DIR = BASE_DIR / "replays"
live_task: asyncio.Task | None = None
last_live_payload: dict | None = None


class AgentConfig(BaseModel):
    agent_type: Literal["market_maker", "noise", "momentum", "mean_reversion"]
    agent_id: str
    position_limit: int = 50
    inventory: int = 0
    cash: float = 0.0
    base_spread: float = 1.0
    order_size: int = 10
    inventory_skew_factor: float = 0.01
    min_qty: int = 1
    max_qty: int = 10
    trade_probability: float = 0.2
    lookback_window: int = 2
    trade_size: int = 5
    threshold: float = 0.1


class LiveSimulationRequest(BaseModel):
    num_ticks: int = 100
    tick_delay_ms: int = 150
    seed_mid_price: float = 100.0
    seed_levels: int = 5
    seed_qty_per_level: int = 20
    seed_spread: float = 2.0
    agents: list[AgentConfig] | None = None


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        disconnected: list[WebSocket] = []
        for websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        for websocket in disconnected:
            self.disconnect(websocket)


manager = ConnectionManager()


def read_replay_file(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def make_live_replay_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return REPLAY_DIR / f"live_{timestamp}.json"


def build_default_agent_configs() -> list[AgentConfig]:
    return [
        AgentConfig(
            agent_type="market_maker",
            agent_id="mm1",
            position_limit=100,
            base_spread=1.0,
            order_size=10,
            inventory_skew_factor=0.01,
        ),
        AgentConfig(agent_type="noise", agent_id="noise1", position_limit=50),
        AgentConfig(agent_type="noise", agent_id="noise2", position_limit=50),
        AgentConfig(agent_type="noise", agent_id="noise3", position_limit=50),
        AgentConfig(
            agent_type="momentum",
            agent_id="mom1",
            position_limit=50,
            lookback_window=2,
            trade_size=5,
            threshold=0.1,
        ),
        AgentConfig(
            agent_type="mean_reversion",
            agent_id="mr1",
            position_limit=50,
            lookback_window=3,
            trade_size=5,
            threshold=0.2,
        ),
    ]


def build_agents_from_configs(configs: list[AgentConfig] | None):
    active_configs = configs if configs else build_default_agent_configs()
    agents = []

    for config in active_configs:
        if config.agent_type == "market_maker":
            agent = MarketMaker(
                config.agent_id,
                base_spread=config.base_spread,
                order_size=config.order_size,
                inventory_skew_factor=config.inventory_skew_factor,
                position_limit=config.position_limit,
            )
        elif config.agent_type == "noise":
            agent = NoiseTrader(config.agent_id, position_limit=config.position_limit)
            agent.min_qty = config.min_qty
            agent.max_qty = config.max_qty
            agent.trade_probability = config.trade_probability
        elif config.agent_type == "momentum":
            agent = MomentumTrader(
                config.agent_id,
                position_limit=config.position_limit,
                lookback_window=config.lookback_window,
                trade_size=config.trade_size,
                threshold=config.threshold,
            )
        else:
            agent = MeanReversionTrader(
                config.agent_id,
                position_limit=config.position_limit,
                lookback_window=config.lookback_window,
                trade_size=config.trade_size,
                threshold=config.threshold,
            )

        agent.inventory = config.inventory
        agent.cash = config.cash
        agents.append(agent)

    return agents


async def run_live_simulation(config: LiveSimulationRequest) -> None:
    from core.simulation import SimulationEngine

    global last_live_payload, live_task

    engine = SimulationEngine(build_agents_from_configs(config.agents))
    replay_path = make_live_replay_path()
    engine.seed_book(
        mid_price=config.seed_mid_price,
        levels=config.seed_levels,
        qty_per_level=config.seed_qty_per_level,
        spread=config.seed_spread,
    )

    simulation_config = {
        "mode": "live",
        "num_ticks": config.num_ticks,
        "agents": [agent.agent_id for agent in engine.agents],
        "replay_filename": replay_path.name,
    }

    initial_payload = {
        "type": "state",
        "data": simulation_to_dict(engine, simulation_config),
    }
    last_live_payload = initial_payload
    try:
        await manager.broadcast(
            {
                "type": "status",
                "message": "live_simulation_started",
            }
        )
        await manager.broadcast(initial_payload)

        for _ in range(config.num_ticks):
            engine.step()
            state_payload = {
                "type": "state",
                "data": simulation_to_dict(engine, simulation_config),
            }
            last_live_payload = state_payload
            await manager.broadcast(state_payload)
            await asyncio.sleep(config.tick_delay_ms / 1000)

        await manager.broadcast(
            {
                "type": "status",
                "message": "live_simulation_completed",
                "replay_filename": replay_path.name,
            }
        )
    except asyncio.CancelledError:
        cancelled_payload = {
            "type": "state",
            "data": simulation_to_dict(engine, simulation_config),
        }
        last_live_payload = cancelled_payload
        await manager.broadcast(cancelled_payload)
        await manager.broadcast(
            {
                "type": "status",
                "message": "live_simulation_stopped",
                "replay_filename": replay_path.name,
            }
        )
        raise
    finally:
        save_simulation(engine, replay_path, simulation_config)
        live_task = None


@app.get("/")
def root():
    return {"message": "API is running"}


@app.get("/live/default-agents")
def live_default_agents():
    return {
        "agents": [config.model_dump() for config in build_default_agent_configs()],
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/dashboard")
def dashboard():
    dashboard_path = BASE_DIR / "dashboard" / "index.html"
    if not dashboard_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return FileResponse(dashboard_path)

@app.get("/replays")
def list_replays():
    if not REPLAY_DIR.exists():
        return {"replays": []}
    
    files = sorted([p.name for p in REPLAY_DIR.glob("*.json")])
    return {"replays": files}

@app.get("/replays/latest")
def get_latest_replay():
    if not REPLAY_DIR.exists():
        raise HTTPException(status_code=404, detail="Replay directory not found")
    
    files = sorted(REPLAY_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not files:
        raise HTTPException(status_code=404, detail="No replay files found")
    
    latest_file = files[0]
    
    return {
        "filename": latest_file.name,
        "data": read_replay_file(latest_file),
    }

@app.get("/replays/{filename}")
def get_replay(filename: str):
    replay_dir = REPLAY_DIR.resolve()
    file_path = (REPLAY_DIR / filename).resolve()
    
    if (
        file_path.parent != replay_dir
        or file_path.suffix != ".json"
        or not file_path.exists()
    ):
        raise HTTPException(status_code=404, detail="Replay file not found")
    
    return {
        "filename": file_path.name,
        "data": read_replay_file(file_path),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await websocket.send_json(
        {
            "type": "status",
            "message": "connected",
        }
    )
    if last_live_payload is not None:
        await websocket.send_json(last_live_payload)

    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@app.post("/live/start")
async def start_live(request: LiveSimulationRequest):
    global live_task

    if request.num_ticks <= 0:
        raise HTTPException(status_code=400, detail="num_ticks must be positive")
    if request.tick_delay_ms < 0:
        raise HTTPException(status_code=400, detail="tick_delay_ms must be non-negative")

    if live_task is not None and not live_task.done():
        raise HTTPException(status_code=409, detail="Live simulation already running")

    live_task = asyncio.create_task(run_live_simulation(request))
    return {
        "status": "started",
        "num_ticks": request.num_ticks,
        "tick_delay_ms": request.tick_delay_ms,
    }


@app.post("/live/stop")
async def stop_live():
    global live_task

    if live_task is None or live_task.done():
        raise HTTPException(status_code=409, detail="No live simulation is running")

    live_task.cancel()
    try:
        await live_task
    except asyncio.CancelledError:
        pass

    return {
        "status": "stopped",
    }
