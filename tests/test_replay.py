from core.agents.noise import NoiseTrader
from core.order import Side, Trade
from core.orderbook import MarketSnapshot
from core.replay import (
    agent_to_dict,
    load_simulation,
    save_simulation,
    simulation_to_dict,
    snapshot_to_dict,
    trade_to_dict,
)
from core.simulation import SimulationEngine


def test_trade_to_dict_serializes_trade():
    trade = Trade(
        buy_order_id="b1",
        sell_order_id="s1",
        price=100.0,
        qty=5,
        timestamp=3,
        aggressor_side=Side.BUY,
    )

    assert trade_to_dict(trade) == {
        "buy_order_id": "b1",
        "sell_order_id": "s1",
        "price": 100.0,
        "qty": 5,
        "timestamp": 3,
        "aggressor_side": "buy",
    }


def test_trade_to_dict_serializes_missing_aggressor_side():
    trade = Trade("b1", "s1", price=100.0, qty=5, timestamp=3)

    assert trade_to_dict(trade)["aggressor_side"] is None


def test_snapshot_to_dict_serializes_snapshot():
    snapshot = MarketSnapshot(
        best_bid=99.0,
        best_ask=101.0,
        spread=2.0,
        mid_price=100.0,
        bid_depth=[(99.0, 10)],
        ask_depth=[(101.0, 8)],
    )

    assert snapshot_to_dict(snapshot) == {
        "best_bid": 99.0,
        "best_ask": 101.0,
        "spread": 2.0,
        "mid_price": 100.0,
        "bid_depth": [(99.0, 10)],
        "ask_depth": [(101.0, 8)],
    }


def test_agent_to_dict_serializes_agent_state():
    agent = NoiseTrader("noise1", position_limit=50)
    agent.inventory = 7
    agent.cash = -700.0

    assert agent_to_dict(agent) == {
        "agent_id": "noise1",
        "agent_type": "NoiseTrader",
        "inventory": 7,
        "cash": -700.0,
        "position_limit": 50,
    }


def test_simulation_to_dict_serializes_engine_state():
    agent = NoiseTrader("noise1", position_limit=50)
    agent.trade_probability = 1.0
    agent.inventory = -50
    agent.min_qty = 1
    agent.max_qty = 1
    engine = SimulationEngine([agent])
    engine.seed_book(mid_price=100.0, levels=1, qty_per_level=5, spread=2.0)
    engine.run(1)

    data = simulation_to_dict(engine, config={"num_ticks": 1, "seed": 42})

    assert data["config"] == {"num_ticks": 1, "seed": 42}
    assert data["current_timestamp"] == 1
    assert len(data["trades"]) == 1
    assert len(data["snapshots"]) == 1
    assert data["agents"][0]["agent_id"] == "noise1"


def test_save_and_load_simulation_round_trips_json(tmp_path):
    agent = NoiseTrader("noise1", position_limit=50)
    engine = SimulationEngine([agent])
    engine.seed_book(mid_price=100.0, levels=1, qty_per_level=5, spread=2.0)
    engine.run(1)
    output_path = tmp_path / "replay.json"

    save_simulation(engine, output_path, config={"num_ticks": 1})
    loaded = load_simulation(output_path)

    assert loaded["config"] == {"num_ticks": 1}
    assert loaded["current_timestamp"] == 1
    assert loaded["agents"][0]["agent_type"] == "NoiseTrader"
