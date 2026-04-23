import json
from dataclasses import asdict
from pathlib import Path

from core.agents.base import BaseAgent
from core.metrics import compute_metrics
from core.order import Trade
from core.orderbook import MarketSnapshot
from core.simulation import SimulationEngine


def trade_to_dict(trade: Trade) -> dict:
    return {
        "buy_order_id": trade.buy_order_id,
        "sell_order_id": trade.sell_order_id,
        "price": trade.price, 
        "qty": trade.qty,
        "timestamp": trade.timestamp,
        "aggressor_side": None if trade.aggressor_side is None else trade.aggressor_side.value
    }

def snapshot_to_dict(snapshot: MarketSnapshot) -> dict:
    return {
        "best_bid": snapshot.best_bid,
        "best_ask": snapshot.best_ask,
        "spread": snapshot.spread,
        "mid_price": snapshot.mid_price,
        "bid_depth": snapshot.bid_depth,
        "ask_depth": snapshot.ask_depth,
    }


def agent_to_dict(agent: BaseAgent) -> dict:
    return {
        "agent_id": agent.agent_id,
        "agent_type": agent.__class__.__name__,
        "inventory": agent.inventory,
        "cash": agent.cash,
        "position_limit": agent.position_limit,
    }


def simulation_to_dict(
    engine: SimulationEngine,
    config: dict | None = None,
) -> dict:
    metrics = compute_metrics(engine.trade_history, engine.snapshot_history)
    return {
        "config": config or {},
        "current_timestamp": engine.current_timestamp,
        "trades": [trade_to_dict(trade) for trade in engine.trade_history],
        "snapshots": [
            snapshot_to_dict(snapshot)
            for snapshot in engine.snapshot_history
        ],
        "agents": [agent_to_dict(agent) for agent in engine.agents],
        "metrics": asdict(metrics),
    }


def save_simulation(
    engine: SimulationEngine,
    path: str | Path,
    config: dict | None = None,
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = simulation_to_dict(engine, config)
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_simulation(path: str | Path) -> dict:
    input_path = Path(path)
    return json.loads(input_path.read_text(encoding="utf-8"))
