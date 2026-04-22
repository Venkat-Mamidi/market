from core.orderbook import MarketSnapshot
from core.order import Order
from abc import ABC, abstractmethod


class BaseAgent(ABC):
    def __init__(self, agent_id, inventory, cash, position_limit):
        self.agent_id = agent_id
        self.inventory = inventory
        self.cash = cash
        self.position_limit = position_limit

    @abstractmethod
    def decide(self, snapshot: MarketSnapshot, timestamp: int) -> list[Order]:
        """Return the orders this agent wants to submit at this tick."""
        raise NotImplementedError