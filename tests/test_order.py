import pytest

from core.order import Order, Trade, Side, OrderType


def test_limit_order_initializes_correctly():
    order = Order(
        order_id="o1",
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        qty=10,
        timestamp=1,
        price=100.0,
    )

    assert order.order_id == "o1"
    assert order.side == Side.BUY
    assert order.order_type == OrderType.LIMIT
    assert order.qty == 10
    assert order.timestamp == 1
    assert order.price == 100.0
    assert order.agent_id is None
    assert order.remaining_qty == 10
    assert order.is_active is True
    assert order.is_filled is False
    assert order.is_buy is True
    assert order.is_sell is False


def test_market_order_initializes_correctly():
    order = Order(
        order_id="o2",
        side=Side.SELL,
        order_type=OrderType.MARKET,
        qty=5,
        timestamp=2,
    )

    assert order.order_id == "o2"
    assert order.side == Side.SELL
    assert order.order_type == OrderType.MARKET
    assert order.qty == 5
    assert order.timestamp == 2
    assert order.price is None
    assert order.remaining_qty == 5
    assert order.is_active is True
    assert order.is_filled is False
    assert order.is_buy is False
    assert order.is_sell is True


def test_limit_order_without_price_raises_value_error():
    with pytest.raises(ValueError, match="limit orders must have a price"):
        Order(
            order_id="o3",
            side=Side.BUY,
            order_type=OrderType.LIMIT,
            qty=10,
            timestamp=3,
        )


def test_limit_order_with_zero_price_raises_value_error():
    with pytest.raises(ValueError, match="price must be positive for limit orders"):
        Order(
            order_id="o4",
            side=Side.BUY,
            order_type=OrderType.LIMIT,
            qty=10,
            timestamp=4,
            price=0.0,
        )


def test_limit_order_with_negative_price_raises_value_error():
    with pytest.raises(ValueError, match="price must be positive for limit orders"):
        Order(
            order_id="o5",
            side=Side.SELL,
            order_type=OrderType.LIMIT,
            qty=10,
            timestamp=5,
            price=-100.0,
        )


def test_market_order_with_price_raises_value_error():
    with pytest.raises(ValueError, match="market orders must not have a price"):
        Order(
            order_id="o6",
            side=Side.BUY,
            order_type=OrderType.MARKET,
            qty=10,
            timestamp=6,
            price=100.0,
        )


def test_order_with_zero_qty_raises_value_error():
    with pytest.raises(ValueError, match="qty must be positive"):
        Order(
            order_id="o7",
            side=Side.BUY,
            order_type=OrderType.LIMIT,
            qty=0,
            timestamp=7,
            price=100.0,
        )


def test_order_with_negative_qty_raises_value_error():
    with pytest.raises(ValueError, match="qty must be positive"):
        Order(
            order_id="o8",
            side=Side.SELL,
            order_type=OrderType.LIMIT,
            qty=-3,
            timestamp=8,
            price=101.0,
        )


def test_fill_reduces_remaining_qty():
    order = Order(
        order_id="o9",
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        qty=10,
        timestamp=9,
        price=100.0,
    )

    order.fill(4)

    assert order.qty == 10
    assert order.remaining_qty == 6
    assert order.is_active is True
    assert order.is_filled is False


def test_full_fill_marks_order_inactive():
    order = Order(
        order_id="o10",
        side=Side.SELL,
        order_type=OrderType.LIMIT,
        qty=7,
        timestamp=10,
        price=101.0,
    )

    order.fill(7)

    assert order.remaining_qty == 0
    assert order.is_active is False
    assert order.is_filled is True


def test_fill_with_zero_qty_raises_value_error():
    order = Order(
        order_id="o11",
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        qty=10,
        timestamp=11,
        price=100.0,
    )

    with pytest.raises(ValueError, match="fill_qty must be positive"):
        order.fill(0)


def test_fill_with_negative_qty_raises_value_error():
    order = Order(
        order_id="o12",
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        qty=10,
        timestamp=12,
        price=100.0,
    )

    with pytest.raises(ValueError, match="fill_qty must be positive"):
        order.fill(-2)


def test_overfill_raises_value_error():
    order = Order(
        order_id="o13",
        side=Side.SELL,
        order_type=OrderType.LIMIT,
        qty=5,
        timestamp=13,
        price=101.0,
    )

    with pytest.raises(ValueError, match="cannot overfill order"):
        order.fill(6)


def test_cancel_marks_order_inactive():
    order = Order(
        order_id="o14",
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        qty=8,
        timestamp=14,
        price=99.0,
    )

    order.cancel()

    assert order.remaining_qty == 8
    assert order.is_active is False
    assert order.is_filled is False


def test_cancel_after_partial_fill_preserves_remaining_qty():
    order = Order(
        order_id="o15",
        side=Side.SELL,
        order_type=OrderType.LIMIT,
        qty=10,
        timestamp=15,
        price=102.0,
    )

    order.fill(3)
    order.cancel()

    assert order.remaining_qty == 7
    assert order.is_active is False
    assert order.is_filled is False


def test_cancel_on_filled_order_leaves_order_filled_and_inactive():
    order = Order(
        order_id="o16",
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        qty=4,
        timestamp=16,
        price=100.0,
    )

    order.fill(4)
    order.cancel()

    assert order.remaining_qty == 0
    assert order.is_active is False
    assert order.is_filled is True


def test_trade_initializes_correctly():
    trade = Trade(
        buy_order_id="buy1",
        sell_order_id="sell1",
        price=101.5,
        qty=6,
        timestamp=20,
    )

    assert trade.buy_order_id == "buy1"
    assert trade.sell_order_id == "sell1"
    assert trade.price == 101.5
    assert trade.qty == 6
    assert trade.timestamp == 20


def test_trade_with_zero_price_raises_value_error():
    with pytest.raises(ValueError, match="trade price must be positive"):
        Trade(
            buy_order_id="buy2",
            sell_order_id="sell2",
            price=0.0,
            qty=5,
            timestamp=21,
        )


def test_trade_with_negative_price_raises_value_error():
    with pytest.raises(ValueError, match="trade price must be positive"):
        Trade(
            buy_order_id="buy3",
            sell_order_id="sell3",
            price=-10.0,
            qty=5,
            timestamp=22,
        )


def test_trade_with_zero_qty_raises_value_error():
    with pytest.raises(ValueError, match="trade qty must be positive"):
        Trade(
            buy_order_id="buy4",
            sell_order_id="sell4",
            price=100.0,
            qty=0,
            timestamp=23,
        )


def test_trade_with_negative_qty_raises_value_error():
    with pytest.raises(ValueError, match="trade qty must be positive"):
        Trade(
            buy_order_id="buy5",
            sell_order_id="sell5",
            price=100.0,
            qty=-1,
            timestamp=24,
        )


def test_trade_is_immutable():
    trade = Trade(
        buy_order_id="buy6",
        sell_order_id="sell6",
        price=100.0,
        qty=2,
        timestamp=25,
    )

    with pytest.raises(Exception):
        trade.price = 105.0