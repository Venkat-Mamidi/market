from datetime import datetime

from core.agents.market_maker import MarketMaker
from core.agents.momentum import MomentumTrader
from core.agents.noise import NoiseTrader
from core.agents.mean_reversion import MeanReversionTrader
from core.metrics import compute_metrics
from core.replay import save_simulation
from core.simulation import SimulationEngine

def main():
    agents = [
        MarketMaker("mm1", base_spread=1.0, order_size=10, inventory_skew_factor=0.01, position_limit=100),
        NoiseTrader("noise1", position_limit=50),
        NoiseTrader("noise2", position_limit=50),
        NoiseTrader("noise3", position_limit=50),
        MomentumTrader("mom1", position_limit=50, lookback_window=2, trade_size=5, threshold=0.1),
        MeanReversionTrader("mr1", position_limit=50, lookback_window=3, trade_size=5, threshold=0.2)
    ]

    engine = SimulationEngine(agents)
    seed_config = {
        "mid_price": 100.0,
        "levels": 5,
        "qty_per_level": 20,
        "spread": 2.0,
    }
    engine.seed_book(
        seed_config["mid_price"],
        seed_config["levels"],
        seed_config["qty_per_level"],
        seed_config["spread"],
    )
    num_ticks = 500
    engine.run(num_ticks)

    final_snapshot = engine.snapshot_history[-1]
    metrics = compute_metrics(engine.trade_history, engine.snapshot_history)
    replay_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    replay_path = f"replays/demo_{replay_timestamp}.json"
    replay_config = {
        "num_ticks": num_ticks,
        "seed_book": seed_config,
        "agents": [agent.agent_id for agent in agents],
    }
    save_simulation(engine, replay_path, config=replay_config)

    print("Simulation complete")
    print(f"Ticks: {num_ticks}")
    print(f"Trades: {metrics.trade_count}")
    print(f"Volume: {metrics.total_volume}")
    print(f"Replay saved to: {replay_path}")

    print("\nFinal market:")
    print(f"Best bid: {final_snapshot.best_bid}")
    print(f"Best ask: {final_snapshot.best_ask}")
    print(f"Spread: {final_snapshot.spread}")
    print(f"Mid-price: {final_snapshot.mid_price}")
    print(f"Bid depth: {final_snapshot.bid_depth}")
    print(f"Ask depth: {final_snapshot.ask_depth}")

    print("\nMetrics:")
    print(f"Average spread: {metrics.average_spread}")
    print(f"Kyle lambda: {metrics.kyle_lambda}")
    print(f"First mid-price: {metrics.first_mid_price}")
    print(f"Last mid-price: {metrics.last_mid_price}")
    print(f"Price change: {metrics.price_change}")
    print(f"Min mid-price: {metrics.min_mid_price}")
    print(f"Max mid-price: {metrics.max_mid_price}")

    print("\nAgents:")
    for agent in agents:
        print(
            f"{agent.agent_id}: "
            f"inventory={agent.inventory}, "
            f"cash={agent.cash:.2f}"
        )


if __name__ == "__main__":
    main()
    
