from pathlib import Path
import sys
from core.replay import load_simulation

def find_latest_replay():
    replay_dir = Path("replays")
    files = list(replay_dir.glob("*.json"))
    if not files:
        return None
    return max(files, key = lambda p: p.stat().st_mtime)


def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        path = find_latest_replay()
    
    if path is None:
        print("No replay files found in replays/.")
        return

    if not path.exists():
        print(f"Replay file not found: {path}")
        return
    
    data = load_simulation(path)
    trades = data["trades"]
    snapshots = data["snapshots"]
    agents = data["agents"]

    config = data.get("config", {})
    print(f"Replay: {path}")
    print(f"Config: {config}")
    print(f"Trades: {len(trades)}")
    print(f"Snapshots: {len(snapshots)}")
    print(f"Agents: {len(agents)}")

    if snapshots:
        final = snapshots[-1]
        print("\nFinal Market:")
        print(f"Best bid: {final['best_bid']}")
        print(f"Best ask: {final['best_ask']}")
        print(f"Spread: {final['spread']}")
        print(f"Mid price: {final['mid_price']}")
        print(f"Bid depth: {final['bid_depth']}")
        print(f"Ask depth: {final['ask_depth']}")
    
    print("\nAgents:")
    for agent in agents:
        print(agent["agent_id"], agent["agent_type"], agent["inventory"], agent["cash"])

if __name__ == "__main__":
    main()
