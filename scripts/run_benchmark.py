import random
from time import perf_counter

from core.agents.market_maker import MarketMaker
from core.agents.mean_reversion import MeanReversionTrader
from core.agents.momentum import MomentumTrader
from core.agents.noise import NoiseTrader
from core.metrics import compute_metrics
from core.simulation import SimulationEngine


def build_agents():
    return [
        MarketMaker("mm1", base_spread=1.0, order_size=10, inventory_skew_factor=0.01, position_limit=100),
        MarketMaker("mm2", base_spread=1.2, order_size=8, inventory_skew_factor=0.01, position_limit=100),
        NoiseTrader("noise1", position_limit=75),
        NoiseTrader("noise2", position_limit=75),
        NoiseTrader("noise3", position_limit=75),
        NoiseTrader("noise4", position_limit=75),
        MomentumTrader("mom1", position_limit=75, lookback_window=2, trade_size=5, threshold=0.1),
        MeanReversionTrader("mr1", position_limit=75, lookback_window=3, trade_size=5, threshold=0.2),
    ]


def main():
    random.seed(42)
    num_ticks = 2_000
    agents = build_agents()
    engine = SimulationEngine(agents)
    engine.seed_book(mid_price=100.0, levels=10, qty_per_level=50, spread=2.0)

    start = perf_counter()
    engine.run(num_ticks)
    elapsed_seconds = perf_counter() - start

    metrics = compute_metrics(engine.trade_history, engine.snapshot_history)
    events_per_second = num_ticks / elapsed_seconds if elapsed_seconds > 0 else None

    print("Benchmark complete")
    print(f"Ticks: {num_ticks}")
    print(f"Elapsed seconds: {elapsed_seconds:.4f}")
    print(f"Ticks/second: {events_per_second:.2f}" if events_per_second is not None else "Ticks/second: n/a")
    print(f"Trades: {metrics.trade_count}")
    print(f"Volume: {metrics.total_volume}")
    print(f"Average spread: {metrics.average_spread}")
    print(f"Kyle lambda: {metrics.kyle_lambda}")
    print(f"First mid-price: {metrics.first_mid_price}")
    print(f"Last mid-price: {metrics.last_mid_price}")
    print(f"Price change: {metrics.price_change}")
    print(f"Min mid-price: {metrics.min_mid_price}")
    print(f"Max mid-price: {metrics.max_mid_price}")

    print("\nAgents:")
    for agent in agents:
        print(f"{agent.agent_id}: inventory={agent.inventory}, cash={agent.cash:.2f}")


if __name__ == "__main__":
    main()
