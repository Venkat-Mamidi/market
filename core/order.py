from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class Side(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    LIMIT = "limit"
    MARKET = "market"

@dataclass
class Order:
    order_id: str
    side: Side
    order_type: OrderType
    qty: int
    timestamp: int
    price: Optional[float] = None
    agent_id: Optional[str] = None
    remaining_qty: int = field(init=False)
    is_active: bool = field(init=False, default = True)

    def __post_init__(self) -> None:
        if self.qty <= 0:
            raise ValueError("qty must be positive")
        
        if self.order_type == OrderType.LIMIT:
            if self.price is None:
                raise ValueError("limit orders must have a price")
            if self.price <= 0:
                raise ValueError("price must be positive for limit orders")
        
        if self.order_type == OrderType.MARKET:
            if self.price is not None:
                raise ValueError("market orders must not have a price")
        
        if self.timestamp < 0:
            raise ValueError("timestamp must be non-negative")
        
        self.remaining_qty = self.qty
    
    def fill(self, fill_qty: int) -> None:
        if fill_qty <= 0:
            raise ValueError("fill_qty must be positive")
        if fill_qty > self.remaining_qty:
            raise ValueError("cannot overfill order")
        
        self.remaining_qty -= fill_qty

        if self.remaining_qty == 0:
            self.is_active = False
        
    def cancel(self) -> None:
        if self.remaining_qty > 0:
            self.is_active = False
    
    @property
    def is_filled(self) -> bool:
        return self.remaining_qty == 0
    
    @property
    def is_buy(self) -> bool:
        return self.side == Side.BUY

    @property 
    def is_sell(self) -> bool:
        return self.side == Side.SELL
    

@dataclass(frozen=True)
class Trade:
    buy_order_id: str
    sell_order_id: str
    price: float
    qty: int
    timestamp: int
    aggressor_side: Side | None = None

    def __post_init__(self) -> None:
        if self.price <= 0:
            raise ValueError("trade price must be positive")
        if self.qty <= 0:
            raise ValueError("trade qty must be positive")
        if self.timestamp < 0:
            raise ValueError("timestamp must be non-negative")
        if self.aggressor_side is not None and not isinstance(self.aggressor_side, Side):
            raise ValueError("aggressor_side must be a Side or None")
