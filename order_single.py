"""
This module contains a function (order_single) to order a 
single 0DTE limit, stop, or stop limit option contract
"""
from ib_insync import *
from datetime import date

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


def order_single(action: str, nof_lot: int, strike: float, right: str, order_type: str, limit_price: float = None, stop_price: float = None) -> int:
    """
    Submits a order for a SPX option and returns the order ID.

    Parameters
    ----------
    action: 'BUY' or 'SELL'
    strike_price: strike price of option
    right: 'C' or 'P'
    order_type: 'MKT', 'LMT', 'STP', or 'STP LMT'
    limit_price: order's stop price (when order_type is LMT or STP LMT) - default None
    stop_price: order's limit price (when order_type is STP or STP LMT) - default None
    
    Returns
    ----------
    Order ID of the placed order
    """
    # Connect to IB
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)

    # Create option contract
    contract = Option(
        symbol = 'SPXW',
        lastTradeDateOrContractMonth = date.today().strftime('%Y%m%d'),
        strike = strike,
        right = right,
        exchange = 'SMART',
        tradingClass = 'SPXW'
    )

    # Create the order
    order = Order(
        action = action,
        totalQuantity = nof_lot
    )

    # Add the trigger and limit prices based on order type
    if order_type == 'MKT':
        order.orderType = 'MKT'

    elif order_type == 'LMT':
        order.orderType = 'LMT'
        order.lmtPrice = assign_if_not_none(limit_price, 'limit_price', order_type)

    elif order_type == 'STP':
        order.orderType = 'STP'
        order.auxPrice = assign_if_not_none(stop_price, 'limit_price', order_type)

    elif order_type == 'STP LMT':
        order.orderType = 'STP LMT'
        order.auxPrice = assign_if_not_none(stop_price, 'limit_price', order_type)
        order.lmtPrice = assign_if_not_none(limit_price, 'limit_price', order_type)
        
    else:
        raise SyntaxError("Order type must be LMT, STP, or STP LMT")

    # Place the parent order
    trade = ib.placeOrder(contract, order)

    # Keep the connection open until orders are filled
    ib.sleep(5)
    
    # Get the parent order ID and place the stop loss order
    order_id = trade.order.orderId
    print(f"order ID = {order_id}")

    ib.disconnect()

    return order_id


## For testing:
def main() -> None:
    order_single('BUY', 1, 5435, 'C', 'STP', 1)

if __name__ == '__main__':
    main()