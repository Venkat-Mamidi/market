from core.orderbook import OrderBook, MarketSnapshot
from core.order import Trade, Order, Side, OrderType
from core.agents.base import BaseAgent
class SimulationEngine:
    def __init__(self, agents: list[BaseAgent], orderbook: OrderBook | None = None):
        if orderbook is not None: 
            self.orderbook = orderbook
        else:
            self.orderbook = OrderBook()
        
        self.agents = agents
        self.current_timestamp = 0
        self.trade_history = []
        self.snapshot_history = []
        self.agent_map = {}
        for agent in self.agents:
            self.agent_map[agent.agent_id] = agent
    
    def seed_book(self, mid_price: float = 100.0, levels: int = 5, qty_per_level: int = 10, spread: float = 2.0):
        half_spread = spread / 2
        best_bid = mid_price - half_spread
        best_ask = mid_price + half_spread

        for i in range(levels):
            bid_price = best_bid - i
            ask_price = best_ask + i
            uniq_bid_id = "seed_bid_" + str(i)
            uniq_ask_id = "seed_ask_" + str(i)
            agent_id = "seed"

            bid_order = Order(uniq_bid_id, Side.BUY, OrderType.LIMIT, qty_per_level, self.current_timestamp, bid_price, agent_id)
            ask_order = Order(uniq_ask_id, Side.SELL, OrderType.LIMIT, qty_per_level, self.current_timestamp, ask_price, agent_id)

            self.orderbook.submit_order(bid_order)
            self.orderbook.submit_order(ask_order)

    def step(self):
        snapshot = self.orderbook.get_market_snapshot()
        tick_trades = []

        for agent in self.agents:
            orders = agent.decide(snapshot, self.current_timestamp)

            for order in orders:
                trades = self.orderbook.submit_order(order)
                for trade in trades:
                    self._apply_trade_to_agents(trade)
                tick_trades.extend(trades)
                self.trade_history.extend(trades)

        ending_snapshot = self.orderbook.get_market_snapshot()
        self.snapshot_history.append(ending_snapshot)

        self.current_timestamp += 1

        return tick_trades
    
    def run(self, num_ticks: int):
        if num_ticks < 0:
            raise ValueError("Num ticks must be non-negative")
        for _ in range(num_ticks):
            self.step()
        return self.trade_history
    
    def _apply_trade_to_agents(self, trade: Trade):
        buy_order = self.orderbook.order_map[trade.buy_order_id]
        sell_order = self.orderbook.order_map[trade.sell_order_id]

        buyer_id = buy_order.agent_id
        seller_id = sell_order.agent_id


        if buyer_id in self.agent_map:
            buyer = self.agent_map[buyer_id]
            buyer.inventory += trade.qty
            buyer.cash -= trade.price * trade.qty
        
        if seller_id in self.agent_map:
            seller = self.agent_map[seller_id]
            seller.inventory -= trade.qty
            seller.cash += trade.price * trade.qty