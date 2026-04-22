from core.metrics import SimulationMetrics, compute_kyle_lambda, compute_metrics
from core.order import Side, Trade
from core.orderbook import MarketSnapshot


def make_snapshot(spread: float | None, mid_price: float | None) -> MarketSnapshot:
    return MarketSnapshot(
        best_bid=None,
        best_ask=None,
        spread=spread,
        mid_price=mid_price,
        bid_depth=[],
        ask_depth=[],
    )


def test_compute_metrics_with_trades_and_snapshots():
    trades = [
        Trade("b1", "s1", price=100.0, qty=3, timestamp=1, aggressor_side=Side.BUY),
        Trade("b2", "s2", price=101.0, qty=4, timestamp=2, aggressor_side=Side.SELL),
    ]
    snapshots = [
        make_snapshot(spread=1.0, mid_price=100.0),
        make_snapshot(spread=2.0, mid_price=101.5),
        make_snapshot(spread=None, mid_price=None),
        make_snapshot(spread=3.0, mid_price=99.5),
    ]

    metrics = compute_metrics(trades, snapshots)

    assert metrics == SimulationMetrics(
        trade_count=2,
        total_volume=7,
        average_spread=2.0,
        kyle_lambda=None,
        first_mid_price=100.0,
        last_mid_price=99.5,
        price_change=-0.5,
        min_mid_price=99.5,
        max_mid_price=101.5,
    )


def test_compute_metrics_with_empty_inputs():
    metrics = compute_metrics([], [])

    assert metrics == SimulationMetrics(
        trade_count=0,
        total_volume=0,
        average_spread=None,
        kyle_lambda=None,
        first_mid_price=None,
        last_mid_price=None,
        price_change=None,
        min_mid_price=None,
        max_mid_price=None,
    )


def test_compute_metrics_ignores_missing_spreads_and_mid_prices():
    snapshots = [
        make_snapshot(spread=None, mid_price=None),
        make_snapshot(spread=1.5, mid_price=100.0),
        make_snapshot(spread=None, mid_price=101.0),
    ]

    metrics = compute_metrics([], snapshots)

    assert metrics.average_spread == 1.5
    assert metrics.first_mid_price == 100.0
    assert metrics.last_mid_price == 101.0
    assert metrics.price_change == 1.0


def test_compute_kyle_lambda_regresses_mid_change_on_signed_flow():
    trades = [
        Trade("b1", "s1", price=100.0, qty=10, timestamp=1, aggressor_side=Side.BUY),
        Trade("b2", "s2", price=100.0, qty=20, timestamp=2, aggressor_side=Side.BUY),
        Trade("b3", "s3", price=100.0, qty=10, timestamp=3, aggressor_side=Side.SELL),
    ]
    snapshots = [
        make_snapshot(spread=1.0, mid_price=100.0),
        make_snapshot(spread=1.0, mid_price=101.0),
        make_snapshot(spread=1.0, mid_price=103.0),
        make_snapshot(spread=1.0, mid_price=102.0),
    ]

    assert compute_kyle_lambda(trades, snapshots) == 0.1


def test_compute_metrics_includes_kyle_lambda():
    trades = [
        Trade("b1", "s1", price=100.0, qty=10, timestamp=1, aggressor_side=Side.BUY),
        Trade("b2", "s2", price=100.0, qty=20, timestamp=2, aggressor_side=Side.BUY),
        Trade("b3", "s3", price=100.0, qty=10, timestamp=3, aggressor_side=Side.SELL),
    ]
    snapshots = [
        make_snapshot(spread=1.0, mid_price=100.0),
        make_snapshot(spread=1.0, mid_price=101.0),
        make_snapshot(spread=1.0, mid_price=103.0),
        make_snapshot(spread=1.0, mid_price=102.0),
    ]

    metrics = compute_metrics(trades, snapshots)

    assert metrics.kyle_lambda == 0.1
