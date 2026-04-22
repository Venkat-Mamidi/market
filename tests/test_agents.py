from core.agents.noise import NoiseTrader
from core.agents.market_maker import MarketMaker
from core.agents.momentum import MomentumTrader
from core.agents.mean_reversion import MeanReversionTrader
from core.order import OrderType, Side
from core.orderbook import MarketSnapshot


def make_snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        best_bid=100,
        best_ask=101,
        spread=1,
        mid_price=100.5,
        bid_depth=[(100, 10)],
        ask_depth=[(101, 10)],
    )


def make_snapshot_with_mid(mid_price: float | None) -> MarketSnapshot:
    return MarketSnapshot(
        best_bid=None if mid_price is None else mid_price - 0.5,
        best_ask=None if mid_price is None else mid_price + 0.5,
        spread=None if mid_price is None else 1.0,
        mid_price=mid_price,
        bid_depth=[],
        ask_depth=[],
    )


def test_noise_trader_returns_no_orders_when_probability_is_zero():
    trader = NoiseTrader("noise1", position_limit=10)
    trader.trade_probability = 0.0

    orders = trader.decide(make_snapshot(), timestamp=1)

    assert orders == []


def test_noise_trader_returns_market_order_when_probability_is_one():
    trader = NoiseTrader("noise1", position_limit=10)
    trader.trade_probability = 1.0

    orders = trader.decide(make_snapshot(), timestamp=1)

    assert len(orders) == 1
    assert orders[0].order_id == "noise1_0"
    assert orders[0].side in (Side.BUY, Side.SELL)
    assert orders[0].order_type == OrderType.MARKET
    assert trader.min_qty <= orders[0].qty <= trader.max_qty
    assert orders[0].timestamp == 1
    assert orders[0].price is None
    assert orders[0].agent_id == "noise1"


def test_noise_trader_increments_order_counter_after_creating_order():
    trader = NoiseTrader("noise1", position_limit=10)
    trader.trade_probability = 1.0

    first_orders = trader.decide(make_snapshot(), timestamp=1)
    second_orders = trader.decide(make_snapshot(), timestamp=2)

    assert first_orders[0].order_id == "noise1_0"
    assert second_orders[0].order_id == "noise1_1"
    assert trader.order_counter == 2


def test_noise_trader_at_long_limit_only_sells():
    trader = NoiseTrader("noise1", position_limit=10)
    trader.trade_probability = 1.0
    trader.inventory = 10

    orders = trader.decide(make_snapshot(), timestamp=1)

    assert len(orders) == 1
    assert orders[0].side == Side.SELL


def test_noise_trader_at_short_limit_only_buys():
    trader = NoiseTrader("noise1", position_limit=10)
    trader.trade_probability = 1.0
    trader.inventory = -10

    orders = trader.decide(make_snapshot(), timestamp=1)

    assert len(orders) == 1
    assert orders[0].side == Side.BUY


def test_market_maker_returns_no_orders_when_mid_price_missing():
    maker = MarketMaker("mm1", base_spread=2.0, order_size=10, inventory_skew_factor=0.01, position_limit=100)
    snapshot = MarketSnapshot(
        best_bid=100,
        best_ask=None,
        spread=None,
        mid_price=None,
        bid_depth=[(100, 10)],
        ask_depth=[],
    )

    orders = maker.decide(snapshot, timestamp=1)

    assert orders == []


def test_market_maker_quotes_bid_and_ask_around_mid_price():
    maker = MarketMaker("mm1", base_spread=2.0, order_size=10, inventory_skew_factor=0.01, position_limit=100)

    orders = maker.decide(make_snapshot(), timestamp=1)

    assert len(orders) == 2
    assert orders[0].order_id == "mm1_bid_0"
    assert orders[0].side == Side.BUY
    assert orders[0].order_type == OrderType.LIMIT
    assert orders[0].qty == 10
    assert orders[0].timestamp == 1
    assert orders[0].price == 99.5
    assert orders[0].agent_id == "mm1"
    assert orders[1].order_id == "mm1_ask_0"
    assert orders[1].side == Side.SELL
    assert orders[1].order_type == OrderType.LIMIT
    assert orders[1].qty == 10
    assert orders[1].timestamp == 1
    assert orders[1].price == 101.5
    assert orders[1].agent_id == "mm1"


def test_market_maker_inventory_skew_moves_quotes_lower_when_long():
    maker = MarketMaker("mm1", base_spread=2.0, order_size=10, inventory_skew_factor=0.1, position_limit=100)
    maker.inventory = 5

    orders = maker.decide(make_snapshot(), timestamp=1)

    assert orders[0].price == 99.0
    assert orders[1].price == 101.0


def test_market_maker_inventory_skew_moves_quotes_higher_when_short():
    maker = MarketMaker("mm1", base_spread=2.0, order_size=10, inventory_skew_factor=0.1, position_limit=100)
    maker.inventory = -5

    orders = maker.decide(make_snapshot(), timestamp=1)

    assert orders[0].price == 100.0
    assert orders[1].price == 102.0


def test_market_maker_increments_order_counter_after_quote_pair():
    maker = MarketMaker("mm1", base_spread=2.0, order_size=10, inventory_skew_factor=0.01, position_limit=100)

    first_orders = maker.decide(make_snapshot(), timestamp=1)
    second_orders = maker.decide(make_snapshot(), timestamp=2)

    assert first_orders[0].order_id == "mm1_bid_0"
    assert first_orders[1].order_id == "mm1_ask_0"
    assert second_orders[0].order_id == "mm1_bid_1"
    assert second_orders[1].order_id == "mm1_ask_1"
    assert maker.order_counter == 2


def test_momentum_trader_returns_no_orders_when_mid_price_missing():
    trader = MomentumTrader("mom1", position_limit=10, lookback_window=2, trade_size=3, threshold=0.5)

    orders = trader.decide(make_snapshot_with_mid(None), timestamp=1)

    assert orders == []
    assert trader.price_history == []


def test_momentum_trader_returns_no_orders_until_enough_history():
    trader = MomentumTrader("mom1", position_limit=10, lookback_window=2, trade_size=3, threshold=0.5)

    first_orders = trader.decide(make_snapshot_with_mid(100), timestamp=1)
    second_orders = trader.decide(make_snapshot_with_mid(101), timestamp=2)

    assert first_orders == []
    assert second_orders == []
    assert trader.price_history == [100, 101]


def test_momentum_trader_buys_on_upward_momentum():
    trader = MomentumTrader("mom1", position_limit=10, lookback_window=2, trade_size=3, threshold=0.5)

    trader.decide(make_snapshot_with_mid(100), timestamp=1)
    trader.decide(make_snapshot_with_mid(100.4), timestamp=2)
    orders = trader.decide(make_snapshot_with_mid(101.0), timestamp=3)

    assert len(orders) == 1
    assert orders[0].order_id == "mom1_mom_0"
    assert orders[0].side == Side.BUY
    assert orders[0].order_type == OrderType.MARKET
    assert orders[0].qty == 3
    assert orders[0].timestamp == 3
    assert orders[0].price is None
    assert orders[0].agent_id == "mom1"


def test_momentum_trader_sells_on_downward_momentum():
    trader = MomentumTrader("mom1", position_limit=10, lookback_window=2, trade_size=3, threshold=0.5)

    trader.decide(make_snapshot_with_mid(101), timestamp=1)
    trader.decide(make_snapshot_with_mid(100.6), timestamp=2)
    orders = trader.decide(make_snapshot_with_mid(100.0), timestamp=3)

    assert len(orders) == 1
    assert orders[0].side == Side.SELL
    assert orders[0].order_type == OrderType.MARKET
    assert orders[0].qty == 3


def test_momentum_trader_returns_no_orders_when_change_under_threshold():
    trader = MomentumTrader("mom1", position_limit=10, lookback_window=2, trade_size=3, threshold=1.0)

    trader.decide(make_snapshot_with_mid(100), timestamp=1)
    trader.decide(make_snapshot_with_mid(100.2), timestamp=2)
    orders = trader.decide(make_snapshot_with_mid(100.5), timestamp=3)

    assert orders == []


def test_momentum_trader_position_limit_blocks_buy():
    trader = MomentumTrader("mom1", position_limit=10, lookback_window=2, trade_size=3, threshold=0.5)
    trader.inventory = 10

    trader.decide(make_snapshot_with_mid(100), timestamp=1)
    trader.decide(make_snapshot_with_mid(100.4), timestamp=2)
    orders = trader.decide(make_snapshot_with_mid(101.0), timestamp=3)

    assert orders == []


def test_momentum_trader_position_limit_blocks_sell():
    trader = MomentumTrader("mom1", position_limit=10, lookback_window=2, trade_size=3, threshold=0.5)
    trader.inventory = -10

    trader.decide(make_snapshot_with_mid(101), timestamp=1)
    trader.decide(make_snapshot_with_mid(100.6), timestamp=2)
    orders = trader.decide(make_snapshot_with_mid(100.0), timestamp=3)

    assert orders == []


def test_momentum_trader_increments_order_counter():
    trader = MomentumTrader("mom1", position_limit=10, lookback_window=1, trade_size=3, threshold=0.5)

    trader.decide(make_snapshot_with_mid(100), timestamp=1)
    first_orders = trader.decide(make_snapshot_with_mid(101), timestamp=2)
    second_orders = trader.decide(make_snapshot_with_mid(102), timestamp=3)

    assert first_orders[0].order_id == "mom1_mom_0"
    assert second_orders[0].order_id == "mom1_mom_1"
    assert trader.order_counter == 2


def test_mean_reversion_trader_returns_no_orders_when_mid_price_missing():
    trader = MeanReversionTrader("mr1", position_limit=10, lookback_window=2, trade_size=3, threshold=0.5)

    orders = trader.decide(make_snapshot_with_mid(None), timestamp=1)

    assert orders == []
    assert trader.price_history == []


def test_mean_reversion_trader_returns_no_orders_until_enough_history():
    trader = MeanReversionTrader("mr1", position_limit=10, lookback_window=2, trade_size=3, threshold=0.5)

    first_orders = trader.decide(make_snapshot_with_mid(100), timestamp=1)
    second_orders = trader.decide(make_snapshot_with_mid(101), timestamp=2)

    assert first_orders == []
    assert second_orders == []
    assert trader.price_history == [100, 101]


def test_mean_reversion_trader_sells_when_price_above_recent_average():
    trader = MeanReversionTrader("mr1", position_limit=10, lookback_window=2, trade_size=3, threshold=0.5)

    trader.decide(make_snapshot_with_mid(100), timestamp=1)
    trader.decide(make_snapshot_with_mid(100), timestamp=2)
    orders = trader.decide(make_snapshot_with_mid(101), timestamp=3)

    assert len(orders) == 1
    assert orders[0].order_id == "mr1_meanrev_0"
    assert orders[0].side == Side.SELL
    assert orders[0].order_type == OrderType.MARKET
    assert orders[0].qty == 3
    assert orders[0].timestamp == 3
    assert orders[0].price is None
    assert orders[0].agent_id == "mr1"


def test_mean_reversion_trader_buys_when_price_below_recent_average():
    trader = MeanReversionTrader("mr1", position_limit=10, lookback_window=2, trade_size=3, threshold=0.5)

    trader.decide(make_snapshot_with_mid(101), timestamp=1)
    trader.decide(make_snapshot_with_mid(101), timestamp=2)
    orders = trader.decide(make_snapshot_with_mid(100), timestamp=3)

    assert len(orders) == 1
    assert orders[0].side == Side.BUY
    assert orders[0].order_type == OrderType.MARKET
    assert orders[0].qty == 3


def test_mean_reversion_trader_returns_no_orders_when_deviation_under_threshold():
    trader = MeanReversionTrader("mr1", position_limit=10, lookback_window=2, trade_size=3, threshold=1.0)

    trader.decide(make_snapshot_with_mid(100), timestamp=1)
    trader.decide(make_snapshot_with_mid(100), timestamp=2)
    orders = trader.decide(make_snapshot_with_mid(100.5), timestamp=3)

    assert orders == []


def test_mean_reversion_trader_position_limit_blocks_sell():
    trader = MeanReversionTrader("mr1", position_limit=10, lookback_window=2, trade_size=3, threshold=0.5)
    trader.inventory = -10

    trader.decide(make_snapshot_with_mid(100), timestamp=1)
    trader.decide(make_snapshot_with_mid(100), timestamp=2)
    orders = trader.decide(make_snapshot_with_mid(101), timestamp=3)

    assert orders == []


def test_mean_reversion_trader_position_limit_blocks_buy():
    trader = MeanReversionTrader("mr1", position_limit=10, lookback_window=2, trade_size=3, threshold=0.5)
    trader.inventory = 10

    trader.decide(make_snapshot_with_mid(101), timestamp=1)
    trader.decide(make_snapshot_with_mid(101), timestamp=2)
    orders = trader.decide(make_snapshot_with_mid(100), timestamp=3)

    assert orders == []


def test_mean_reversion_trader_increments_order_counter():
    trader = MeanReversionTrader("mr1", position_limit=10, lookback_window=1, trade_size=3, threshold=0.5)

    trader.decide(make_snapshot_with_mid(100), timestamp=1)
    first_orders = trader.decide(make_snapshot_with_mid(101), timestamp=2)
    second_orders = trader.decide(make_snapshot_with_mid(99), timestamp=3)

    assert first_orders[0].order_id == "mr1_meanrev_0"
    assert second_orders[0].order_id == "mr1_meanrev_1"
    assert trader.order_counter == 2
