from core.order import Order, Trade, OrderType, Side
from typing import List
import heapq
from collections import defaultdict
from dataclasses import dataclass

@dataclass
class MarketSnapshot:
    best_bid: float | None
    best_ask: float | None
    spread: float | None
    mid_price: float | None
    bid_depth: list[tuple[float, int]]
    ask_depth: list[tuple[float, int]]


class OrderBook:
    def __init__(self):
        self.bids = []
        self.asks = []
        self.order_map = {}
    # buy stock
    # max heap
    # 
    def get_best_bid(self):
        while self.bids and (self.bids[0][2] not in self.order_map or self.order_map[self.bids[0][2]].is_active == False or self.order_map[self.bids[0][2]].remaining_qty == 0):
            heapq.heappop(self.bids)
        if self.bids:
            return -self.bids[0][0]
        
    # sell stock
    # min heap
    # returns price
    def get_best_ask(self):
        while self.asks and (self.asks[0][2] not in self.order_map or self.order_map[self.asks[0][2]].is_active == False or self.order_map[self.asks[0][2]].remaining_qty == 0):
            heapq.heappop(self.asks)
        if self.asks:
            return self.asks[0][0]
        
        
    def submit_order(self, o: Order) -> List[Trade]:
        self.order_map[o.order_id] = o
        trades = []
        # Buy Order
        if o.side == Side.BUY:
            if o.order_type == OrderType.LIMIT:
                best_ask = self.get_best_ask()
                while o.remaining_qty > 0 and best_ask is not None and best_ask <= o.price:
                    traded_order_id = self.asks[0][2]
                    traded_order = self.order_map[traded_order_id]
                    minimum_quantity = min(o.remaining_qty, traded_order.remaining_qty)
                    traded_order.fill(minimum_quantity)
                    o.fill(minimum_quantity)
                    trade = Trade(o.order_id, traded_order.order_id, traded_order.price, minimum_quantity, o.timestamp, o.side)
                    trades.append(trade)
                    best_ask = self.get_best_ask()
                if o.remaining_qty > 0:
                    heapq.heappush(self.bids, (-o.price, o.timestamp, o.order_id))
            else:
                # market buy
                best_ask = self.get_best_ask()
                while o.remaining_qty > 0 and best_ask is not None:
                    traded_order_id = self.asks[0][2]
                    traded_order = self.order_map[traded_order_id]
                    minimum_quantity = min(o.remaining_qty, traded_order.remaining_qty)
                    traded_order.fill(minimum_quantity)
                    o.fill(minimum_quantity)
                    trade = Trade(o.order_id, traded_order.order_id, traded_order.price, minimum_quantity, o.timestamp, o.side)
                    trades.append(trade)
                    best_ask = self.get_best_ask()
        # Sell Order
        else:
            if o.order_type == OrderType.LIMIT:
                best_bid = self.get_best_bid()
                while o.remaining_qty > 0 and best_bid is not None and best_bid >= o.price:
                    traded_order_id = self.bids[0][2]
                    traded_order = self.order_map[traded_order_id]
                    minimum_quantity = min(o.remaining_qty, traded_order.remaining_qty)
                    traded_order.fill(minimum_quantity)
                    o.fill(minimum_quantity)
                    trade = Trade(traded_order.order_id, o.order_id, traded_order.price, minimum_quantity, o.timestamp, o.side)
                    trades.append(trade)
                    best_bid = self.get_best_bid()
                if o.remaining_qty > 0:
                    heapq.heappush(self.asks, (o.price, o.timestamp, o.order_id))
            else:
                #market sell
                best_bid = self.get_best_bid()
                while o.remaining_qty > 0 and best_bid is not None:
                    traded_order_id = self.bids[0][2]
                    traded_order = self.order_map[traded_order_id]
                    minimum_quantity = min(o.remaining_qty, traded_order.remaining_qty)
                    traded_order.fill(minimum_quantity)
                    o.fill(minimum_quantity)
                    trade = Trade(traded_order.order_id, o.order_id, traded_order.price, minimum_quantity, o.timestamp, o.side)
                    trades.append(trade)
                    best_bid = self.get_best_bid()
        return trades
    
    def cancel_order(self, order_id: str):
        if order_id not in self.order_map:
            return False
        
        order = self.order_map[order_id]
        if order.is_active == False:
            return False
        order.is_active = False
        return True
    
    def get_top_of_book(self):
        best_ask = self.get_best_ask()
        best_bid = self.get_best_bid()
        if best_ask is not None and best_bid is not None:
            return ((best_bid, best_ask))
    
    def get_spread(self):
        top_tuple = self.get_top_of_book()
        if top_tuple is not None:
            return self.get_top_of_book()[1] - self.get_top_of_book()[0]
    
    def get_mid_price(self):
        top_tuple = self.get_top_of_book()
        if top_tuple is not None:
            return (top_tuple[0] + top_tuple[1]) / 2
    
    def get_bids_depth(self, levels: int | None = None):
        bids_map = defaultdict(int)
        for bid_tuple in self.bids:
            order_id = bid_tuple[2]
            if order_id not in self.order_map:
                continue
            order = self.order_map[order_id]
            if order.is_active == False:
                continue
            if order.remaining_qty == 0:
                continue
            
            bids_map[order.price]+= order.remaining_qty
        bids_list = list(bids_map.items())
        bids_list.sort(reverse=True)
        return bids_list[:levels]
    
    def get_asks_depth(self, levels: int | None = None):
        asks_map = defaultdict(int)
        for ask_tuple in self.asks:
            order_id = ask_tuple[2]
            if order_id not in self.order_map:
                continue
            order = self.order_map[order_id]
            if order.is_active == False:
                continue
            if order.remaining_qty == 0:
                continue
            
            asks_map[order.price]+= order.remaining_qty
        asks_list = list(asks_map.items())
        asks_list.sort()
        return asks_list[:levels]
    
    def get_market_snapshot(self, levels: int = 5) -> MarketSnapshot:
        snapshot = MarketSnapshot(best_bid = self.get_best_bid(), best_ask = self.get_best_ask(), spread = self.get_spread(), mid_price = self.get_mid_price(), bid_depth = self.get_bids_depth(levels), ask_depth = self.get_asks_depth(levels))
        return snapshot
