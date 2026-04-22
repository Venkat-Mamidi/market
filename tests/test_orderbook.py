from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.order import Order, Trade, OrderType, Side
from core.orderbook import OrderBook


def make_order(
    order_id: str,
    side: Side,
    order_type: OrderType,
    qty: int,
    timestamp: int,
    price: float | None = None,
    agent_id: str | None = None,
) -> Order:
    return Order(order_id, side, order_type, qty, timestamp, price, agent_id)


def test_limit_buy_rests_on_empty_book():
    book = OrderBook()
    buy = make_order("b1", Side.BUY, OrderType.LIMIT, 10, 1, 100)

    trades = book.submit_order(buy)

    assert trades == []
    assert book.get_best_bid() == 100
    assert book.get_best_ask() is None
    assert buy.remaining_qty == 10
    assert buy.is_active is True
    assert buy.is_filled is False


def test_limit_sell_rests_on_empty_book():
    book = OrderBook()
    sell = make_order("s1", Side.SELL, OrderType.LIMIT, 8, 1, 105)

    trades = book.submit_order(sell)

    assert trades == []
    assert book.get_best_ask() == 105
    assert book.get_best_bid() is None
    assert sell.remaining_qty == 8
    assert sell.is_active is True
    assert sell.is_filled is False


def test_crossing_limit_buy_matches_resting_ask():
    book = OrderBook()
    resting_ask = make_order("s1", Side.SELL, OrderType.LIMIT, 5, 1, 100)
    incoming_buy = make_order("b1", Side.BUY, OrderType.LIMIT, 5, 2, 101)

    book.submit_order(resting_ask)
    trades = book.submit_order(incoming_buy)

    assert len(trades) == 1
    assert trades[0].buy_order_id == "b1"
    assert trades[0].sell_order_id == "s1"
    assert trades[0].price == 100
    assert trades[0].qty == 5
    assert trades[0].timestamp == 2

    assert resting_ask.remaining_qty == 0
    assert incoming_buy.remaining_qty == 0
    assert resting_ask.is_active is False
    assert incoming_buy.is_active is False
    assert resting_ask.is_filled is True
    assert incoming_buy.is_filled is True

    assert book.get_best_ask() is None
    assert book.get_best_bid() is None


def test_crossing_limit_sell_matches_resting_bid():
    book = OrderBook()
    resting_bid = make_order("b1", Side.BUY, OrderType.LIMIT, 6, 1, 100)
    incoming_sell = make_order("s1", Side.SELL, OrderType.LIMIT, 6, 2, 99)

    book.submit_order(resting_bid)
    trades = book.submit_order(incoming_sell)

    assert len(trades) == 1
    assert trades[0].buy_order_id == "b1"
    assert trades[0].sell_order_id == "s1"
    assert trades[0].price == 100
    assert trades[0].qty == 6
    assert trades[0].timestamp == 2

    assert resting_bid.remaining_qty == 0
    assert incoming_sell.remaining_qty == 0
    assert resting_bid.is_active is False
    assert incoming_sell.is_active is False
    assert resting_bid.is_filled is True
    assert incoming_sell.is_filled is True

    assert book.get_best_bid() is None
    assert book.get_best_ask() is None


def test_partial_fill_buy_against_resting_ask():
    book = OrderBook()
    resting_ask = make_order("s1", Side.SELL, OrderType.LIMIT, 10, 1, 100)
    incoming_buy = make_order("b1", Side.BUY, OrderType.LIMIT, 4, 2, 101)

    book.submit_order(resting_ask)
    trades = book.submit_order(incoming_buy)

    assert len(trades) == 1
    assert trades[0].price == 100
    assert trades[0].qty == 4

    assert incoming_buy.remaining_qty == 0
    assert resting_ask.remaining_qty == 6

    assert incoming_buy.is_active is False
    assert incoming_buy.is_filled is True
    assert resting_ask.is_active is True
    assert resting_ask.is_filled is False

    assert book.get_best_ask() == 100
    assert book.get_best_bid() is None


def test_partial_fill_sell_against_resting_bid():
    book = OrderBook()
    resting_bid = make_order("b1", Side.BUY, OrderType.LIMIT, 9, 1, 100)
    incoming_sell = make_order("s1", Side.SELL, OrderType.LIMIT, 3, 2, 99)

    book.submit_order(resting_bid)
    trades = book.submit_order(incoming_sell)

    assert len(trades) == 1
    assert trades[0].price == 100
    assert trades[0].qty == 3

    assert incoming_sell.remaining_qty == 0
    assert resting_bid.remaining_qty == 6

    assert incoming_sell.is_active is False
    assert incoming_sell.is_filled is True
    assert resting_bid.is_active is True
    assert resting_bid.is_filled is False

    assert book.get_best_bid() == 100
    assert book.get_best_ask() is None


def test_limit_buy_remainder_rests_after_partial_fill():
    book = OrderBook()
    resting_ask = make_order("s1", Side.SELL, OrderType.LIMIT, 3, 1, 100)
    incoming_buy = make_order("b1", Side.BUY, OrderType.LIMIT, 7, 2, 101)

    book.submit_order(resting_ask)
    trades = book.submit_order(incoming_buy)

    assert len(trades) == 1
    assert trades[0].price == 100
    assert trades[0].qty == 3

    assert resting_ask.remaining_qty == 0
    assert incoming_buy.remaining_qty == 4

    assert resting_ask.is_active is False
    assert incoming_buy.is_active is True
    assert incoming_buy.is_filled is False

    assert book.get_best_bid() == 101
    assert book.get_best_ask() is None


def test_limit_sell_remainder_rests_after_partial_fill():
    book = OrderBook()
    resting_bid = make_order("b1", Side.BUY, OrderType.LIMIT, 2, 1, 100)
    incoming_sell = make_order("s1", Side.SELL, OrderType.LIMIT, 5, 2, 99)

    book.submit_order(resting_bid)
    trades = book.submit_order(incoming_sell)

    assert len(trades) == 1
    assert trades[0].price == 100
    assert trades[0].qty == 2

    assert resting_bid.remaining_qty == 0
    assert incoming_sell.remaining_qty == 3

    assert resting_bid.is_active is False
    assert incoming_sell.is_active is True
    assert incoming_sell.is_filled is False

    assert book.get_best_ask() == 99
    assert book.get_best_bid() is None


def test_market_buy_on_empty_book_returns_no_trades_and_does_not_rest():
    book = OrderBook()
    market_buy = make_order("b1", Side.BUY, OrderType.MARKET, 5, 1)

    trades = book.submit_order(market_buy)

    assert trades == []
    assert book.get_best_bid() is None
    assert book.get_best_ask() is None
    assert market_buy.remaining_qty == 5
    assert market_buy.is_active is True
    assert market_buy.is_filled is False


def test_market_sell_on_empty_book_returns_no_trades_and_does_not_rest():
    book = OrderBook()
    market_sell = make_order("s1", Side.SELL, OrderType.MARKET, 5, 1)

    trades = book.submit_order(market_sell)

    assert trades == []
    assert book.get_best_bid() is None
    assert book.get_best_ask() is None
    assert market_sell.remaining_qty == 5
    assert market_sell.is_active is True
    assert market_sell.is_filled is False


def test_market_buy_sweeps_multiple_ask_levels():
    book = OrderBook()
    ask1 = make_order("s1", Side.SELL, OrderType.LIMIT, 3, 1, 100)
    ask2 = make_order("s2", Side.SELL, OrderType.LIMIT, 4, 2, 101)
    market_buy = make_order("b1", Side.BUY, OrderType.MARKET, 6, 3)

    book.submit_order(ask1)
    book.submit_order(ask2)
    trades = book.submit_order(market_buy)

    assert len(trades) == 2

    assert trades[0].buy_order_id == "b1"
    assert trades[0].sell_order_id == "s1"
    assert trades[0].price == 100
    assert trades[0].qty == 3

    assert trades[1].buy_order_id == "b1"
    assert trades[1].sell_order_id == "s2"
    assert trades[1].price == 101
    assert trades[1].qty == 3

    assert ask1.remaining_qty == 0
    assert ask2.remaining_qty == 1
    assert market_buy.remaining_qty == 0

    assert ask1.is_filled is True
    assert ask2.is_filled is False
    assert market_buy.is_filled is True

    assert book.get_best_ask() == 101
    assert book.get_best_bid() is None


def test_market_sell_sweeps_multiple_bid_levels():
    book = OrderBook()
    bid1 = make_order("b1", Side.BUY, OrderType.LIMIT, 2, 1, 99)
    bid2 = make_order("b2", Side.BUY, OrderType.LIMIT, 5, 2, 98)
    market_sell = make_order("s1", Side.SELL, OrderType.MARKET, 6, 3)

    book.submit_order(bid1)
    book.submit_order(bid2)
    trades = book.submit_order(market_sell)

    assert len(trades) == 2

    assert trades[0].buy_order_id == "b1"
    assert trades[0].sell_order_id == "s1"
    assert trades[0].price == 99
    assert trades[0].qty == 2

    assert trades[1].buy_order_id == "b2"
    assert trades[1].sell_order_id == "s1"
    assert trades[1].price == 98
    assert trades[1].qty == 4

    assert bid1.remaining_qty == 0
    assert bid2.remaining_qty == 1
    assert market_sell.remaining_qty == 0

    assert bid1.is_filled is True
    assert bid2.is_filled is False
    assert market_sell.is_filled is True

    assert book.get_best_bid() == 98
    assert book.get_best_ask() is None


def test_market_buy_with_insufficient_liquidity_partially_fills_and_leftover_disappears():
    book = OrderBook()
    ask1 = make_order("s1", Side.SELL, OrderType.LIMIT, 2, 1, 100)
    ask2 = make_order("s2", Side.SELL, OrderType.LIMIT, 3, 2, 101)
    market_buy = make_order("b1", Side.BUY, OrderType.MARKET, 10, 3)

    book.submit_order(ask1)
    book.submit_order(ask2)
    trades = book.submit_order(market_buy)

    assert len(trades) == 2
    assert trades[0].qty == 2
    assert trades[1].qty == 3

    assert ask1.remaining_qty == 0
    assert ask2.remaining_qty == 0
    assert market_buy.remaining_qty == 5

    assert book.get_best_ask() is None
    assert book.get_best_bid() is None


def test_market_sell_with_insufficient_liquidity_partially_fills_and_leftover_disappears():
    book = OrderBook()
    bid1 = make_order("b1", Side.BUY, OrderType.LIMIT, 4, 1, 100)
    bid2 = make_order("b2", Side.BUY, OrderType.LIMIT, 1, 2, 99)
    market_sell = make_order("s1", Side.SELL, OrderType.MARKET, 9, 3)

    book.submit_order(bid1)
    book.submit_order(bid2)
    trades = book.submit_order(market_sell)

    assert len(trades) == 2
    assert trades[0].qty == 4
    assert trades[1].qty == 1

    assert bid1.remaining_qty == 0
    assert bid2.remaining_qty == 0
    assert market_sell.remaining_qty == 4

    assert book.get_best_bid() is None
    assert book.get_best_ask() is None


def test_same_price_earlier_ask_timestamp_gets_filled_first():
    book = OrderBook()
    ask_early = make_order("s1", Side.SELL, OrderType.LIMIT, 3, 1, 100)
    ask_late = make_order("s2", Side.SELL, OrderType.LIMIT, 3, 2, 100)
    market_buy = make_order("b1", Side.BUY, OrderType.MARKET, 4, 3)

    book.submit_order(ask_early)
    book.submit_order(ask_late)
    trades = book.submit_order(market_buy)

    assert len(trades) == 2

    assert trades[0].sell_order_id == "s1"
    assert trades[0].qty == 3

    assert trades[1].sell_order_id == "s2"
    assert trades[1].qty == 1

    assert ask_early.remaining_qty == 0
    assert ask_late.remaining_qty == 2
    assert book.get_best_ask() == 100


def test_same_price_earlier_bid_timestamp_gets_filled_first():
    book = OrderBook()
    bid_early = make_order("b1", Side.BUY, OrderType.LIMIT, 2, 1, 100)
    bid_late = make_order("b2", Side.BUY, OrderType.LIMIT, 4, 2, 100)
    market_sell = make_order("s1", Side.SELL, OrderType.MARKET, 5, 3)

    book.submit_order(bid_early)
    book.submit_order(bid_late)
    trades = book.submit_order(market_sell)

    assert len(trades) == 2

    assert trades[0].buy_order_id == "b1"
    assert trades[0].qty == 2

    assert trades[1].buy_order_id == "b2"
    assert trades[1].qty == 3

    assert bid_early.remaining_qty == 0
    assert bid_late.remaining_qty == 1
    assert book.get_best_bid() == 100


def test_get_top_of_book_returns_best_bid_and_ask_when_both_sides_exist():
    book = OrderBook()
    bid = make_order("b1", Side.BUY, OrderType.LIMIT, 5, 1, 99)
    ask = make_order("s1", Side.SELL, OrderType.LIMIT, 5, 2, 101)

    book.submit_order(bid)
    book.submit_order(ask)

    assert book.get_top_of_book() == (99, 101)


def test_get_top_of_book_returns_none_when_one_side_is_missing():
    book = OrderBook()
    bid = make_order("b1", Side.BUY, OrderType.LIMIT, 5, 1, 99)

    book.submit_order(bid)

    assert book.get_top_of_book() is None


def test_get_spread_returns_difference_when_both_sides_exist():
    book = OrderBook()
    bid = make_order("b1", Side.BUY, OrderType.LIMIT, 5, 1, 99)
    ask = make_order("s1", Side.SELL, OrderType.LIMIT, 5, 2, 101)

    book.submit_order(bid)
    book.submit_order(ask)

    assert book.get_spread() == 2


def test_get_spread_returns_none_when_one_side_is_missing():
    book = OrderBook()
    ask = make_order("s1", Side.SELL, OrderType.LIMIT, 5, 1, 101)

    book.submit_order(ask)

    assert book.get_spread() is None


def test_get_mid_price_returns_average_when_both_sides_exist():
    book = OrderBook()
    bid = make_order("b1", Side.BUY, OrderType.LIMIT, 5, 1, 99)
    ask = make_order("s1", Side.SELL, OrderType.LIMIT, 5, 2, 101)

    book.submit_order(bid)
    book.submit_order(ask)

    assert book.get_mid_price() == 100


def test_get_mid_price_returns_none_when_one_side_is_missing():
    book = OrderBook()
    bid = make_order("b1", Side.BUY, OrderType.LIMIT, 5, 1, 99)

    book.submit_order(bid)

    assert book.get_mid_price() is None


def test_get_bids_depth_aggregates_orders_at_same_price():
    book = OrderBook()
    bid1 = make_order("b1", Side.BUY, OrderType.LIMIT, 5, 1, 100)
    bid2 = make_order("b2", Side.BUY, OrderType.LIMIT, 2, 2, 100)
    bid3 = make_order("b3", Side.BUY, OrderType.LIMIT, 4, 3, 99)

    book.submit_order(bid1)
    book.submit_order(bid2)
    book.submit_order(bid3)

    assert book.get_bids_depth() == [(100, 7), (99, 4)]


def test_get_bids_depth_returns_highest_prices_first():
    book = OrderBook()
    bid1 = make_order("b1", Side.BUY, OrderType.LIMIT, 1, 1, 98)
    bid2 = make_order("b2", Side.BUY, OrderType.LIMIT, 1, 2, 100)
    bid3 = make_order("b3", Side.BUY, OrderType.LIMIT, 1, 3, 99)

    book.submit_order(bid1)
    book.submit_order(bid2)
    book.submit_order(bid3)

    assert book.get_bids_depth() == [(100, 1), (99, 1), (98, 1)]


def test_get_bids_depth_excludes_cancelled_orders():
    book = OrderBook()
    bid1 = make_order("b1", Side.BUY, OrderType.LIMIT, 5, 1, 100)
    bid2 = make_order("b2", Side.BUY, OrderType.LIMIT, 4, 2, 99)

    book.submit_order(bid1)
    book.submit_order(bid2)
    book.cancel_order("b1")

    assert book.get_bids_depth() == [(99, 4)]


def test_get_bids_depth_uses_remaining_qty_after_partial_fill():
    book = OrderBook()
    bid = make_order("b1", Side.BUY, OrderType.LIMIT, 10, 1, 100)
    sell = make_order("s1", Side.SELL, OrderType.LIMIT, 3, 2, 99)

    book.submit_order(bid)
    book.submit_order(sell)

    assert book.get_bids_depth() == [(100, 7)]


def test_get_bids_depth_respects_levels_limit():
    book = OrderBook()
    bid1 = make_order("b1", Side.BUY, OrderType.LIMIT, 5, 1, 100)
    bid2 = make_order("b2", Side.BUY, OrderType.LIMIT, 4, 2, 99)
    bid3 = make_order("b3", Side.BUY, OrderType.LIMIT, 3, 3, 98)

    book.submit_order(bid1)
    book.submit_order(bid2)
    book.submit_order(bid3)

    assert book.get_bids_depth(levels=2) == [(100, 5), (99, 4)]


def test_get_bids_depth_returns_empty_list_when_no_bids_exist():
    book = OrderBook()

    assert book.get_bids_depth() == []


def test_get_asks_depth_aggregates_orders_at_same_price():
    book = OrderBook()
    ask1 = make_order("s1", Side.SELL, OrderType.LIMIT, 5, 1, 101)
    ask2 = make_order("s2", Side.SELL, OrderType.LIMIT, 2, 2, 101)
    ask3 = make_order("s3", Side.SELL, OrderType.LIMIT, 4, 3, 102)

    book.submit_order(ask1)
    book.submit_order(ask2)
    book.submit_order(ask3)

    assert book.get_asks_depth() == [(101, 7), (102, 4)]


def test_get_asks_depth_returns_lowest_prices_first():
    book = OrderBook()
    ask1 = make_order("s1", Side.SELL, OrderType.LIMIT, 1, 1, 103)
    ask2 = make_order("s2", Side.SELL, OrderType.LIMIT, 1, 2, 101)
    ask3 = make_order("s3", Side.SELL, OrderType.LIMIT, 1, 3, 102)

    book.submit_order(ask1)
    book.submit_order(ask2)
    book.submit_order(ask3)

    assert book.get_asks_depth() == [(101, 1), (102, 1), (103, 1)]


def test_get_asks_depth_excludes_cancelled_orders():
    book = OrderBook()
    ask1 = make_order("s1", Side.SELL, OrderType.LIMIT, 5, 1, 101)
    ask2 = make_order("s2", Side.SELL, OrderType.LIMIT, 4, 2, 102)

    book.submit_order(ask1)
    book.submit_order(ask2)
    book.cancel_order("s1")

    assert book.get_asks_depth() == [(102, 4)]


def test_get_asks_depth_uses_remaining_qty_after_partial_fill():
    book = OrderBook()
    ask = make_order("s1", Side.SELL, OrderType.LIMIT, 10, 1, 101)
    buy = make_order("b1", Side.BUY, OrderType.LIMIT, 3, 2, 102)

    book.submit_order(ask)
    book.submit_order(buy)

    assert book.get_asks_depth() == [(101, 7)]


def test_get_asks_depth_respects_levels_limit():
    book = OrderBook()
    ask1 = make_order("s1", Side.SELL, OrderType.LIMIT, 5, 1, 101)
    ask2 = make_order("s2", Side.SELL, OrderType.LIMIT, 4, 2, 102)
    ask3 = make_order("s3", Side.SELL, OrderType.LIMIT, 3, 3, 103)

    book.submit_order(ask1)
    book.submit_order(ask2)
    book.submit_order(ask3)

    assert book.get_asks_depth(levels=2) == [(101, 5), (102, 4)]


def test_get_asks_depth_returns_empty_list_when_no_asks_exist():
    book = OrderBook()

    assert book.get_asks_depth() == []


def test_get_market_snapshot_returns_expected_values_when_both_sides_exist():
    book = OrderBook()
    bid1 = make_order("b1", Side.BUY, OrderType.LIMIT, 5, 1, 100)
    bid2 = make_order("b2", Side.BUY, OrderType.LIMIT, 2, 2, 99)
    ask1 = make_order("s1", Side.SELL, OrderType.LIMIT, 4, 3, 101)
    ask2 = make_order("s2", Side.SELL, OrderType.LIMIT, 3, 4, 102)

    book.submit_order(bid1)
    book.submit_order(bid2)
    book.submit_order(ask1)
    book.submit_order(ask2)

    snapshot = book.get_market_snapshot(levels=2)

    assert snapshot.best_bid == 100
    assert snapshot.best_ask == 101
    assert snapshot.spread == 1
    assert snapshot.mid_price == 100.5
    assert snapshot.bid_depth == [(100, 5), (99, 2)]
    assert snapshot.ask_depth == [(101, 4), (102, 3)]


def test_get_market_snapshot_returns_none_fields_when_one_side_is_missing():
    book = OrderBook()
    bid1 = make_order("b1", Side.BUY, OrderType.LIMIT, 5, 1, 100)
    bid2 = make_order("b2", Side.BUY, OrderType.LIMIT, 2, 2, 99)

    book.submit_order(bid1)
    book.submit_order(bid2)

    snapshot = book.get_market_snapshot(levels=2)

    assert snapshot.best_bid == 100
    assert snapshot.best_ask is None
    assert snapshot.spread is None
    assert snapshot.mid_price is None
    assert snapshot.bid_depth == [(100, 5), (99, 2)]
    assert snapshot.ask_depth == []


def test_get_market_snapshot_respects_depth_levels_limit():
    book = OrderBook()
    bid1 = make_order("b1", Side.BUY, OrderType.LIMIT, 5, 1, 100)
    bid2 = make_order("b2", Side.BUY, OrderType.LIMIT, 4, 2, 99)
    bid3 = make_order("b3", Side.BUY, OrderType.LIMIT, 3, 3, 98)
    ask1 = make_order("s1", Side.SELL, OrderType.LIMIT, 5, 4, 101)
    ask2 = make_order("s2", Side.SELL, OrderType.LIMIT, 4, 5, 102)
    ask3 = make_order("s3", Side.SELL, OrderType.LIMIT, 3, 6, 103)

    book.submit_order(bid1)
    book.submit_order(bid2)
    book.submit_order(bid3)
    book.submit_order(ask1)
    book.submit_order(ask2)
    book.submit_order(ask3)

    snapshot = book.get_market_snapshot(levels=2)

    assert snapshot.bid_depth == [(100, 5), (99, 4)]
    assert snapshot.ask_depth == [(101, 5), (102, 4)]

def test_cancelled_best_bid_is_skipped_by_lazy_deletion():
    book = OrderBook()
    bid1 = make_order("b1", Side.BUY, OrderType.LIMIT, 5, 1, 101)
    bid2 = make_order("b2", Side.BUY, OrderType.LIMIT, 5, 2, 100)

    book.submit_order(bid1)
    book.submit_order(bid2)

    assert book.get_best_bid() == 101

    assert book.cancel_order("b1") is True
    assert bid1.is_active is False

    assert book.get_best_bid() == 100
