"""
This module contains a function (order_combo_profit_taker) to order a multi-leg
combo position and attach a stop loss order.
"""
from ib_insync import *
from datetime import date
from find_spreads import get_spreads

# Dictonary that maps to the opposite action (BUY -> SELL, SELL -> BUY)
OPPOSITE = {
    'BUY': 'SELL',
    'SELL': 'BUY'
}

def assign_if_not_none(x: float, variable_name: str, order_type: str) -> float:
    """
    Function that raises a SyntaxError if 'x' is None, error message says variable_name cannot be empty for order_type
    
    Parameters
    ----------
    x: value to check if it is None
    variable_name: name of variable (used only for error messsage)
    order_type: order type (used only for error messsage)
    
    Returns
    ----------
    x if not None
    """
    if x is not None:
        return x
    else:
        raise SyntaxError(f"{variable_name} cannot be empty for {order_type} order")


def get_contract(ib: IB, strike: float, right: str) -> Option:
    """
    Helper function that qualifies and returns the SPXW 0DTE contract with the given strike and right.

    Parameters
    ----------
    ib: Interactive brokers object
    strike: Strike price of the option
    right: 'P' or 'C'
    """
    contract: Option = Option('SPXW', date.today().strftime('%Y%m%d'), strike, right, 'SMART', tradingClass='SPXW')
    ib.qualifyContracts(contract)

    return contract


def order_combo_profit_taker(*legs: tuple, action: str, nof_lot: int, order_type: str, limit_price: float = None, stop_price: float = None, stop_loss_type: str = None, stop_loss_limit_price: float = None, stop_loss_stop_price: float = None, profit_taker_limit: str = None) -> int:
    """
    Submits an combo spread order with stop loss and/or profit taker and returns the order ID.
    Stop loss can be stop or stop limit and profit taker is limit.

    Parameters
    ----------
    *legs: tuples of legs to order: (strike price, 'BUY'/'SELL', 'C'/'P)
    action: 'BUY'/'SELL'
    nof_lot: number of lots to order
    order_type: Original order's type ('MKT', 'LMT', 'STP', or 'STP LMT')
    limit_price: order's stop price (when order_type is LMT or STP LMT) - default None
    stop_price: order's limit price (when order_type is STP or STP LMT) - default None
    stop_loss_type: Stop loss order type ('STP' or 'STP LMT') - default None
    stop_loss_limit_price: stop loss order's limit price (when stop_loss_type is STP LMT) - default None
    stop_loss_stop_price: stop loss order's stop price (when stop_loss_type is STP or STP LMT) - default None
    profit_taker_limit: profit taker's limit price - default None
    
    Returns
    ----------
    Order ID of the placed order
    """
    # Connect to IB
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)

    combo_legs = [ComboLeg(conId=get_contract(ib, leg[0], leg[2]).conId, ratio=1, action=leg[1], exchange='SMART') for leg in legs]

    # Combo contract
    combo = Bag(
        symbol = 'SPX',
        currency = 'USD',
        exchange = 'SMART',
        comboLegs = combo_legs    
    )
    
    # Create the parent order
    parent_order = Order(
        action = action,
        totalQuantity = nof_lot
    )

    # Add the trigger and limit prices based on order type
    if order_type == 'MKT':
        parent_order.orderType = 'MKT'

    elif order_type == 'LMT':
        parent_order.orderType = 'LMT'
        parent_order.lmtPrice = assign_if_not_none(limit_price, 'limit_price', order_type)

    elif order_type == 'STP':
        parent_order.orderType = 'STP'
        parent_order.auxPrice = assign_if_not_none(stop_price, 'limit_price', order_type)

    elif order_type == 'STP LMT':
        parent_order.orderType = 'STP LMT'
        parent_order.auxPrice = assign_if_not_none(stop_price, 'limit_price', order_type)
        parent_order.lmtPrice = assign_if_not_none(limit_price, 'limit_price', order_type)
        
    else:
        raise SyntaxError("Order type must be LMT, STP, or STP LMT")

    # Create and attach the stop loss order
    stop_loss_order = Order(
        action = OPPOSITE[action],
        totalQuantity = nof_lot,
        parentId = parent_order.orderId
    )

    # Add the trigger and limit prices based on order type
    if stop_loss_type == 'STP':
        stop_loss_order.orderType = 'STP'
        stop_loss_order.auxPrice = assign_if_not_none(stop_loss_stop_price, 'stop_price', order_type)

    elif stop_loss_type == 'STP LMT':
        stop_loss_order.orderType = 'STP LMT'
        stop_loss_order.lmtPrice = assign_if_not_none(stop_loss_limit_price, 'limit_price', order_type)
        stop_loss_order.auxPrice = assign_if_not_none(stop_loss_stop_price, 'stop_price', order_type)

    else:
        raise SyntaxError("Stop loss type must be STP or STP LMT")

    # Create and attach the stop loss order
    if profit_taker_limit:
        profit_taker_order = LimitOrder(
            action = OPPOSITE[action],
            totalQuantity = nof_lot,
            parentId = parent_order.orderId,
            lmtPrice = profit_taker_limit
        )

    # Place the orders
    parent_trade = ib.placeOrder(combo, parent_order)
    ib.placeOrder(combo, stop_loss_order)
    ib.placeOrder(combo, profit_taker_order)

    order_id = parent_trade.order.orderId
    print(f"order ID = {order_id}")

    ib.disconnect()

    return order_id


## For testing:
def main() -> None:
    order_combo_profit_taker(
        (5470, 'SELL', 'C'), (5480, 'BUY', 'C'), (5455, 'SELL', 'P'), (5445, 'BUY', 'P'),
        action='BUY', nof_lot=1, order_type='STP', stop_price=13,
        stop_loss_type='STP LMT', stop_loss_limit_price=11, stop_loss_stop_price=10,
        profit_taker_limit=14
    )

if __name__ == '__main__':
    main()