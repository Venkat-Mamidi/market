# Market Microstructure Simulation Engine

A Python market microstructure simulator with a heap-based limit order book, price-time priority matching, agent-based trading, inventory/cash accounting, and Kyle's lambda price-impact measurement.

This project models the core mechanics behind modern electronic exchanges: orders enter a limit order book, match by price-time priority, generate trades, update agent state, and produce market-level metrics over time.

## Quick Start

Recommended environment:

- Python 3.11+
- Windows PowerShell or a Unix-like shell

Create a virtual environment and install dependencies:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Features

- Limit and market orders
- Price-time priority matching
- Partial fills across multiple price levels
- Resting limit orders
- Non-resting market orders
- Order cancellation with lazy heap deletion
- Bid/ask top-of-book inspection
- Aggregated bid/ask depth
- Market snapshots with spread and mid-price
- Four agent types:
  - Noise trader
  - Market maker
  - Momentum trader
  - Mean reversion trader
- Simulation engine with tick-based execution
- Agent inventory and cash accounting
- Trade and snapshot history
- Metrics module with:
  - trade count
  - total volume
  - average spread
  - first/last mid-price
  - price change
  - min/max mid-price
  - Kyle's lambda
- Demo runner
- Benchmark runner
- FastAPI replay API
- Browser dashboard with replay selector
- Agent PnL ranking and cumulative volume visualization
- Live WebSocket dashboard mode
- Unit test coverage for matching, agents, simulation, and metrics

## Architecture

```text
Agents
  -> decide from MarketSnapshot
  -> submit Orders

SimulationEngine
  -> gives snapshots to agents
  -> routes orders to OrderBook
  -> stores trades and snapshots
  -> updates agent inventory/cash

OrderBook
  -> matches orders
  -> maintains bids/asks heaps
  -> records active orders in order_map
  -> exposes market snapshots

Metrics
  -> computes spread/price/volume stats
  -> estimates Kyle's lambda
```

Core data flow:

```text
MarketSnapshot -> Agent decisions -> Orders -> OrderBook -> Trades -> Metrics
```

## Project Structure

```text
core/
  agents/
    base.py
    noise.py
    market_maker.py
    momentum.py
    mean_reversion.py
  metrics.py
  order.py
  orderbook.py
  simulation.py

scripts/
  inspect_replay.py
  run_demo.py
  run_benchmark.py

api/
  main.py

dashboard/
  index.html

tests/
  test_agents.py
  test_api.py
  test_metrics.py
  test_order.py
  test_orderbook.py
  test_replay.py
  test_simulation.py
```

## How The Matching Engine Works

The order book uses two heaps:

- Bids: max-heap behavior using `(-price, timestamp, order_id)`
- Asks: min-heap using `(price, timestamp, order_id)`

The `order_map` dictionary is the source of truth:

```text
order_id -> Order
```

It tracks remaining quantity, active status, and order metadata.

Orders match using price-time priority:

1. Better price executes first.
2. At the same price, earlier timestamp executes first.

Limit orders match as much as possible, then any leftover quantity rests on the book. Market orders match as much as possible, and any leftover quantity does not rest.

Canceled or filled orders are not removed from heaps immediately. Instead, the book uses lazy deletion: stale heap entries are skipped when top-of-book methods clean the heap.

## Agent Behavior

### Noise Trader

Submits random market orders with configurable trade probability and quantity range. This represents uninformed order flow and helps keep the market active.

### Market Maker

Quotes both sides of the book by placing:

- a limit bid below mid-price
- a limit ask above mid-price

Quotes are adjusted by inventory. If the market maker is long, quotes shift lower to encourage selling inventory. If short, quotes shift higher.

### Momentum Trader

Tracks recent mid-prices. If price has moved upward over a lookback window by more than a threshold, it buys. If price has moved downward, it sells.

### Mean Reversion Trader

Compares current mid-price to the recent average. If price is too high relative to the average, it sells. If price is too low, it buys.

## Metrics

The metrics module computes simulation-level statistics from trade and snapshot histories.

Kyle's lambda is estimated by regressing mid-price changes against signed order flow:

```text
signed flow = +qty for buy aggressor trades
signed flow = -qty for sell aggressor trades

lambda = slope of mid-price change vs signed flow
```

A larger lambda means trades have greater price impact, which suggests lower liquidity.

## Running The Project

Run commands from the project root:

```powershell
cd C:\Users\venka\market
```

Run all tests:

```powershell
python -m pytest -v
```

Run the demo simulation:

```powershell
python -m scripts.run_demo
```

The demo also saves a replay JSON file under `replays/`.

Run the benchmark:

```powershell
python -m scripts.run_benchmark
```

Run the FastAPI server:

```powershell
python -m uvicorn api.main:app --reload
```

For live WebSocket mode on Windows, run without `--reload`:

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Open the dashboard:

```text
http://127.0.0.1:8000/dashboard
```

Useful API endpoints:

```text
GET /health
GET /replays
GET /replays/latest
GET /replays/{filename}
POST /live/start
WS /ws
```

Inspect the latest saved replay:

```powershell
python -m scripts.inspect_replay
```

Inspect a specific replay file:

```powershell
python -m scripts.inspect_replay replays/demo_YYYYMMDD_HHMMSS.json
```

Replace `demo_YYYYMMDD_HHMMSS.json` with an actual file name from the `replays/` folder. You can list saved replays with:

```powershell
Get-ChildItem replays
```

## Example Demo Output

Example output will vary because some agents use randomness.

```text
Simulation complete
Ticks: 500
Trades: 452
Volume: 1798

Final market:
Best bid: 100.83037323307536
Best ask: 101.20692886531974
Spread: 0.3765556322443757
Mid-price: 101.01865104919756

Metrics:
Average spread: 0.3929528731803849
Kyle lambda: 0.00047232419577633415
First mid-price: 100.0
Last mid-price: 101.01865104919756
Price change: 1.0186510491975582
```

## Example Benchmark Output

This is representative benchmark output from one run, not a guaranteed fixed result.

```text
Benchmark complete
Ticks: 2000
Elapsed seconds: 14.0840
Ticks/second: 142.01
Trades: 3677
Volume: 15158
Average spread: 0.13450747347121603
Kyle lambda: 0.00022367454201275815
```

## Testing

The test suite currently covers:

- Order validation
- Trade validation
- Limit order resting
- Market order execution
- Partial fills
- Multi-level sweeps
- Price-time priority
- Lazy deletion
- Cancellation
- Bid/ask depth
- Market snapshots
- Agent decision logic
- API replay endpoints
- WebSocket live endpoint
- Simulation stepping/running
- Inventory and cash updates
- Metrics and Kyle's lambda

At the time this README was written, the suite passes with:

```text
120 passed
```

## Technical Highlights

- Heap-based limit order book
- `order_map` as source of truth for active order state
- Lazy deletion for efficient cancellation handling
- Deterministic price-time priority matching
- Agent polymorphism through a shared `BaseAgent.decide(...)` interface
- Tick-based simulation orchestration
- Aggressor-side tracking for signed order flow
- Kyle's lambda computed without external libraries
- FastAPI + WebSocket delivery for replay and live market views

## GitHub Notes

- `tests/` is intentionally included because correctness is a core part of the project.
- Generated live replay files are ignored by git; you can keep one curated demo replay in `replays/` for showcasing the system.
- On Windows, use uvicorn without `--reload` for live WebSocket mode.git