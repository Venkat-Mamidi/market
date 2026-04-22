from dataclasses import dataclass

from core.order import Side, Trade
from core.orderbook import MarketSnapshot


@dataclass(frozen=True)
class SimulationMetrics:
    trade_count: int
    total_volume: int
    average_spread: float | None
    kyle_lambda: float | None
    first_mid_price: float | None
    last_mid_price: float | None
    price_change: float | None
    min_mid_price: float | None
    max_mid_price: float | None


def compute_metrics(
    trades: list[Trade],
    snapshots: list[MarketSnapshot],
) -> SimulationMetrics:
    spreads = [snapshot.spread for snapshot in snapshots if snapshot.spread is not None]
    mid_prices = [snapshot.mid_price for snapshot in snapshots if snapshot.mid_price is not None]

    trade_count = len(trades)
    total_volume = sum(trade.qty for trade in trades)
    average_spread = sum(spreads) / len(spreads) if spreads else None
    kyle_lambda = compute_kyle_lambda(trades, snapshots)

    first_mid_price = mid_prices[0] if mid_prices else None
    last_mid_price = mid_prices[-1] if mid_prices else None
    price_change = (
        last_mid_price - first_mid_price
        if first_mid_price is not None and last_mid_price is not None
        else None
    )

    min_mid_price = min(mid_prices) if mid_prices else None
    max_mid_price = max(mid_prices) if mid_prices else None

    return SimulationMetrics(
        trade_count=trade_count,
        total_volume=total_volume,
        average_spread=average_spread,
        kyle_lambda=kyle_lambda,
        first_mid_price=first_mid_price,
        last_mid_price=last_mid_price,
        price_change=price_change,
        min_mid_price=min_mid_price,
        max_mid_price=max_mid_price,
    )


def compute_kyle_lambda(
    trades: list[Trade],
    snapshots: list[MarketSnapshot],
) -> float | None:
    mid_by_tick = {
        tick: snapshot.mid_price
        for tick, snapshot in enumerate(snapshots)
        if snapshot.mid_price is not None
    }
    signed_flow_by_tick: dict[int, int] = {}

    for trade in trades:
        if trade.aggressor_side is None:
            continue

        signed_qty = trade.qty if trade.aggressor_side == Side.BUY else -trade.qty
        signed_flow_by_tick[trade.timestamp] = (
            signed_flow_by_tick.get(trade.timestamp, 0) + signed_qty
        )

    observations: list[tuple[int, float]] = []
    for tick, signed_flow in signed_flow_by_tick.items():
        if signed_flow == 0 or tick <= 0:
            continue
        if tick not in mid_by_tick or tick - 1 not in mid_by_tick:
            continue

        mid_change = mid_by_tick[tick] - mid_by_tick[tick - 1]
        observations.append((signed_flow, mid_change))

    if len(observations) < 2:
        return None

    mean_flow = sum(flow for flow, _ in observations) / len(observations)
    mean_change = sum(change for _, change in observations) / len(observations)
    variance_flow = sum((flow - mean_flow) ** 2 for flow, _ in observations)

    if variance_flow == 0:
        return None

    covariance = sum(
        (flow - mean_flow) * (change - mean_change)
        for flow, change in observations
    )
    return covariance / variance_flow
