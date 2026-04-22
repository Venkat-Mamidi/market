from core.agents.base import BaseAgent
from core.order import Order, Side, OrderType
from core.orderbook import MarketSnapshot
class MarketMaker(BaseAgent):
    def __init__(self, agent_id, base_spread, order_size, inventory_skew_factor, position_limit):
        super().__init__(agent_id, 0, 0.0,  position_limit)
        self.base_spread = base_spread
        self.order_size = order_size
        self.inventory_skew_factor = inventory_skew_factor
        self.order_counter = 0

    def decide(self, snapshot: MarketSnapshot, timestamp: int) -> list[Order]:
        if snapshot.mid_price is None:
            return []
        
        half_spread = self.base_spread / 2
        inventory_adjustment = self.inventory * self.inventory_skew_factor

        bid_price = snapshot.mid_price - half_spread - inventory_adjustment
        ask_price = snapshot.mid_price + half_spread - inventory_adjustment

        bid_id = self.agent_id + "_bid_" + str(self.order_counter)
        ask_id = self.agent_id + "_ask_" + str(self.order_counter)

        bid_order = Order(bid_id, Side.BUY, OrderType.LIMIT, self.order_size, timestamp, bid_price, self.agent_id)
        ask_order = Order(ask_id, Side.SELL, OrderType.LIMIT, self.order_size, timestamp, ask_price, self.agent_id)

        self.order_counter += 1

        return [bid_order, ask_order]