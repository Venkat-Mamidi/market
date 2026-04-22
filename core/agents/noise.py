from core.agents.base import BaseAgent
from core.orderbook import MarketSnapshot
from core.order import Order, Side, OrderType
import random
class NoiseTrader(BaseAgent):
    def __init__(self, agent_id, position_limit):
        super().__init__(agent_id, 0, 0.0, position_limit)
        self.min_qty = 1
        self.max_qty = 10
        self.trade_probability = 0.2
        self.order_counter = 0
    
    def decide(self, snapshot: MarketSnapshot, timestamp: int) -> list[Order]:
        random_num = random.random()
        if random_num <= self.trade_probability:
            allowed_sides = []
            if self.inventory < self.position_limit:
                allowed_sides.append(Side.BUY)
            if self.inventory > -self.position_limit:
                allowed_sides.append(Side.SELL)
            if len(allowed_sides) == 0:
                return []
            else:
                random_side = random.choice(allowed_sides)
                random_qty = random.randint(self.min_qty, self.max_qty)
                uniq_order_id = self.agent_id + "_" + str(self.order_counter)
                self.order_counter+=1
                market_order = Order(uniq_order_id, random_side, OrderType.MARKET,random_qty, timestamp, None, self.agent_id) 
                return [market_order]
        else:
            return []