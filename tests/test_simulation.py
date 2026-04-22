from core.simulation import SimulationEngine
from core.agents.noise import NoiseTrader
from core.agents.market_maker import MarketMaker
import pytest


def test_seed_book_populates_top_of_book():
    engine = SimulationEngine(agents=[])

    engine.seed_book(mid_price=100.0, levels=3, qty_per_level=10, spread=2.0)

    assert engine.orderbook.get_best_bid() == 99.0
    assert engine.orderbook.get_best_ask() == 101.0
    assert engine.orderbook.get_spread() == 2.0
    assert engine.orderbook.get_mid_price() == 100.0


def test_seed_book_populates_expected_depth():
    engine = SimulationEngine(agents=[])

    engine.seed_book(mid_price=100.0, levels=3, qty_per_level=10, spread=2.0)

    assert engine.orderbook.get_bids_depth() == [(99.0, 10), (98.0, 10), (97.0, 10)]
    assert engine.orderbook.get_asks_depth() == [(101.0, 10), (102.0, 10), (103.0, 10)]


def test_seed_book_respects_qty_per_level():
    engine = SimulationEngine(agents=[])

    engine.seed_book(mid_price=50.0, levels=2, qty_per_level=25, spread=4.0)

    assert engine.orderbook.get_bids_depth() == [(48.0, 25), (47.0, 25)]
    assert engine.orderbook.get_asks_depth() == [(52.0, 25), (53.0, 25)]


def test_step_returns_no_trades_with_no_agents():
    engine = SimulationEngine(agents=[])
    engine.seed_book()

    trades = engine.step()

    assert trades == []
    assert engine.trade_history == []


def test_step_advances_timestamp_and_records_snapshot():
    engine = SimulationEngine(agents=[])
    engine.seed_book()

    engine.step()

    assert engine.current_timestamp == 1
    assert len(engine.snapshot_history) == 1
    assert engine.snapshot_history[0].best_bid == 99.0
    assert engine.snapshot_history[0].best_ask == 101.0


def test_step_records_trades_from_agent_orders():
    trader = NoiseTrader("noise1", position_limit=10)
    trader.trade_probability = 1.0
    trader.inventory = 10
    trader.min_qty = 1
    trader.max_qty = 1
    engine = SimulationEngine(agents=[trader])
    engine.seed_book(mid_price=100.0, levels=1, qty_per_level=5, spread=2.0)

    trades = engine.step()

    assert len(trades) == 1
    assert trades == engine.trade_history
    assert trades[0].buy_order_id == "seed_bid_0"
    assert trades[0].sell_order_id == "noise1_0"
    assert trades[0].price == 99.0
    assert trades[0].qty == 1


def test_run_zero_ticks_does_not_advance_time():
    engine = SimulationEngine(agents=[])

    trades = engine.run(0)

    assert trades == []
    assert engine.current_timestamp == 0
    assert engine.snapshot_history == []


def test_run_advances_timestamp_and_records_snapshots():
    engine = SimulationEngine(agents=[])
    engine.seed_book()

    trades = engine.run(3)

    assert trades == []
    assert engine.current_timestamp == 3
    assert len(engine.snapshot_history) == 3


def test_run_negative_ticks_raises_value_error():
    engine = SimulationEngine(agents=[])

    with pytest.raises(ValueError, match="Num ticks must be non-negative"):
        engine.run(-1)


def test_run_returns_accumulated_trade_history():
    trader = NoiseTrader("noise1", position_limit=10)
    trader.trade_probability = 1.0
    trader.inventory = 10
    trader.min_qty = 1
    trader.max_qty = 1
    engine = SimulationEngine(agents=[trader])
    engine.seed_book(mid_price=100.0, levels=1, qty_per_level=5, spread=2.0)

    trades = engine.run(3)

    assert trades is engine.trade_history
    assert len(trades) == 3
    assert engine.current_timestamp == 3


def test_step_updates_seller_inventory_and_cash():
    trader = NoiseTrader("noise1", position_limit=10)
    trader.trade_probability = 1.0
    trader.inventory = 10
    trader.cash = 0.0
    trader.min_qty = 1
    trader.max_qty = 1
    engine = SimulationEngine(agents=[trader])
    engine.seed_book(mid_price=100.0, levels=1, qty_per_level=5, spread=2.0)

    trades = engine.step()

    assert len(trades) == 1
    assert trader.inventory == 9
    assert trader.cash == 99.0


def test_step_updates_buyer_inventory_and_cash():
    trader = NoiseTrader("noise1", position_limit=10)
    trader.trade_probability = 1.0
    trader.inventory = -10
    trader.cash = 0.0
    trader.min_qty = 1
    trader.max_qty = 1
    engine = SimulationEngine(agents=[trader])
    engine.seed_book(mid_price=100.0, levels=1, qty_per_level=5, spread=2.0)

    trades = engine.step()

    assert len(trades) == 1
    assert trader.inventory == -9
    assert trader.cash == -101.0


def test_step_submits_market_maker_quotes_to_orderbook():
    maker = MarketMaker("mm1", base_spread=2.0, order_size=10, inventory_skew_factor=0.01, position_limit=100)
    engine = SimulationEngine(agents=[maker])
    engine.seed_book(mid_price=100.0, levels=1, qty_per_level=5, spread=4.0)

    trades = engine.step()

    assert trades == []
    assert maker.order_counter == 1
    assert engine.orderbook.get_bids_depth() == [(99.0, 10), (98.0, 5)]
    assert engine.orderbook.get_asks_depth() == [(101.0, 10), (102.0, 5)]
