"""
This module contains a function (order_combo_profit_taker) to order a multi-leg
combo position and attach a stop loss order.
"""
from ib_insync import *
from datetime import date

# Dictonary that maps to the opposite action (BUY -> SELL, SELL -> BUY)
OPPOSITE = {
    'BUY': 'SELL',
    'SELL': 'BUY'
}

def place_orders(ib: IB, contract: Contract, orders: list[Order]) -> int:
    """
    Function that places orders and attaches all sub-orders

    Parameters
    ----------
    ib: Interactive brokers object
    contract: The order's contract
    orders: List of orders, the first item in the list must be the parent order, all following items are the sub-orders
    
    Parameters
    ----------
    Parent order ID
    """
    parent_order = orders[0]
    parent_trade = ib.placeOrder(contract, parent_order)
    ib.sleep(1)

    for order in orders[0:]:
        order.parentId = parent_trade.order.orderId
        parent_trade = ib.placeOrder(contract, order)
        ib.sleep(1)

    return parent_trade.order.orderId


def create_order(order_type: str, action: str, nof_lot: int, limit_price: float = None, stop_price: float = None) -> Order:
    """
    Returns an order object based on the given inputs

    Parameters
    ----------
    order_type: Original order's type ('MKT', 'LMT', 'STP', or 'STP LMT')
    action: 'BUY'/'SELL'
    nof_lot: number of lots to order
    limit_price: order's stop price (when order_type is LMT or STP LMT) - default None
    stop_price: order's limit price (when order_type is STP or STP LMT) - default None
    """
    order = Order(
        action = action,
        totalQuantity = nof_lot
    )   

    if order_type == 'MKT':
        order.orderType = 'MKT'
    elif order_type == 'LMT':
        order.orderType = 'LMT'
        order.lmtPrice = assign_if_not_none(limit_price, 'limit_price', order_type)
    elif order_type == 'STP':
        order.orderType = 'STP'
        order.auxPrice = assign_if_not_none(stop_price, 'stop_price', order_type)
    elif order_type == 'STP LMT':
        order.orderType = 'STP LMT'
        order.auxPrice = assign_if_not_none(stop_price, 'stop_price', order_type)
        order.lmtPrice = assign_if_not_none(limit_price, 'limit_price', order_type)
    else:
        raise SyntaxError("Order type must be MKT, LMT, STP, or STP LMT")

    return order


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
    - ib: Interactive brokers object
    - strike: Strike price of the option
    - right: 'P' or 'C'
    """
    contract: Option = Option('SPXW', date.today().strftime('%Y%m%d'), strike, right, 'SMART', tradingClass='SPXW')
    ib.qualifyContracts(contract)

    return contract


def order_combo_profit_taker(legs: tuple[int, str, str], action: str, nof_lot: int, 
                             order_type: str, limit_price: float = None, stop_price: float = None, 
                             stop_loss_type: str = 'STP', stop_loss_limit_price: float = None, stop_loss_stop_price: float = None, 
                             profit_taker: bool = False, profit_taker_limit: float = None) -> int:
    """
    Submits an combo spread order with stop loss and/or profit taker and returns the order ID.
    Stop loss can be stop or stop limit and profit taker is limit.

    Parameters:
    - legs: tuples of legs to order: (strike price, 'BUY'/'SELL', 'Call'/'Put)
    - action: 'BUY'/'SELL'
    - nof_lot: number of lots to order

    - order_type: Original order's type ('MKT', 'LMT', 'STP', or 'STP LMT')
    - limit_price: order's stop price (when order_type is LMT or STP LMT) - default None
    - stop_price: order's limit price (when order_type is STP or STP LMT) - default None

    - stop_loss_type: Stop loss order type ('STP' or 'STP LMT') - default 'STP'
    - stop_loss_limit_price: stop loss order's limit price (when stop_loss_type is STP LMT) - default None
    - stop_loss_stop_price: stop loss order's stop price (when stop_loss_type is STP or STP LMT) - default None

    - profit_taker: True if profit taker is enabled - default False
    - profit_taker_limit: profit taker's limit price - default None
    """
    # Connect to IB
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)

    # Combo contract
    combo = Bag(
        symbol = 'SPX',
        currency = 'USD',
        exchange = 'SMART',
        comboLegs = [ComboLeg(conId=get_contract(ib, leg[0], leg[2].upper()).conId, ratio=1, action=leg[1].upper(), exchange='SMART') for leg in legs]
    )
    
    orders: list[Order] = []
    action = action.upper()

    # Create the parent order
    parent_order = create_order(order_type, action, nof_lot, limit_price, stop_price)
    orders.append(parent_order)
    
    # Create the stop loss order if it exists
    if stop_loss_type in ['STP', 'STP LMT']:
        stop_loss_order = create_order(stop_loss_type, OPPOSITE[action], nof_lot, stop_loss_limit_price, stop_loss_stop_price)
        stop_loss_order.parentId = parent_order.orderId
        orders.append(stop_loss_order)
    else:
        raise SyntaxError("Stop loss type must be STP or STP LMT")

    # Create the profit taker order if it exists
    if profit_taker:
        profit_taker_order = LimitOrder(
            action = OPPOSITE[action],
            totalQuantity = nof_lot,
            lmtPrice = profit_taker_limit
        )
        profit_taker_order.parentId = parent_order.orderId
        orders.append(profit_taker_order)

    # Place Orders
    order_id = place_orders(ib, combo, orders)

    ib.disconnect()

    return order_id


## For testing:
def main() -> None:
    order_id = order_combo_profit_taker(
        [(5470, 'SELL', 'C'), (5480, 'BUY', 'C'), (5455, 'SELL', 'P'), (5445, 'BUY', 'P')], 
        action='BUY', nof_lot=1, order_type='STP LMT', limit_price=-1.0, stop_price=-1.0,
        stop_loss_type='STP LMT', stop_loss_limit_price=-3.0, stop_loss_stop_price=-0.9,
        profit_taker=True, profit_taker_limit=-14.0
    )

    print(f"Order ID = {order_id}")

if __name__ == '__main__':
    main()