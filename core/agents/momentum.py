from core.agents.base import BaseAgent
from core.order import Order, Side, OrderType
from core.orderbook import MarketSnapshot
class MomentumTrader(BaseAgent):
    def __init__(self, agent_id, position_limit, lookback_window, trade_size, threshold):
        super().__init__(agent_id, 0, 0.0, position_limit)

        if lookback_window <= 0:
            raise ValueError("Lookback window must be more than 0")
        if trade_size <= 0:
            raise ValueError("Trade size must be more than 0")
        if threshold <0:
            raise ValueError("threshold must be non-negative")
        
        self.lookback_window = lookback_window
        self.trade_size = trade_size
        self.threshold = threshold
        self.order_counter = 0
        self.price_history = []
    
    def decide(self, snapshot: MarketSnapshot, timestamp: int) -> list[Order]:
        if snapshot.mid_price is None:
            return []
        self.price_history.append(snapshot.mid_price)
        if len(self.price_history) <= self.lookback_window:
            return []
        current_price = self.price_history[-1]
        old_price = self.price_history[len(self.price_history) - 1 - self.lookback_window]
        change = current_price - old_price

        if change > self.threshold and self.inventory < self.position_limit:
            order_id = self.agent_id + "_mom_" + str(self.order_counter)
            market_buy = Order(order_id, Side.BUY, OrderType.MARKET, self.trade_size, timestamp, None, self.agent_id)
            self.order_counter += 1
            return [market_buy]
        elif change < -self.threshold and self.inventory > -self.position_limit:
            order_id = self.agent_id + "_mom_" + str(self.order_counter)
            market_sell = Order(order_id, Side.SELL, OrderType.MARKET, self.trade_size, timestamp, None, self.agent_id)
            self.order_counter += 1
            return [market_sell]
        else:
            return []
